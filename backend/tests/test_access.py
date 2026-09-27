def test_login_required_and_bad_password(client):
    assert client.get("/api/sessions").status_code == 401
    assert (
        client.post(
            "/api/auth/login", json={"email": "gestor@demo.local", "password": "incorrect"}
        ).status_code
        == 401
    )


def test_resident_cannot_read_other_unit_or_admin_endpoints(client, resident):
    rows = client.get("/api/sessions?unit_id=ap102", headers=resident).json()
    assert rows and all(s["unit_id"] == "ap101" for s in rows)
    bill = client.get("/api/billing/2026-09", headers=resident).json()
    assert len(bill["units"]) == 1 and bill["units"][0]["unit_id"] == "ap101"
    assert client.get("/api/sessions/hist-0002", headers=resident).status_code == 404
    for endpoint in ("/api/audit", "/api/analytics", "/api/forecast", "/api/model"):
        assert client.get(endpoint, headers=resident).status_code == 403
    assert client.post("/api/simulate", headers=resident, json={}).status_code == 403
    assert client.post("/api/billing/2026-09/close", headers=resident).status_code == 403
    catalog = client.get("/api/catalog", headers=resident).json()
    assert [u["id"] for u in catalog["units"]] == ["ap101"]
    assert all("password_hash" not in u for u in catalog["users"])


def test_csv_is_protected_and_scoped(client, resident):
    assert client.get("/api/billing/2026-09/csv").status_code == 401
    result = client.get("/api/billing/2026-09/csv", headers=resident)
    assert result.status_code == 200
    assert "ap101" in result.text and "ap102" not in result.text
    assert "text/csv" in result.headers["content-type"]


def test_logout_revokes_token(client, headers):
    assert client.post("/api/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/auth/me", headers=headers).status_code == 401
