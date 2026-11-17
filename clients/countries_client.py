import httpx

from exceptions import CountryNotFoundError, ExternalAPIError


class CountriesNowClient:
    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def fetch_country_details(
        self,
        country: str,
    ) -> tuple[str, str | None]:
        data = await self._fetch_country_data("capital", country)
        name = data.get("name")
        capital = data.get("capital")
        if capital is not None and not isinstance(capital, str):
            raise ExternalAPIError("CountriesNow returned an invalid capital")
        return name if isinstance(name, str) else country, capital

    async def fetch_country_currency(self, country: str) -> str:
        data = await self._fetch_country_data("currency", country)
        currency = data.get("currency")
        if not isinstance(currency, str) or not currency:
            raise CountryNotFoundError("Currency information not found")
        return currency

    async def fetch_country_currency_details(
        self,
        country: str,
    ) -> tuple[str, str]:
        data = await self._fetch_country_data("currency", country)
        currency = data.get("currency")
        if not isinstance(currency, str) or not currency:
            raise CountryNotFoundError("Currency information not found")
        name = data.get("name")
        return name if isinstance(name, str) else country, currency

    async def fetch_country_capital(self, country: str) -> str | None:
        _, capital = await self.fetch_country_details(country)
        return capital

    async def _fetch_country_data(
        self,
        endpoint: str,
        country: str,
    ) -> dict[str, object]:
        url = f"{self.base_url}/{endpoint}/q"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url, params={"country": country})
                response.raise_for_status()
                payload = response.json()
        except httpx.TimeoutException as exc:
            raise ExternalAPIError("CountriesNow request timed out") from exc
        except httpx.HTTPStatusError as exc:
            raise ExternalAPIError(
                "CountriesNow returned an unsuccessful response"
            ) from exc
        except httpx.RequestError as exc:
            raise ExternalAPIError("CountriesNow is currently unavailable") from exc
        except (ValueError, TypeError) as exc:
            raise ExternalAPIError("CountriesNow returned an invalid response") from exc

        if not isinstance(payload, dict):
            raise ExternalAPIError("CountriesNow returned an invalid response")
        if payload.get("error"):
            raise CountryNotFoundError(f"Country '{country}' not found")
        if "data" not in payload:
            raise ExternalAPIError("CountriesNow returned an invalid response")
        data = payload.get("data")
        if data is None or data == {} or data == []:
            raise CountryNotFoundError(f"Country '{country}' not found")
        if not isinstance(data, dict):
            raise ExternalAPIError("CountriesNow returned an invalid response")
        return data
