import csv
import io
import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import (
    bearer,
    create_token,
    current_user,
    manager,
    token_digest,
    verify_password,
)
from .billing import cents, close_month, lock_period, preview
from .db import engine, get_db
from .intelligence import MODEL_PATH, forecast
from .models import (
    AuditEvent,
    AuthToken,
    Charger,
    ChargingSession,
    Credit,
    MonthClose,
    Tariff,
    Unit,
    User,
    Vehicle,
)
from .schemas import (
    CreditInput,
    LoginInput,
    Month,
    ReviewInput,
    SessionInput,
    SimulationInput,
    TariffInput,
)
from .sessions import TZ, ingest, review, serialize
from .simulator import DEMO_AS_OF, scenario_payload

app = FastAPI(
    title="EV ChargeOps",
    version="2.0.0",
    description="Protótipo acadêmico GoodWe + FIAP; dados sintéticos, sem cobrança real.",
)
DB = Annotated[Session, Depends(get_db)]
Manager = Annotated[User, Depends(manager)]
Actor = Annotated[User, Depends(current_user)]


@app.exception_handler(IntegrityError)
async def integrity_error(_, exc):
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=409,
        content={"detail": "Conflito de gravação. Atualize os dados e tente novamente."},
    )


@app.get("/api/health")
def health(db: DB):
    db.execute(select(1))
    return {"status": "ok", "database": engine.dialect.name, "source": "synthetic_demo"}


def public_user(user):
    return dict(id=user.id, name=user.name, email=user.email, role=user.role, unit_id=user.unit_id)


@app.post("/api/auth/login")
def login(data: LoginInput, db: DB):
    user = db.scalar(select(User).where(User.email == data.email.strip().lower()))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "E-mail ou senha inválidos.")
    return {"token": create_token(db, user), "user": public_user(user)}


@app.get("/api/auth/me")
def me(user: Actor):
    return public_user(user)


@app.post("/api/auth/logout", status_code=204)
def logout(user: Actor, db: DB, credentials=Depends(bearer)):
    db.delete(db.get(AuthToken, token_digest(credentials.credentials)))
    db.commit()


@app.get("/api/catalog")
def catalog(user: Actor, db: DB):
    return dict(
        units=[
            dict(id=u.id, label=u.label)
            for u in db.scalars(select(Unit).order_by(Unit.id))
            if user.role == "manager" or u.id == user.unit_id
        ],
        users=[
            public_user(u)
            for u in db.scalars(select(User))
            if user.role == "manager" or u.id == user.id
        ],
        vehicles=[
            dict(id=v.id, unit_id=v.unit_id, model=v.model)
            for v in db.scalars(select(Vehicle))
            if user.role == "manager" or v.unit_id == user.unit_id
        ],
        chargers=[
            dict(
                id=c.id,
                name=c.name,
                model=c.model,
                nominal_power_kw=float(c.nominal_power_kw),
                status=c.status,
            )
            for c in db.scalars(select(Charger))
        ],
        months=list(db.scalars(select(Tariff.month).order_by(Tariff.month))),
        demo_as_of=DEMO_AS_OF.isoformat(),
    )


@app.post("/api/sessions")
def register(data: SessionInput, user: Manager, db: DB, response: Response):
    item, created = ingest(db, data, user.id)
    db.commit()
    response.status_code = 201 if created else 200
    return {"created": created, "session": serialize(item)}


@app.get("/api/sessions")
def sessions(
    user: Actor,
    db: DB,
    month: Month = "2026-09",
    unit_id: str | None = None,
    charger_id: str | None = None,
    eligibility: str | None = None,
    status: str | None = None,
):
    query = select(ChargingSession).where(ChargingSession.month == month)
    if user.role != "manager":
        query = query.where(ChargingSession.unit_id == user.unit_id)
    elif unit_id:
        query = query.where(ChargingSession.unit_id == unit_id)
    for column, value in (
        (ChargingSession.charger_id, charger_id),
        (ChargingSession.eligibility, eligibility),
        (ChargingSession.status, status),
    ):
        if value:
            query = query.where(column == value)
    return [
        serialize(s)
        for s in db.scalars(query.order_by(ChargingSession.started_at.desc(), ChargingSession.id))
    ]


@app.get("/api/sessions/{sid}")
def session_detail(sid: str, user: Actor, db: DB):
    s = db.get(ChargingSession, sid)
    if not s or (user.role != "manager" and s.unit_id != user.unit_id):
        raise HTTPException(404, "Sessão não encontrada.")
    return {**serialize(s), "original": s.raw_source}


@app.post("/api/sessions/{sid}/review")
def review_session(sid: str, data: ReviewInput, user: Manager, db: DB):
    return serialize(review(db, sid, data.decision, data.reason.strip(), user.id))


@app.post("/api/simulate", status_code=201)
def simulate(data: SimulationInput, user: Manager, db: DB):
    item, _ = ingest(db, scenario_payload(data.scenario, data.month, data.unit_id), user.id)
    db.commit()
    return serialize(item)


@app.get("/api/billing/{month}")
def billing(month: Month, user: Actor, db: DB):
    return preview(db, month, user.unit_id if user.role != "manager" else None)


@app.post("/api/billing/{month}/close")
def close(month: Month, user: Manager, db: DB):
    return close_month(db, month, user.id)


@app.put("/api/tariffs/{month}")
def update_tariff(month: Month, data: TariffInput, user: Manager, db: DB):
    t = db.get(Tariff, month)
    if t:
        lock_period(db, month)
    elif db.get(MonthClose, month):
        raise HTTPException(409, "Período fechado.")
    else:
        t = Tariff(month=month)
        db.add(t)
    for key, value in data.model_dump().items():
        setattr(t, key, value)
    db.add(
        AuditEvent(
            action="tariff.updated",
            entity_id=month,
            actor=user.id,
            detail=data.model_dump(mode="json"),
        )
    )
    db.commit()
    return preview(db, month)


@app.post("/api/billing/{month}/credits", status_code=201)
def credit(month: Month, data: CreditInput, user: Manager, db: DB):
    lock_period(db, month)
    if not db.get(Unit, data.unit_id):
        raise HTTPException(422, "Unidade desconhecida.")
    existing = db.get(Credit, data.id)
    if existing:
        if (existing.month, existing.unit_id, existing.amount_cents, existing.reason) != (
            month,
            data.unit_id,
            cents(data.amount),
            data.reason,
        ):
            raise HTTPException(409, "Chave de crédito já usada com outros dados.")
        return {"id": existing.id, "created": False}
    db.add(
        Credit(
            id=data.id,
            month=month,
            unit_id=data.unit_id,
            amount_cents=cents(data.amount),
            reason=data.reason,
            created_by=user.id,
        )
    )
    db.add(
        AuditEvent(
            action="credit.created",
            entity_id=data.id,
            actor=user.id,
            detail=data.model_dump(mode="json"),
        )
    )
    db.commit()
    return {"id": data.id, "created": True}


@app.get("/api/billing/{month}/csv")
def export_csv(month: Month, user: Actor, db: DB):
    data = preview(db, month, user.unit_id if user.role != "manager" else None)
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(
        [
            "Mes",
            "Unidade",
            "Energia_kWh",
            "Sessoes",
            "Quota_fixa_BRL",
            "Creditos_BRL",
            "Total_BRL",
            "Estado",
        ]
    )
    for unit in data["units"]:
        writer.writerow(
            [
                month,
                unit["unit_id"],
                f"{unit['energy_kwh']:.3f}".replace(".", ","),
                len(unit["items"]),
                f"{unit['fixed_cents'] / 100:.2f}".replace(".", ","),
                f"{unit['credit_cents'] / 100:.2f}".replace(".", ","),
                f"{unit['total_cents'] / 100:.2f}".replace(".", ","),
                "Fechado" if data["closed"] else "Previa",
            ]
        )
    return Response(
        "\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="rateio-{month}.csv"'},
    )


@app.get("/api/analytics")
def analytics(user: Manager, db: DB, month: Month = "2026-09"):
    rows = db.scalars(select(ChargingSession).where(ChargingSession.month == month)).all()
    data = preview(db, month)
    daily = {}
    for s in rows:
        if not s.quality_issues and s.eligibility == "eligible":
            day = datetime.fromisoformat(s.started_at).astimezone(TZ).date().isoformat()
            daily[day] = daily.get(day, 0) + float(s.energy_kwh)
    return dict(
        sessions=len(rows),
        energy_kwh=round(sum(float(s.energy_kwh) for s in rows if s.eligibility == "eligible"), 2),
        pending=sum(s.eligibility == "pending" for s in rows),
        excluded=sum(s.eligibility == "excluded" for s in rows),
        anomalies=sum(bool(s.anomaly.get("flagged")) for s in rows),
        total_cents=data["total_cents"],
        active_units=len({s.unit_id for s in rows if s.unit_id and s.eligibility == "eligible"}),
        daily=[{"date": d, "kwh": round(v, 2)} for d, v in sorted(daily.items())],
        units=[
            dict(
                unit_id=u["unit_id"],
                label=u["label"],
                kwh=u["energy_kwh"],
                total_cents=u["total_cents"],
            )
            for u in data["units"]
        ],
    )


@app.get("/api/forecast")
def get_forecast(user: Manager, db: DB, month: Month = "2026-09", as_of: date = DEMO_AS_OF):
    return forecast(db, month, as_of)


@app.get("/api/model")
def model_info(user: Manager):
    return (
        json.loads(MODEL_PATH.read_text())
        if MODEL_PATH.exists()
        else {"status": "insufficient_history"}
    )


@app.get("/api/audit")
def audit(
    user: Manager,
    db: DB,
    entity_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
):
    query = select(AuditEvent)
    if entity_id:
        query = query.where(AuditEvent.entity_id == entity_id)
    rows = db.scalars(query.order_by(AuditEvent.id.desc()).limit(limit))
    return [
        dict(
            id=r.id,
            action=r.action,
            entity_id=r.entity_id,
            actor=r.actor,
            detail=r.detail,
            created_at=r.created_at,
        )
        for r in rows
    ]


static_dir = Path(os.getenv("FRONTEND_DIST", "../frontend/dist"))
if static_dir.is_dir():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
