from collections.abc import Mapping
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from db import DatabaseSession, Trip


class TripRepository:
    def __init__(self, session: DatabaseSession) -> None:
        self.session = session

    def add(
        self,
        traveller: str,
        country: str,
        currency_code: str,
        budget_inr: Decimal,
        travel_date: date,
    ) -> Trip:
        trip = Trip(
            traveller=traveller,
            country=country,
            currency_code=currency_code,
            budget_inr=budget_inr,
            travel_date=travel_date,
        )
        self.session.add(trip)
        self.session.commit()
        self.session.refresh(trip)
        return trip

    def get(self, trip_id: int) -> Trip | None:
        return self.session.get(Trip, trip_id)

    def list(self) -> list[Trip]:
        statement = select(Trip).order_by(Trip.id)
        return list(self.session.scalars(statement).all())

    def update(self, trip_id: int, values: Mapping[str, object]) -> Trip | None:
        trip = self.get(trip_id)
        if trip is None:
            return None

        for field, value in values.items():
            setattr(trip, field, value)
        self.session.commit()
        self.session.refresh(trip)
        return trip

    def delete(self, trip_id: int) -> bool:
        trip = self.get(trip_id)
        if trip is None:
            return False
        self.session.delete(trip)
        self.session.commit()
        return True
