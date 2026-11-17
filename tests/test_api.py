import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from clients import countries_client as countries_client_module
from clients import rates_client as rates_client_module
from clients.countries_client import CountriesNowClient
from clients.rates_client import FrankfurterClient
from exceptions import CountryNotFoundError, ExternalAPIError
from main import app, get_travel_service


class StubCountriesClient:
    async def fetch_country_details(
        self,
        country: str,
    ) -> tuple[str, str]:
        if country == "Atlantis":
            raise CountryNotFoundError(f"Country '{country}' not found")
        return country, "Tokyo"

    async def fetch_country_capital(self, country: str) -> str:
        if country == "Atlantis":
            raise CountryNotFoundError(f"Country '{country}' not found")
        return "Tokyo"

    async def fetch_country_currency_details(
        self,
        country: str,
    ) -> tuple[str, str]:
        if country == "Atlantis":
            raise CountryNotFoundError(f"Country '{country}' not found")
        return country, "JPY"

    async def fetch_country_currency(self, country: str) -> str:
        if country == "Atlantis":
            raise CountryNotFoundError(f"Country '{country}' not found")
        return "JPY"


class StubRatesClient:
    async def fetch_exchange_rate_with_date(
        self,
        base: str,
        quote: str,
    ) -> tuple[float, str]:
        return 0.0065, "2026-11-15"


class FailingCountriesClient(StubCountriesClient):
    async def fetch_country_details(self, country: str) -> tuple[str, str]:
        raise ExternalAPIError("CountriesNow request timed out")


class StubHTTPResponse:
    status_code = 200

    def __init__(self, payload: object) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self.payload


class StubAsyncHTTPClient:
    def __init__(
        self,
        response: StubHTTPResponse | None = None,
        failure: Exception | None = None,
        **kwargs: object,
    ) -> None:
        self.response = response
        self.failure = failure

    async def __aenter__(self) -> "StubAsyncHTTPClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def get(self, *args: object, **kwargs: object) -> StubHTTPResponse:
        if self.failure:
            raise self.failure
        if self.response is None:
            raise AssertionError("A response or failure must be provided")
        return self.response


class TravelApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        app.dependency_overrides[get_travel_service] = lambda: app.state.test_service

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        if hasattr(app.state, "test_service"):
            del app.state.test_service

    def set_service(
        self,
        countries_client: StubCountriesClient | None = None,
    ) -> None:
        from services.travel_service import TravelService

        selected_countries_client = countries_client or StubCountriesClient()
        app.state.test_service = TravelService(
            selected_countries_client,
            StubRatesClient(),
        )

    def test_health_response(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "healthy", "message": "Mini API is running"},
        )

    def test_country_response(self) -> None:
        self.set_service()
        response = self.client.get("/countries/Japan")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"country": "Japan", "capital": "Tokyo", "currency": "JPY"},
        )

    def test_roam_response(self) -> None:
        self.set_service()
        response = self.client.get("/roam/Japan?budget_inr=150000")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "country": "Japan",
                "currency": "JPY",
                "rate": 0.0065,
                "rate_date": "2026-11-15",
                "budget_inr": 150000,
                "budget_local": 975.0,
            },
        )

    def test_unknown_country_returns_404(self) -> None:
        self.set_service()
        response = self.client.get("/countries/Atlantis")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {"detail": "Country 'Atlantis' not found"},
        )

    def test_zero_and_negative_budgets_return_422(self) -> None:
        self.set_service()
        for budget in ("0", "-100"):
            with self.subTest(budget=budget):
                response = self.client.get(
                    f"/roam/Japan?budget_inr={budget}"
                )
                self.assertEqual(response.status_code, 422)

    def test_external_api_error_returns_503(self) -> None:
        self.set_service(FailingCountriesClient())
        response = self.client.get("/countries/Japan")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {"detail": "CountriesNow request timed out"},
        )

    def test_startup_fails_with_missing_api_urls(self) -> None:
        root = Path(__file__).resolve().parents[1]
        environment = os.environ.copy()
        environment["API_1_BASE_URL"] = ""
        environment["API_2_BASE_URL"] = ""
        with tempfile.TemporaryDirectory() as working_directory:
            environment["PYTHONPATH"] = str(root)
            result = subprocess.run(
                [sys.executable, "-c", "import config"],
                cwd=working_directory,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("API_1_BASE_URL", result.stderr)
        self.assertIn("API_2_BASE_URL", result.stderr)


class ClientErrorTests(unittest.IsolatedAsyncioTestCase):
    async def test_countries_timeout_becomes_external_api_error(self) -> None:
        timeout = countries_client_module.httpx.TimeoutException("timeout")
        fake_client = StubAsyncHTTPClient(failure=timeout)
        client = CountriesNowClient("https://example.test", 10)
        with patch(
            "clients.countries_client.httpx.AsyncClient",
            return_value=fake_client,
        ):
            with self.assertRaisesRegex(ExternalAPIError, "timed out"):
                await client.fetch_country_currency("Japan")

    async def test_invalid_rate_becomes_external_api_error(self) -> None:
        fake_client = StubAsyncHTTPClient(
            response=StubHTTPResponse({"rate": "invalid", "date": "2026-11-15"})
        )
        client = FrankfurterClient("https://example.test", 10)
        with patch(
            "clients.rates_client.httpx.AsyncClient",
            return_value=fake_client,
        ):
            with self.assertRaisesRegex(
                ExternalAPIError,
                "Exchange rate could not be retrieved",
            ):
                await client.fetch_exchange_rate("INR", "JPY")


if __name__ == "__main__":
    unittest.main()
