import hashlib
import json
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from .billing import lock_period
from .intelligence import score_session
from .models import AuditEvent, Charger, ChargingSession, Unit, User, Vehicle
from .schemas import SessionInput

TZ = ZoneInfo("America/Sao_Paulo")


def ingest(db, payload: SessionInput, actor: str, warmup=False):
    raw = payload.model_dump(mode="json")
    digest = hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()
    existing = db.get(ChargingSession, payload.session_id)
    if existing:
        if existing.payload_hash != digest:
            raise HTTPException(409, "Identificador já usado com conteúdo diferente.")
        return existing, False
    charger = db.get(Charger, payload.charger_id)
    if not charger:
        raise HTTPException(422, "Carregador desconhecido.")
    month = payload.started_at.astimezone(TZ).strftime("%Y-%m")
    lock_period(db, month)
    for cls, key in (
        (User, payload.user_id),
        (Unit, payload.unit_id),
        (Vehicle, payload.vehicle_id),
    ):
        if key and not db.get(cls, key):
            raise HTTPException(422, f"Referência desconhecida: {key}")
    issues = []
    if not payload.user_id or not payload.unit_id:
        issues.append("Sessão sem identificação de usuário/unidade.")
    if (
        payload.user_id
        and payload.unit_id
        and db.get(User, payload.user_id).unit_id != payload.unit_id
    ):
        issues.append("Usuário não pertence à unidade informada.")
    if payload.vehicle_id and db.get(Vehicle, payload.vehicle_id).unit_id != payload.unit_id:
        issues.append("Veículo não pertence à unidade informada.")
    energy = payload.end_meter_kwh - payload.start_meter_kwh
    duration = Decimal(str((payload.ended_at - payload.started_at).total_seconds())) / 60
    active_minutes = duration - payload.idle_minutes
    if energy < 0:
        issues.append("Medidor final inferior ao inicial.")
    if payload.energy_kwh is not None and abs(payload.energy_kwh - energy) > Decimal("0.01"):
        issues.append("Energia declarada diverge da diferença entre medidores.")
    average = max(energy, Decimal(0)) / active_minutes * 60
    if average > charger.nominal_power_kw * Decimal("1.05"):
        issues.append("Energia incompatível com potência nominal e tempo ativo.")
    s = ChargingSession(
        id=payload.session_id,
        charger_id=payload.charger_id,
        user_id=payload.user_id,
        unit_id=payload.unit_id,
        vehicle_id=payload.vehicle_id,
        month=month,
        started_at=payload.started_at.isoformat(),
        ended_at=payload.ended_at.isoformat(),
        energy_kwh=max(energy, Decimal(0)),
        duration_minutes=duration,
        average_power_kw=average,
        idle_minutes=payload.idle_minutes,
        status=payload.status,
        stop_reason=payload.stop_reason,
        cost_center=payload.cost_center,
        raw_source=raw,
        payload_hash=digest,
        quality_issues=issues,
        eligibility="pending" if issues else "eligible",
    )
    s.anomaly = (
        dict(
            flagged=False,
            status="training_warmup",
            version=None,
            explanation="Histórico de aquecimento do detector, ainda sem modelo.",
        )
        if warmup
        else score_session(s)
    )
    if s.anomaly.get("flagged"):
        s.eligibility = "pending"
    db.add(s)
    db.add(
        AuditEvent(
            action="session.ingested",
            entity_id=s.id,
            actor=actor,
            detail=dict(
                eligibility=s.eligibility,
                payload_hash=digest,
                model=s.anomaly.get("version"),
                source=payload.source,
            ),
        )
    )
    db.flush()
    return s, True


def review(db, sid, decision, reason, actor):
    s = db.get(ChargingSession, sid)
    if not s:
        raise HTTPException(404, "Sessão não encontrada.")
    lock_period(db, s.month)
    if s.eligibility != "pending":
        raise HTTPException(409, "A sessão já foi revisada ou não está retida.")
    if decision == "approve" and s.quality_issues:
        raise HTTPException(
            422,
            "Dados inconsistentes não podem ser liberados. Exclua e importe uma sessão corrigida.",
        )
    s.eligibility = "eligible" if decision == "approve" else "excluded"
    s.review_reason = reason
    s.reviewed_by = actor
    db.add(
        AuditEvent(
            action="session.reviewed",
            entity_id=sid,
            actor=actor,
            detail=dict(decision=decision, reason=reason, model=s.anomaly.get("version")),
        )
    )
    db.commit()
    return s


def serialize(s):
    return dict(
        id=s.id,
        charger_id=s.charger_id,
        user_id=s.user_id,
        unit_id=s.unit_id,
        vehicle_id=s.vehicle_id,
        month=s.month,
        started_at=s.started_at,
        ended_at=s.ended_at,
        energy_kwh=float(s.energy_kwh),
        duration_minutes=float(s.duration_minutes),
        average_power_kw=float(s.average_power_kw),
        idle_minutes=s.idle_minutes,
        status=s.status,
        stop_reason=s.stop_reason,
        cost_center=s.cost_center,
        eligibility=s.eligibility,
        quality_issues=s.quality_issues,
        anomaly=s.anomaly,
        review_reason=s.review_reason,
        reviewed_by=s.reviewed_by,
        source=s.raw_source["source"],
    )
