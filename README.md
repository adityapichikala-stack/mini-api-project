# Mini API Project

Mini API Project provides country information and converts an INR travel budget to the local currency. CountriesNow supplies country and currency data, and Frankfurter supplies exchange rates.

## Requirements

- Python 3.14
- Docker Desktop for container builds and runs
- Postman for manual API testing

## Project structure

```text
mini-api-project/
├── clients/
│   ├── __init__.py
│   ├── countries_client.py
│   └── rates_client.py
├── repositories/
│   ├── __init__.py
│   └── trip_repository.py
├── postman/
│   └── Mini API Project.postman_collection.json
├── services/
│   ├── __init__.py
│   ├── travel_service.py
│   └── trip_service.py
├── db.py
├── schemas.py
├── tests/
│   ├── test_api.py
│   └── test_trips.py
├── .dockerignore
├── .env.example
├── .gitignore
├── config.py
├── docker-compose.yml
├── Dockerfile
├── exceptions.py
├── main.py
└── requirements.txt
```

## Local installation

In PowerShell, change to the project folder and create the virtual environment:

```powershell
cd C:\Users\adity\OneDrive\Desktop\mini_api_project
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, use Command Prompt instead:

```cmd
.venv\Scripts\activate.bat
```

## Environment configuration

Copy the example file to `.env`:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

If `.env` already exists, preserve its API URL values and add the database and logging settings shown in `.env.example`. Set these values in `.env`:

| Variable | Description | Default |
|---|---|---|
| `API_1_BASE_URL` | CountriesNow API base URL | Required |
| `API_2_BASE_URL` | Frankfurter API base URL | Required |
| `API_TIMEOUT_SECONDS` | Timeout for external API requests, in seconds | `10` |
| `DATABASE_URL` | SQLAlchemy PostgreSQL URL | Required |
| `LOG_LEVEL` | Loguru level | `INFO` |
| `POSTGRES_USER` | PostgreSQL development user | Required by Compose |
| `POSTGRES_PASSWORD` | PostgreSQL development password | Required by Compose |
| `POSTGRES_DB` | PostgreSQL database name | Required by Compose |
| `POSTGRES_PORT` | Host port mapped to PostgreSQL | `5432` |
| `APP_PORT` | Host port mapped to FastAPI | `8000` |

The application fails during startup with the missing variable name if an API base URL or `DATABASE_URL` is unset. The example database credentials are for development only; change them for any non-local deployment. `.env` is excluded from Git and Docker build context. Keep local values in `.env`; do not commit it.

`LOG_LEVEL` controls Loguru output. Application logs are written to standard output. HTTP requests include method, path, status, and elapsed time; external API logs include API name, path, status or failure kind, and latency. Request paths are logged without query strings.

For local Python runs, `DATABASE_URL` should use `localhost`:

```text
postgresql+psycopg://mini_api:change-me@localhost:5432/mini_api
```

In Compose, the app uses the database service name `db` instead of `localhost`. Compose overrides `DATABASE_URL` inside the app container to use that hostname.

## Run locally

With `.venv` activated and `.env` configured:

```powershell
python -m uvicorn main:app --reload
```

The API is available at `http://127.0.0.1:8000`. Interactive API documentation is at `http://127.0.0.1:8000/docs`.

## API endpoints

### Health

```http
GET http://127.0.0.1:8000/health
```

Example response:

```json
{
  "status": "healthy",
  "message": "Mini API is running"
}
```

### Country information

```http
GET http://127.0.0.1:8000/countries/Japan
```

Example response:

```json
{
  "country": "Japan",
  "capital": "Tokyo",
  "currency": "JPY"
}
```

### Travel budget conversion

```http
GET http://127.0.0.1:8000/roam/Japan?budget_inr=150000
```

Example response (the rate and date vary):

```json
{
  "country": "Japan",
  "currency": "JPY",
  "rate": 0.0065,
  "rate_date": "2026-11-15",
  "budget_inr": 150000.0,
  "budget_local": 975.0
}
```

### Errors

- `404 Not Found`: CountriesNow has no information for the requested country.
- `503 Service Unavailable`: An external API timed out, was unavailable, or returned an invalid response.
- `422 Unprocessable Entity`: `budget_inr` is missing, invalid, zero, or negative.

## Trip API

Trip routes store and retrieve trip records in PostgreSQL. `travel_date` must be today or a future date. Money values are stored and calculated with decimal precision.

### Create a trip

```http
POST http://127.0.0.1:8000/trips
Content-Type: application/json
```

```json
{
  "traveller": "Avery",
  "country": "Japan",
  "budget_inr": "150000.00",
  "travel_date": "2027-01-15"
}
```

The API looks up the country's currency before saving and returns HTTP `201` with the trip, including its generated `id` and `created_at`.

### List trips

```http
GET http://127.0.0.1:8000/trips
```

Each list item includes the trip fields plus `rate` and `budget_local`. Decimal-valued money and rate fields are serialized as JSON strings to preserve decimal precision. The service requests each distinct currency's INR exchange rate at most once per list request.

### Get one trip

```http
GET http://127.0.0.1:8000/trips/1
```

### Update a trip

```http
PATCH http://127.0.0.1:8000/trips/1
Content-Type: application/json
```

```json
{
  "country": "Canada",
  "budget_inr": "175000.00"
}
```

Only provided fields change. Changing the country performs a new currency lookup before updating the record.

### Delete a trip

```http
DELETE http://127.0.0.1:8000/trips/1
```

Successful deletion returns `204 No Content` with an empty body. Invalid request data or non-positive IDs return `422`; a valid but nonexistent trip ID returns `404`.

Trip create fields are all required. PATCH fields may be omitted, but supplied fields cannot be null; supplied budgets must be positive and supplied travel dates must be today or later. Decimal money and rate values serialize as JSON strings.

Import `postman/Mini API Project.postman_collection.json` in Postman and run the `Day 2 API Tests` or `Day 3 Trip API Tests` folder. Its `base_url` collection variable defaults to `http://127.0.0.1:8000`; change it to the published `APP_PORT` when using a non-default host port.

## Docker Compose with PostgreSQL

Start PostgreSQL and the API together:

```powershell
docker compose config --quiet
docker compose up --build -d
docker compose ps
```

The API container waits for the database healthcheck to pass, then creates the trips table and checks the database connection during application startup. Database sessions are opened per request and closed afterwards. The database data is stored in the named `postgres_data` volume and survives container recreation. Stop the services while retaining data with:

```powershell
docker compose down
```

To delete the database data too, run `docker compose down --volumes`; this permanently removes the named database volume.

Compose publishes PostgreSQL on host port `5432` and the API on `8000` by default. If those ports are already in use, set `POSTGRES_PORT` and `APP_PORT` in `.env`, or set alternate values in PowerShell before starting Compose, for example:

```powershell
$env:POSTGRES_PORT = "5433"
$env:APP_PORT = "8001"
docker compose up --build -d
```

In that case, the API is at `http://127.0.0.1:8001`; the app-to-database URL still uses `db:5432` inside the Compose network.

## Standalone Docker

Build the image from the project directory:

```powershell
docker build -t mini-api-project .
```

Use Docker Compose to run the image with PostgreSQL; the standalone image requires a separately reachable database and is not sufficient by itself.

## Design

- **Adapter pattern:** `CountriesNowClient` and `FrankfurterClient` wrap their respective external APIs, handle transport and response errors, and expose simple Python values.
- **Facade pattern:** `TravelService` combines client operations into country-information and budget-conversion features.
- **Dependency injection:** `main.py` wires the clients into `TravelService`; the route dependency provides the service to each handler.
- **Single Responsibility Principle:** Configuration, external API access, travel logic, HTTP routing, and exception translation live in separate modules.

## Tests

Run the API, database-backed trip API, and configuration tests inside the Compose app container:

```powershell
docker compose exec -T app python -m unittest discover -s tests -v
```
