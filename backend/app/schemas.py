from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

Money = Annotated[Decimal, Field(ge=0, le=10000, max_digits=12, decimal_places=6)]
Identifier = Annotated[str, Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")]
Month = Annotated[str, Field(pattern=r"^20\d{2}-(0[1-9]|1[0-2])$")]


class SessionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: Identifier
    charger_id: Identifier
    user_id: Identifier | None = None
    unit_id: Identifier | None = None
    vehicle_id: Identifier | None = None
    started_at: AwareDatetime
    ended_at: AwareDatetime
    start_meter_kwh: Annotated[Decimal, Field(ge=0, le=100000000, decimal_places=3)]
    end_meter_kwh: Annotated[Decimal, Field(ge=0, le=100000000, decimal_places=3)]
    energy_kwh: Annotated[Decimal | None, Field(ge=0, le=10000, decimal_places=3)] = None
    idle_minutes: Annotated[int, Field(ge=0, le=1440)] = 0
    status: Literal["completed", "interrupted"] = "completed"
    stop_reason: Annotated[str, Field(min_length=1, max_length=100)] = "vehicle_disconnected"
    cost_center: Literal["resident", "promotion"] = "resident"
    source: Literal["simulator", "normalized_import"] = "normalized_import"

    @model_validator(mode="after")
    def coherent_time(self):
        duration = (self.ended_at - self.started_at).total_seconds() / 60
        if duration <= 0 or duration > 7 * 24 * 60:
            raise ValueError("A duração deve ser maior que zero e de até sete dias.")
        if self.idle_minutes >= duration:
            raise ValueError("Ociosidade deve ser menor que a duração total.")
        return self


class LoginInput(BaseModel):
    email: Annotated[str, Field(max_length=150)]
    password: Annotated[str, Field(max_length=256)]


class ReviewInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    decision: Literal["approve", "exclude"]
    reason: Annotated[str, Field(min_length=10, max_length=500)]


class TariffInput(BaseModel):
    tariff_kwh: Money
    session_fee: Annotated[Decimal, Field(ge=0, le=10000, decimal_places=2)] = Decimal(0)
    idle_fee: Annotated[Decimal, Field(ge=0, le=10000, decimal_places=4)] = Decimal(0)
    idle_grace_minutes: Annotated[int, Field(ge=0, le=1440)] = 15
    loss_percent: Annotated[Decimal, Field(ge=0, le=30, decimal_places=4)] = Decimal(0)
    fixed_fee: Annotated[Decimal, Field(ge=0, le=10000, decimal_places=2)] = Decimal(0)


class CreditInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    id: Identifier
    unit_id: Identifier
    amount: Annotated[Decimal, Field(gt=0, le=10000, decimal_places=2)]
    reason: Annotated[str, Field(min_length=10, max_length=500)]


class SimulationInput(BaseModel):
    scenario: Literal[
        "normal", "interrupted", "anomaly", "unidentified", "meter_error", "promotion"
    ] = "normal"
    month: Month = "2026-09"
    unit_id: Identifier = "ap101"
