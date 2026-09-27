"""Dados sintéticos determinísticos; nenhum registro veio de um HCA G2 real."""

import argparse
import random
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select

from .auth import hash_password
from .db import SessionLocal
from .intelligence import train_anomaly
from .models import AuditEvent, Charger, ChargingSession, Tariff, Unit, User, Vehicle
from .schemas import SessionInput
from .sessions import ingest

DEMO_AS_OF = date(2026, 9, 27)
TZ = ZoneInfo("America/Sao_Paulo")


def scenario_payload(scenario="normal", month="2026-09", unit_id="ap101", sid=None):
    start = datetime.fromisoformat(month + "-26T19:00:00-03:00")
    duration, energy, idle = 150, Decimal("14.200"), 10
    if scenario == "interrupted":
        duration, energy, idle = 48, Decimal("4.500"), 0
    elif scenario == "anomaly":
        duration, energy, idle = 650, Decimal("12.000"), 0
    who = unit_id.removeprefix("ap")
    payload = dict(
        session_id=sid or "sim-" + uuid.uuid4().hex[:12],
        charger_id="hca-g2-01",
        user_id=f"resident-{who}",
        unit_id=unit_id,
        vehicle_id=f"veh-{who}",
        started_at=start,
        ended_at=start + timedelta(minutes=duration),
        start_meter_kwh=Decimal(1000),
        end_meter_kwh=Decimal(1000) + energy,
        energy_kwh=energy,
        idle_minutes=idle,
        source="simulator",
        status="interrupted" if scenario == "interrupted" else "completed",
        stop_reason="power_interruption" if scenario == "interrupted" else "vehicle_disconnected",
        cost_center="promotion" if scenario == "promotion" else "resident",
    )
    if scenario == "unidentified":
        payload.update(user_id=None, unit_id=None, vehicle_id=None)
    elif scenario == "meter_error":
        payload["end_meter_kwh"] = Decimal(999)
    return SessionInput(**payload)


def seed(db):
    if db.get(User, "manager"):
        return {
            "created": False,
            "message": "Base existente preservada; seed não redefine dados.",
        }
    rng = random.Random(568600)
    for label in ("101", "102", "201", "202", "301"):
        db.add(Unit(id=f"ap{label}", label=f"Apartamento {label}"))
    db.flush()
    password_hash = hash_password("Demo2026!")
    db.add(
        User(
            id="manager",
            name="Gestor demonstração",
            email="gestor@demo.local",
            role="manager",
            password_hash=password_hash,
        )
    )
    names = ["Ana Martins", "Bruno Lima", "Carla Nunes", "Diego Costa", "Elisa Souza"]
    for label, name in zip(("101", "102", "201", "202", "301"), names, strict=True):
        db.add(
            User(
                id=f"resident-{label}",
                name=name + " (fictício)",
                email=f"morador{label}@demo.local",
                role="user",
                unit_id=f"ap{label}",
                password_hash=password_hash,
            )
        )
        db.add(
            Vehicle(
                id=f"veh-{label}",
                unit_id=f"ap{label}",
                model="Veículo elétrico demonstrativo",
            )
        )
    db.add(Vehicle(id="veh-101-b", unit_id="ap101", model="Segundo veículo da unidade"))
    for number, power in ((1, 7), (2, 11), (3, 22)):
        db.add(
            Charger(
                id=f"hca-g2-0{number}",
                name=f"Estação 0{number}",
                nominal_power_kw=Decimal(power),
            )
        )
    for month in ("2026-07", "2026-08", "2026-09", "2026-10"):
        db.add(
            Tariff(
                month=month,
                tariff_kwh=Decimal("0.95"),
                session_fee=Decimal("1.50"),
                idle_fee=Decimal("0.10"),
                loss_percent=Decimal(2),
                fixed_fee=Decimal(0),
                idle_grace_minutes=15,
            )
        )
    db.commit()
    counter = 0
    for offset in range((DEMO_AS_OF - date(2026, 7, 1)).days):
        day = date(2026, 7, 1) + timedelta(days=offset)
        if day == date(2026, 9, 1):
            train_anomaly(db, day)
        # Uma sessão por unidade/dia, quatro unidades ativas. Sem sobreposição
        # no mesmo carregador: uma estação por slot diário sequencial de 4 h.
        for slot, label in enumerate(("101", "102", "201", "202")):
            energy = Decimal(
                str(
                    round(
                        12
                        + offset * 0.035
                        + (2 if day.weekday() < 5 else -2)
                        + rng.uniform(-1.4, 1.4),
                        3,
                    )
                )
            )
            active = int(float(energy) / 6.1 * 60) + 1
            idle = rng.randint(0, 25)
            start = datetime.combine(day, datetime.min.time(), TZ) + timedelta(hours=slot * 4)
            counter += 1
            p = SessionInput(
                session_id=f"hist-{counter:04d}",
                charger_id="hca-g2-01",
                user_id=f"resident-{label}",
                unit_id=f"ap{label}",
                vehicle_id="veh-101-b"
                if label == "101" and slot == 0 and offset % 2
                else f"veh-{label}",
                started_at=start,
                ended_at=start + timedelta(minutes=active + idle),
                start_meter_kwh=Decimal(counter * 100),
                end_meter_kwh=Decimal(counter * 100) + energy,
                energy_kwh=energy,
                idle_minutes=idle,
                source="simulator",
                status="interrupted" if offset % 17 == 0 else "completed",
                stop_reason="power_interruption" if offset % 17 == 0 else "vehicle_disconnected",
            )
            ingest(db, p, "seed", warmup=day < date(2026, 9, 1))
        db.commit()
    for scenario in ("anomaly", "unidentified", "meter_error", "promotion"):
        ingest(db, scenario_payload(scenario, sid=f"demo-{scenario}"), "seed")
    db.add(
        AuditEvent(
            action="demo.seeded",
            entity_id="synthetic-568600",
            actor="seed",
            detail=dict(as_of=DEMO_AS_OF.isoformat(), seed=568600),
        )
    )
    db.commit()
    return dict(
        created=True,
        sessions=len(db.scalars(select(ChargingSession)).all()),
        source="synthetic",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    with SessionLocal() as db:
        print(seed(db))
