import math

import httpx

from exceptions import ExternalAPIError


class FrankfurterClient:
    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def fetch_exchange_rate(self, base: str, quote: str) -> float:
        rate, _ = await self.fetch_exchange_rate_with_date(base, quote)
        return rate

    async def fetch_exchange_rate_with_date(
        self,
        base: str,
        quote: str,
    ) -> tuple[float, str | None]:
        url = f"{self.base_url}/rate/{base}/{quote}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url)
                response.raise_for_status()
                payload = response.json()
        except httpx.TimeoutException as exc:
            raise ExternalAPIError("Frankfurter request timed out") from exc
        except httpx.HTTPStatusError as exc:
            raise ExternalAPIError(
                "Frankfurter returned an unsuccessful response"
            ) from exc
        except httpx.RequestError as exc:
            raise ExternalAPIError("Frankfurter is currently unavailable") from exc
        except (ValueError, TypeError) as exc:
            raise ExternalAPIError("Frankfurter returned an invalid response") from exc

        if not isinstance(payload, dict):
            raise ExternalAPIError("Frankfurter returned an invalid response")
        raw_rate = payload.get("rate")
        if isinstance(raw_rate, bool):
            raise ExternalAPIError("Exchange rate could not be retrieved")
        try:
            rate = float(raw_rate)
        except (TypeError, ValueError) as exc:
            raise ExternalAPIError(
                "Exchange rate could not be retrieved"
            ) from exc
        if not math.isfinite(rate) or rate <= 0:
            raise ExternalAPIError("Exchange rate could not be retrieved")

        rate_date = payload.get("date")
        if rate_date is not None and not isinstance(rate_date, str):
            raise ExternalAPIError("Frankfurter returned an invalid rate date")
        return rate, rate_date
