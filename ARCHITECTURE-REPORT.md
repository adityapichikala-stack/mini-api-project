# Mini API Project: Client, Server, Adapter, and Facade Report

## 1. Overview

This project is an HTTP API server built with FastAPI. It exposes country information and travel-budget conversion routes. When a route needs external data, the server delegates to a travel service, which coordinates API clients for CountriesNow and Frankfurter.

The project has two different kinds of client/server communication:

1. A caller such as Postman is an HTTP client. It sends a request to this project's FastAPI server.
2. The project's CountriesNow and Frankfurter client classes are also HTTP clients. They send outbound requests from the server to those external API servers.

In other words, this project is the server to Postman, and a client to the external APIs.

## 2. Component responsibilities

| Component | File | Responsibility |
|---|---|---|
| API server and composition root | [main.py](./main.py) | Creates the FastAPI app, constructs and wires clients and service, defines routes, and maps application exceptions to HTTP responses. |
| Configuration | [config.py](./config.py) | Loads `.env`, validates required base URLs, and sets a positive API timeout (10 seconds by default). |
| Domain exceptions | [exceptions.py](./exceptions.py) | Defines `CountryNotFoundError` and `ExternalAPIError` without coupling them to FastAPI. |
| CountriesNow adapter | [clients/countries_client.py](./clients/countries_client.py) | Makes async HTTP requests to CountriesNow, validates its response structure, and returns country/currency/capital values. |
| Frankfurter adapter | [clients/rates_client.py](./clients/rates_client.py) | Makes async HTTP requests to Frankfurter, validates the rate and date, and returns Python values. |
| Travel facade | [services/travel_service.py](./services/travel_service.py) | Coordinates client calls and implements country-information and budget-conversion use cases. |

## 3. Server and request flow

Uvicorn runs the ASGI application object named `app` from `main.py`. FastAPI receives incoming HTTP requests, matches the method and path to a route, validates route parameters, calls the route function, and serializes its returned Python dictionary as JSON.

For service-backed routes, `Depends(get_travel_service)` asks FastAPI to provide a `TravelService`. The route passes the request values to that service and returns the resulting data. It does not construct an outbound HTTP request itself.

The health route is independent of the external APIs and directly returns:

```json
{
  "status": "healthy",
  "message": "Mini API is running"
}
```

### `GET /countries/{name}`

For `GET /countries/Japan`:

1. FastAPI extracts `Japan` from the URL.
2. The route calls `TravelService.get_country_info("Japan")`.
3. The service asks `CountriesNowClient` for country name and capital, then for currency.
4. The client calls CountriesNow's capital and currency endpoints and converts its response into simple Python values.
5. The service assembles the `country`, `capital`, and `currency` fields.
6. FastAPI serializes the dictionary as the HTTP JSON response.

### `GET /roam/{name}?budget_inr=...`

For `GET /roam/Japan?budget_inr=150000`:

1. FastAPI extracts `Japan` and parses `budget_inr` as a number.
2. `Query(gt=0)` rejects zero and negative values before the service is called.
3. The route calls `TravelService.get_roam_info("Japan", 150000)`.
4. The service asks `CountriesNowClient` for the country name and currency.
5. The service passes `INR` and the target currency to `FrankfurterClient`.
6. The rate client retrieves and validates the exchange rate and date.
7. The service calculates `budget_local = budget_inr * rate`, rounds the converted amount to two decimal places, and assembles the response.
8. FastAPI serializes the result as JSON.

## 4. Adapter pattern

The external APIs each have their own URL layout, transport details, and response format. The adapter classes hide those details behind methods expressed in the application's vocabulary:

- `CountriesNowClient.fetch_country_details(...)`
- `CountriesNowClient.fetch_country_currency(...)`
- `CountriesNowClient.fetch_country_currency_details(...)`
- `FrankfurterClient.fetch_exchange_rate(...)`
- `FrankfurterClient.fetch_exchange_rate_with_date(...)`

For example, `CountriesNowClient` builds the `/capital/q` or `/currency/q` URL, sends the country as a query parameter, parses the JSON `data` object, and returns a Python string or tuple. `FrankfurterClient` builds the `/rate/{base}/{quote}` URL and converts the returned rate to a validated `float`.

Both adapters contain the `httpx.AsyncClient` usage and translate timeouts, connection/request failures, unsuccessful HTTP responses, and malformed payloads into `ExternalAPIError`. An unknown country or missing country data becomes `CountryNotFoundError` in the CountriesNow adapter.

This isolates the rest of the application from vendor-specific HTTP and JSON details. If an external API changes, the corresponding adapter is the primary place to update.

## 5. Facade pattern

`TravelService` is the facade over the two adapters. It offers higher-level operations that match what the application needs:

- `get_country_info(country)` coordinates country details and currency retrieval.
- `get_roam_info(country, budget_inr)` gets the currency, obtains its INR exchange rate, and calculates the converted budget.

The API routes use these operations instead of coordinating multiple low-level requests themselves. `TravelService` has no direct HTTP requests, `httpx` import, FastAPI dependency, or HTTP status code handling. It focuses on the application use case.

## 6. Dependency injection and wiring

At module import, `main.py` reads the settings object from `config.py`, creates one `CountriesNowClient` and one `FrankfurterClient`, and passes both instances into `TravelService`. This constructor injection is dependency injection: the service receives the collaborators it needs instead of creating them internally.

`get_travel_service()` exposes the wired service through FastAPI's dependency mechanism. The route parameters declare `Depends(get_travel_service)`, which lets FastAPI provide the service and lets tests replace it with a stub.

## 7. Configuration and error mapping

`config.py` loads environment variables with `python-dotenv`. `API_1_BASE_URL` and `API_2_BASE_URL` are required; a missing or blank value raises a startup-time `RuntimeError` that names the missing variable. `API_TIMEOUT_SECONDS` defaults to `10` and must be positive and finite.

Clients raise application exceptions; `main.py` is the HTTP boundary that maps them:

| Application exception or input issue | HTTP result |
|---|---|
| `CountryNotFoundError` | `404` with a `detail` message |
| `ExternalAPIError` | `503` with a `detail` message |
| Non-positive `budget_inr` | FastAPI validation response `422` |

This keeps HTTP status codes out of the adapters and service.

## 8. Design benefits

- **Separation of responsibilities:** configuration, vendor HTTP access, use-case logic, and HTTP routing are in separate modules.
- **Testability:** tests can inject stub clients or override the FastAPI service dependency without contacting external services.
- **Vendor isolation:** the service consumes methods and values rather than external JSON structures.
- **Consistent error handling:** client failures are translated once at the API boundary.
- **Async I/O:** outbound network requests use `httpx.AsyncClient`, allowing the server to await I/O without blocking the route's event loop.

## 9. Important implementation detail

The current clients create an `httpx.AsyncClient` for each outbound operation using the configured timeout, then close it at the end of that operation. This is straightforward and ensures cleanup. It does not reuse a shared connection pool across requests; a future optimization could manage a long-lived client in the FastAPI lifespan if connection reuse becomes important.

The API's error-handling and response structures can be exercised with the tests in [tests/test_api.py](./tests/test_api.py). Manual request examples are in [README.md](./README.md).
