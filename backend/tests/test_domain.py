from datetime import date
from decimal import Decimal

import pytest
from app.billing import cents
from app.intelligence import forecast, train_anomaly
from app.simulator import scenario_payload


def post_session(client, headers, scenario="normal", sid="test-normal", month="2026-10", **changes):
    payload = scenario_payload(scenario, month=month, sid=sid).model_dump(mode="json")
    payload.update(changes)
    return client.post("/api/sessions", headers=headers, json=payload)


def test_rounding_half_up_is_decimal():
    assert cents(Decimal("4.275")) == 428
    assert cents(Decimal("0.005")) == 1
    assert cents(Decimal("13.49") * Decimal(".02")) == 27


def test_full_billing_flow_with_interruption_promotion_credit_and_no_usage(client, headers):
    for scenario in ("normal", "interrupted", "promotion"):
        result = post_session(client, headers, scenario, sid=f"test-{scenario}")
        assert result.status_code == 201, result.text
        assert result.json()["session"]["eligibility"] == "eligible"
    result = client.post(
        "/api/billing/2026-10/credits",
        headers=headers,
        json={
            "id": "credit-1",
            "unit_id": "ap101",
            "amount": "5.00",
            "reason": "Estorno de demonstração",
        },
    )
    assert result.status_code == 201
    data = client.get("/api/billing/2026-10", headers=headers).json()
    unit = next(u for u in data["units"] if u["unit_id"] == "ap101")
    items = {i["session_id"]: i for i in unit["items"]}
    assert items["test-normal"]["total_cents"] == 1526
    assert items["test-interrupted"]["total_cents"] == 587
    assert items["test-promotion"]["total_cents"] == 0
    assert unit["total_cents"] == 1613
    assert next(u for u in data["units"] if u["unit_id"] == "ap301")["total_cents"] == 0
    result = client.post("/api/billing/2026-10/close", headers=headers)
    assert result.status_code == 200, result.text
    assert result.json()["closed"] is True
    assert client.post("/api/billing/2026-10/close", headers=headers).json() == result.json()
    assert post_session(client, headers, sid="too-late").status_code == 409
    assert (
        client.put("/api/tariffs/2026-10", headers=headers, json={"tariff_kwh": "9.00"}).status_code
        == 409
    )
    assert (
        client.post(
            "/api/billing/2026-10/credits",
            headers=headers,
            json={
                "id": "late-credit",
                "unit_id": "ap101",
                "amount": "1",
                "reason": "Não deve ser permitido",
            },
        ).status_code
        == 409
    )


def test_ingestion_idempotency_and_conflicting_duplicate(client, headers):
    first = post_session(client, headers)
    repeated = post_session(client, headers)
    assert first.status_code == 201 and repeated.status_code == 200
    assert repeated.json()["created"] is False
    assert post_session(client, headers, idle_minutes=5).status_code == 409
    logs = client.get("/api/audit?entity_id=test-normal", headers=headers).json()
    assert len(logs) == 1


@pytest.mark.parametrize("scenario", ["unidentified", "meter_error"])
def test_bad_data_held_and_cannot_be_approved(client, headers, scenario):
    result = post_session(client, headers, scenario, sid="invalid")
    assert result.status_code == 201
    assert result.json()["session"]["eligibility"] == "pending"
    assert client.get("/api/billing/2026-10", headers=headers).json()["total_cents"] == 0
    assert client.post("/api/billing/2026-10/close", headers=headers).status_code == 409
    assert (
        client.post(
            "/api/sessions/invalid/review",
            headers=headers,
            json={"decision": "approve", "reason": "Tentativa de liberação inválida"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/sessions/invalid/review",
            headers=headers,
            json={"decision": "exclude", "reason": "Falha confirmada, importar correção separada"},
        ).status_code
        == 200
    )
    assert client.post("/api/billing/2026-10/close", headers=headers).status_code == 200


def test_ai_controls_eligibility_and_review_changes_bill(client, headers):
    data = post_session(client, headers, "anomaly", sid="odd").json()["session"]
    assert data["anomaly"]["flagged"] is True
    assert data["anomaly"]["score"] > data["anomaly"]["threshold"]
    assert data["eligibility"] == "pending"
    assert data["anomaly"]["version"]
    assert client.get("/api/billing/2026-10", headers=headers).json()["total_cents"] == 0
    review = client.post(
        "/api/sessions/odd/review",
        headers=headers,
        json={"decision": "approve", "reason": "Duração longa conferida com o usuário fictício"},
    )
    assert review.status_code == 200
    assert client.get("/api/billing/2026-10", headers=headers).json()["total_cents"] == 1313
    assert (
        client.post(
            "/api/sessions/odd/review",
            headers=headers,
            json={"decision": "exclude", "reason": "Segunda revisão indevida"},
        ).status_code
        == 409
    )
    events = client.get("/api/audit?entity_id=odd", headers=headers).json()
    assert events[0]["action"] == "session.reviewed"
    assert events[0]["actor"] == "manager"


@pytest.mark.parametrize(
    "changes",
    [
        {"user_id": "resident-102"},
        {"vehicle_id": "veh-102"},
        {"energy_kwh": "20"},
        {"end_meter_kwh": "1200", "energy_kwh": "200"},
    ],
)
def test_identity_meter_and_power_consistency(client, headers, changes):
    response = post_session(client, headers, **changes)
    assert response.status_code == 201
    assert response.json()["session"]["quality_issues"]
    assert response.json()["session"]["eligibility"] == "pending"


@pytest.mark.parametrize(
    "changes",
    [
        {"started_at": "2026-10-26T19:00:00"},
        {"ended_at": "2026-10-25T19:00:00-03:00"},
        {"idle_minutes": 1000},
        {"charger_id": "does-not-exist"},
        {"start_meter_kwh": "NaN"},
        {"user_id": "ghost"},
        {"energy_kwh": "Infinity"},
        {"session_id": "bad\nidentifier"},
    ],
)
def test_invalid_contract_returns_422(client, headers, changes):
    assert post_session(client, headers, **changes).status_code == 422


def test_timezone_assigns_month_by_sao_paulo_start(client, headers):
    result = post_session(
        client, headers, started_at="2026-09-01T01:00:00Z", ended_at="2026-09-01T03:30:00Z"
    )
    assert result.status_code == 201
    assert result.json()["session"]["month"] == "2026-08"


def test_credit_replay_does_not_double_credit(client, headers):
    credit = {
        "id": "refund",
        "unit_id": "ap101",
        "amount": "2.50",
        "reason": "Ajuste explicado de demonstração",
    }
    assert (
        client.post("/api/billing/2026-10/credits", headers=headers, json=credit).status_code == 201
    )
    assert (
        client.post("/api/billing/2026-10/credits", headers=headers, json=credit).json()["created"]
        is False
    )
    assert client.get("/api/billing/2026-10", headers=headers).json()["total_cents"] == -250
    credit["amount"] = "3.00"
    assert (
        client.post("/api/billing/2026-10/credits", headers=headers, json=credit).status_code == 409
    )


def test_optional_fixed_fee_applies_to_all_units(client, headers):
    assert (
        client.put(
            "/api/tariffs/2026-10", headers=headers, json={"tariff_kwh": ".95", "fixed_fee": "10"}
        ).status_code
        == 200
    )
    bill = client.get("/api/billing/2026-10", headers=headers).json()
    assert bill["total_cents"] == 5000
    assert all(u["total_cents"] == 1000 for u in bill["units"])


def test_two_vehicles_consolidated_same_unit(client, headers):
    post_session(client, headers, sid="vehicle-a")
    post_session(client, headers, sid="vehicle-b", vehicle_id="veh-101-b")
    bill = client.get("/api/billing/2026-10", headers=headers).json()
    assert bill["units"][0]["total_cents"] == 3052
    assert len(bill["units"][0]["items"]) == 2


def test_forecast_temporal_holdout_and_future_invariance(client, headers):
    initial = client.get("/api/forecast?month=2026-09&as_of=2026-09-27", headers=headers).json()
    assert initial["status"] == "ready"
    assert (
        initial["training_end"]
        < initial["validation_start"]
        <= initial["validation_end"]
        < initial["as_of"]
    )
    assert initial["validation_days"] == 14
    assert initial["forecast_days"] == 4
    assert initial["projected_kwh"] == pytest.approx(
        initial["observed_kwh"] + initial["remaining_kwh"], abs=0.011
    )
    assert initial["ridge_mae_kwh"] < initial["baseline_mae_kwh"]
    post_session(client, headers, sid="future-data")
    assert (
        client.get("/api/forecast?month=2026-09&as_of=2026-09-27", headers=headers).json()
        == initial
    )


def test_insufficient_history_returns_explicit_state(database, tmp_path):
    with database() as db:
        assert forecast(db, "2026-07", date(2026, 7, 3))["status"] == "insufficient_history"
        with pytest.raises(ValueError):
            train_anomaly(db, date(2026, 7, 2), path=tmp_path / "not-created.json")


def test_review_reason_cannot_be_whitespace(client, headers):
    assert (
        client.post(
            "/api/sessions/demo-anomaly/review",
            headers=headers,
            json={"decision": "approve", "reason": " " * 20},
        ).status_code
        == 422
    )


def test_nonexistent_session(client, headers):
    assert client.get("/api/sessions/unknown", headers=headers).status_code == 404


def test_tariff_currency_precision(client, headers):
    assert (
        client.put(
            "/api/tariffs/2026-10",
            headers=headers,
            json={"tariff_kwh": ".95", "fixed_fee": "0.005"},
        ).status_code
        == 422
    )
