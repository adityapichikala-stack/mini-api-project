from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def validate_not_past(value: date) -> date:
    if value < date.today():
        raise ValueError("travel_date cannot be in the past")
    return value


class TripCreate(BaseModel):
    traveller: str = Field(min_length=1)
    country: str = Field(min_length=1)
    budget_inr: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    travel_date: date

    @field_validator("traveller", "country")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value cannot be empty")
        return value

    @field_validator("travel_date")
    @classmethod
    def validate_travel_date(cls, value: date) -> date:
        return validate_not_past(value)


class TripUpdate(BaseModel):
    traveller: str | None = Field(default=None, min_length=1)
    country: str | None = Field(default=None, min_length=1)
    budget_inr: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )
    travel_date: date | None = None

    @field_validator("traveller", "country", "budget_inr", "travel_date", mode="before")
    @classmethod
    def reject_explicit_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("field cannot be null")
        return value

    @field_validator("traveller", "country")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("value cannot be empty")
        return value

    @field_validator("travel_date")
    @classmethod
    def validate_optional_travel_date(cls, value: date | None) -> date | None:
        if value is None:
            return None
        return validate_not_past(value)


class TripOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    traveller: str
    country: str
    currency_code: str
    budget_inr: Decimal
    travel_date: date
    created_at: datetime


class TripListOut(TripOut):
    rate: Decimal
    budget_local: Decimal
