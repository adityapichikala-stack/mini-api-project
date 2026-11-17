from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import JSONResponse

from clients.countries_client import CountriesNowClient
from clients.rates_client import FrankfurterClient
from config import settings
from exceptions import CountryNotFoundError, ExternalAPIError
from services.travel_service import TravelService

countries_client = CountriesNowClient(
    settings.api_1_base_url,
    settings.api_timeout_seconds,
)
rates_client = FrankfurterClient(
    settings.api_2_base_url,
    settings.api_timeout_seconds,
)
travel_service = TravelService(countries_client, rates_client)

app = FastAPI(
    title="Mini API Project",
    description="Travel budget and country information API",
    version="1.0.0",
)


def get_travel_service() -> TravelService:
    return travel_service


@app.exception_handler(CountryNotFoundError)
async def country_not_found_handler(
    request: Request,
    exc: CountryNotFoundError,
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ExternalAPIError)
async def external_api_error_handler(
    request: Request,
    exc: ExternalAPIError,
) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "message": "Mini API is running",
    }


@app.get("/countries/{name}")
async def get_country(
    name: str,
    service: TravelService = Depends(get_travel_service),
) -> dict[str, str | None]:
    return await service.get_country_info(name)


@app.get("/roam/{name}")
async def roam_country(
    name: str,
    budget_inr: float = Query(gt=0),
    service: TravelService = Depends(get_travel_service),
) -> dict[str, str | float | None]:
    return await service.get_roam_info(name, budget_inr)
