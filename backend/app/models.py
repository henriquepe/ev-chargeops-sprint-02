from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import JSON, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def now():
    return datetime.now(timezone.utc).isoformat()


class Unit(Base):
    __tablename__ = "units"
    id: Mapped[str] = mapped_column(primary_key=True)
    label: Mapped[str]


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    email: Mapped[str] = mapped_column(unique=True)
    role: Mapped[str]
    unit_id: Mapped[str | None] = mapped_column(ForeignKey("units.id"))
    password_hash: Mapped[str]


class AuthToken(Base):
    __tablename__ = "auth_tokens"
    digest: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[str]


class Vehicle(Base):
    __tablename__ = "vehicles"
    id: Mapped[str] = mapped_column(primary_key=True)
    unit_id: Mapped[str] = mapped_column(ForeignKey("units.id"))
    model: Mapped[str]


class Charger(Base):
    __tablename__ = "chargers"
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    model: Mapped[str] = mapped_column(default="HCA G2 (simulado)")
    nominal_power_kw: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    status: Mapped[str] = mapped_column(default="available")


class Tariff(Base):
    __tablename__ = "tariff_periods"
    month: Mapped[str] = mapped_column(String(7), primary_key=True)
    tariff_kwh: Mapped[Decimal] = mapped_column(Numeric(12, 6))
    session_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    idle_fee: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=0)
    idle_grace_minutes: Mapped[int] = mapped_column(default=15)
    loss_percent: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    fixed_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)


class ChargingSession(Base):
    __tablename__ = "charging_sessions"
    id: Mapped[str] = mapped_column(primary_key=True)
    charger_id: Mapped[str] = mapped_column(ForeignKey("chargers.id"))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    unit_id: Mapped[str | None] = mapped_column(ForeignKey("units.id"))
    vehicle_id: Mapped[str | None] = mapped_column(ForeignKey("vehicles.id"))
    month: Mapped[str] = mapped_column(String(7), index=True)
    started_at: Mapped[str]
    ended_at: Mapped[str]
    energy_kwh: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    duration_minutes: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    average_power_kw: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    idle_minutes: Mapped[int]
    status: Mapped[str]
    stop_reason: Mapped[str]
    cost_center: Mapped[str]
    eligibility: Mapped[str] = mapped_column(index=True)
    quality_issues: Mapped[list] = mapped_column(JSON)
    anomaly: Mapped[dict] = mapped_column(JSON)
    raw_source: Mapped[dict] = mapped_column(JSON)
    payload_hash: Mapped[str]
    review_reason: Mapped[str | None]
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[str] = mapped_column(default=now)


class Credit(Base):
    __tablename__ = "credits"
    id: Mapped[str] = mapped_column(primary_key=True)
    month: Mapped[str]
    unit_id: Mapped[str] = mapped_column(ForeignKey("units.id"))
    amount_cents: Mapped[int]
    reason: Mapped[str]
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))


class MonthClose(Base):
    __tablename__ = "month_closes"
    month: Mapped[str] = mapped_column(primary_key=True)
    tariff_snapshot: Mapped[dict] = mapped_column(JSON)
    closed_at: Mapped[str] = mapped_column(default=now)
    closed_by: Mapped[str] = mapped_column(ForeignKey("users.id"))


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (UniqueConstraint("month", "unit_id"),)
    id: Mapped[str] = mapped_column(primary_key=True)
    month: Mapped[str] = mapped_column(ForeignKey("month_closes.month"))
    unit_id: Mapped[str] = mapped_column(ForeignKey("units.id"))
    total_cents: Mapped[int]
    snapshot: Mapped[dict] = mapped_column(JSON)


class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"))
    session_id: Mapped[str] = mapped_column(ForeignKey("charging_sessions.id"), unique=True)
    amount_cents: Mapped[int]
    breakdown: Mapped[dict] = mapped_column(JSON)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    action: Mapped[str]
    entity_id: Mapped[str]
    actor: Mapped[str]
    detail: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(default=now)
