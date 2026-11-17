from decimal import Decimal, ROUND_HALF_UP

from clients.countries_client import CountriesNowClient
from clients.rates_client import FrankfurterClient
from exceptions import TripNotFoundError
from repositories.trip_repository import TripRepository
from schemas import TripCreate, TripListOut, TripOut, TripUpdate


class TripService:
    def __init__(
        self,
        repository: TripRepository,
        countries_client: CountriesNowClient,
        rates_client: FrankfurterClient,
    ) -> None:
        self.repository = repository
        self.countries_client = countries_client
        self.rates_client = rates_client

    async def create_trip(self, data: TripCreate) -> TripOut:
        currency_code = await self.countries_client.fetch_country_currency(
            data.country
        )
        trip = self.repository.add(
            traveller=data.traveller,
            country=data.country,
            currency_code=currency_code,
            budget_inr=data.budget_inr,
            travel_date=data.travel_date,
        )
        return TripOut.model_validate(trip)

    async def get_trip(self, trip_id: int) -> TripOut:
        trip = self.repository.get(trip_id)
        if trip is None:
            raise TripNotFoundError(trip_id)
        return TripOut.model_validate(trip)

    async def list_trips(self) -> list[TripListOut]:
        trips = self.repository.list()
        rates_by_currency: dict[str, Decimal] = {}
        results: list[TripListOut] = []

        for trip in trips:
            currency_code = trip.currency_code
            if currency_code not in rates_by_currency:
                exchange_rate = await self.rates_client.fetch_exchange_rate(
                    "INR",
                    currency_code,
                )
                rates_by_currency[currency_code] = Decimal(str(exchange_rate))

            rate = rates_by_currency[currency_code]
            budget_local = (trip.budget_inr * rate).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )
            trip_data = TripOut.model_validate(trip).model_dump()
            results.append(
                TripListOut(
                    **trip_data,
                    rate=rate,
                    budget_local=budget_local,
                )
            )

        return results

    async def update_trip(
        self,
        trip_id: int,
        data: TripUpdate,
    ) -> TripOut:
        existing_trip = self.repository.get(trip_id)
        if existing_trip is None:
            raise TripNotFoundError(trip_id)

        values = data.model_dump(exclude_unset=True, exclude_none=True)
        updated_country = values.get("country")
        if updated_country is not None and updated_country != existing_trip.country:
            values["currency_code"] = await (
                self.countries_client.fetch_country_currency(updated_country)
            )

        trip = self.repository.update(trip_id, values)
        if trip is None:
            raise TripNotFoundError(trip_id)
        return TripOut.model_validate(trip)

    async def delete_trip(self, trip_id: int) -> None:
        if not self.repository.delete(trip_id):
            raise TripNotFoundError(trip_id)
