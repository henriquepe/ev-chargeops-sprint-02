"""Valores calculados em Decimal e arredondados por componente, em centavos."""

from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException
from sqlalchemy import select

from .models import (
    AuditEvent,
    ChargingSession,
    Credit,
    Invoice,
    InvoiceItem,
    MonthClose,
    Tariff,
    Unit,
)


def cents(value):
    return int((Decimal(str(value)) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def tariff_dict(t):
    return {
        k: str(getattr(t, k))
        for k in (
            "tariff_kwh",
            "session_fee",
            "idle_fee",
            "idle_grace_minutes",
            "loss_percent",
            "fixed_fee",
        )
    }


def session_cost(s, t):
    if s.cost_center == "promotion":
        return dict(energy_cents=0, operation_cents=0, idle_cents=0, loss_cents=0, total_cents=0)
    energy = s.energy_kwh * t.tariff_kwh
    parts = dict(
        energy_cents=cents(energy),
        operation_cents=cents(t.session_fee),
        idle_cents=cents(Decimal(max(0, s.idle_minutes - t.idle_grace_minutes)) * t.idle_fee),
        loss_cents=cents(energy * t.loss_percent / Decimal(100)),
    )
    return {**parts, "total_cents": sum(parts.values())}


def lock_period(db, month):
    # Todas as escritas no período passam por esta trava. PostgreSQL serializa
    # ingestão/revisão/tarifa/crédito/fechamento; a demo SQLite usa um worker.
    tariff = db.scalar(select(Tariff).where(Tariff.month == month).with_for_update())
    if tariff is None:
        raise HTTPException(422, "Cadastre a tarifa deste mês antes de importar sessões.")
    if db.get(MonthClose, month):
        raise HTTPException(409, "Mês fechado: o demonstrativo é imutável.")
    return tariff


def preview(db, month, unit_id=None):
    closed = db.get(MonthClose, month)
    if closed:
        invoices = db.scalars(
            select(Invoice).where(Invoice.month == month).order_by(Invoice.unit_id)
        ).all()
        rows = [i.snapshot for i in invoices if unit_id is None or i.unit_id == unit_id]
        return dict(
            month=month,
            closed=True,
            closed_at=closed.closed_at,
            tariff=closed.tariff_snapshot,
            units=rows,
            pending_count=0,
            total_cents=sum(u["total_cents"] for u in rows),
        )
    tariff = db.get(Tariff, month)
    if not tariff:
        raise HTTPException(404, "Tarifa não cadastrada para este mês.")
    units = db.scalars(select(Unit).order_by(Unit.id)).all()
    sessions = db.scalars(
        select(ChargingSession)
        .where(ChargingSession.month == month)
        .order_by(ChargingSession.started_at)
    ).all()
    credits = db.scalars(select(Credit).where(Credit.month == month)).all()
    rows = []
    for unit in units:
        if unit_id is not None and unit.id != unit_id:
            continue
        items = []
        for s in sessions:
            if s.unit_id == unit.id and s.eligibility == "eligible":
                items.append(
                    dict(
                        session_id=s.id,
                        started_at=s.started_at,
                        status=s.status,
                        energy_kwh=float(s.energy_kwh),
                        cost_center=s.cost_center,
                        **session_cost(s, tariff),
                    )
                )
        unit_credits = [
            dict(id=c.id, amount_cents=c.amount_cents, reason=c.reason)
            for c in credits
            if c.unit_id == unit.id
        ]
        credit_total = sum(c["amount_cents"] for c in unit_credits)
        gross = sum(i["total_cents"] for i in items) + cents(tariff.fixed_fee)
        rows.append(
            dict(
                unit_id=unit.id,
                label=unit.label,
                items=items,
                energy_kwh=round(sum(i["energy_kwh"] for i in items), 3),
                fixed_cents=cents(tariff.fixed_fee),
                credits=unit_credits,
                credit_cents=credit_total,
                total_cents=gross - credit_total,
                pending_count=sum(
                    s.eligibility == "pending" and s.unit_id == unit.id for s in sessions
                ),
            )
        )
    pending = sum(
        s.eligibility == "pending" and (unit_id is None or s.unit_id == unit_id) for s in sessions
    )
    return dict(
        month=month,
        closed=False,
        tariff=tariff_dict(tariff),
        units=rows,
        pending_count=pending,
        total_cents=sum(u["total_cents"] for u in rows),
    )


def close_month(db, month, actor):
    # Repetir o fechamento devolve exatamente o snapshot persistido.
    if db.get(MonthClose, month):
        return preview(db, month)
    tariff = lock_period(db, month)
    data = preview(db, month)
    if data["pending_count"]:
        raise HTTPException(
            409,
            f"Revise as {data['pending_count']} sessões retidas antes do fechamento.",
        )
    db.add(MonthClose(month=month, tariff_snapshot=tariff_dict(tariff), closed_by=actor))
    db.flush()
    for row in data["units"]:
        iid = f"{month}-{row['unit_id']}"
        db.add(
            Invoice(
                id=iid,
                month=month,
                unit_id=row["unit_id"],
                total_cents=row["total_cents"],
                snapshot=row,
            )
        )
        db.flush()
        for item in row["items"]:
            db.add(
                InvoiceItem(
                    invoice_id=iid,
                    session_id=item["session_id"],
                    amount_cents=item["total_cents"],
                    breakdown=item,
                )
            )
    db.add(
        AuditEvent(
            action="month.closed",
            entity_id=month,
            actor=actor,
            detail={"total_cents": data["total_cents"], "units": len(data["units"])},
        )
    )
    db.commit()
    return preview(db, month)
