from clients.countries_client import CountriesNowClient
from clients.rates_client import FrankfurterClient


class TravelService:
    def __init__(
        self,
        countries_client: CountriesNowClient,
        rates_client: FrankfurterClient,
    ) -> None:
        self.countries_client = countries_client
        self.rates_client = rates_client

    async def get_country_info(self, country: str) -> dict[str, str | None]:
        country_name, capital = await self.countries_client.fetch_country_details(
            country
        )
        currency = await self.countries_client.fetch_country_currency(country)
        return {
            "country": country_name,
            "capital": capital,
            "currency": currency,
        }

    async def get_roam_info(
        self,
        country: str,
        budget_inr: float,
    ) -> dict[str, str | float | None]:
        country_name, currency = (
            await self.countries_client.fetch_country_currency_details(country)
        )
        rate, rate_date = await self.rates_client.fetch_exchange_rate_with_date(
            "INR",
            currency,
        )
        return {
            "country": country_name,
            "currency": currency,
            "rate": rate,
            "rate_date": rate_date,
            "budget_inr": budget_inr,
            "budget_local": round(budget_inr * rate, 2),
        }
