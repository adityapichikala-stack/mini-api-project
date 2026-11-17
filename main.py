from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import Depends, FastAPI, Path, Query, Request, status
from fastapi.responses import JSONResponse, Response
from loguru import logger
from starlette.middleware.base import RequestResponseEndpoint

from clients.countries_client import CountriesNowClient
from clients.rates_client import FrankfurterClient
from config import settings
from db import (
    DatabaseSession,
    check_database_connection,
    create_tables,
    dispose_database_engine,
    get_db,
)
from exceptions import CountryNotFoundError, ExternalAPIError, NotFoundError
from logging_setup import configure_logging
from repositories.trip_repository import TripRepository
from schemas import TripCreate, TripListOut, TripOut, TripUpdate
from services.travel_service import TravelService
from services.trip_service import TripService

countries_client = CountriesNowClient(
    settings.api_1_base_url,
    settings.api_timeout_seconds,
)
rates_client = FrankfurterClient(
    settings.api_2_base_url,
    settings.api_timeout_seconds,
)
travel_service = TravelService(countries_client, rates_client)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    try:
        configure_logging()
        create_tables()
        check_database_connection()
        logger.info("Database connection established")
        yield
    finally:
        dispose_database_engine()


app = FastAPI(
    title="Mini API Project",
    description="Travel budget and country information API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def log_request(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    started_at = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = (perf_counter() - started_at) * 1000
        logger.error(
            "{} {} -> 500 in {:.2f} ms",
            request.method,
            request.url.path,
            elapsed_ms,
        )
        raise

    elapsed_ms = (perf_counter() - started_at) * 1000
    logger.info(
        "{} {} -> {} in {:.2f} ms",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


def get_travel_service() -> TravelService:
    return travel_service


def get_trip_service(
    session: DatabaseSession = Depends(get_db),
) -> TripService:
    repository = TripRepository(session)
    return TripService(repository, countries_client, rates_client)


@app.exception_handler(CountryNotFoundError)
async def country_not_found_handler(
    _request: Request,
    exc: CountryNotFoundError,
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ExternalAPIError)
async def external_api_error_handler(
    _request: Request,
    exc: ExternalAPIError,
) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(NotFoundError)
async def not_found_handler(
    _request: Request,
    exc: NotFoundError,
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


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


@app.post(
    "/trips",
    status_code=status.HTTP_201_CREATED,
    response_model=TripOut,
)
async def create_trip(
    data: TripCreate,
    service: TripService = Depends(get_trip_service),
) -> TripOut:
    return await service.create_trip(data)


@app.get("/trips", response_model=list[TripListOut])
async def list_trips(
    service: TripService = Depends(get_trip_service),
) -> list[TripListOut]:
    return await service.list_trips()


@app.get("/trips/{id}", response_model=TripOut)
async def get_trip(
    id: int = Path(gt=0),
    service: TripService = Depends(get_trip_service),
) -> TripOut:
    return await service.get_trip(id)


@app.patch("/trips/{id}", response_model=TripOut)
async def update_trip(
    data: TripUpdate,
    id: int = Path(gt=0),
    service: TripService = Depends(get_trip_service),
) -> TripOut:
    return await service.update_trip(id, data)


@app.delete("/trips/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trip(
    id: int = Path(gt=0),
    service: TripService = Depends(get_trip_service),
) -> Response:
    await service.delete_trip(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
