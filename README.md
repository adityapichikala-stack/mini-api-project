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
├── postman/
│   └── Mini API Project.postman_collection.json
├── services/
│   ├── __init__.py
│   └── travel_service.py
├── tests/
│   └── test_api.py
├── .dockerignore
├── .env.example
├── .gitignore
├── config.py
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
Copy-Item .env.example .env
```

Set these values in `.env`:

| Variable | Description | Default |
|---|---|---|
| `API_1_BASE_URL` | CountriesNow API base URL | Required |
| `API_2_BASE_URL` | Frankfurter API base URL | Required |
| `API_TIMEOUT_SECONDS` | Timeout for external API requests, in seconds | `10` |

The application fails during startup with the missing variable name if either API base URL is unset. `.env` is excluded from Git and Docker build context. Keep real values in `.env`; do not commit it.

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

Import `postman/Mini API Project.postman_collection.json` in Postman and run the `Day 2 API Tests` folder. Its `base_url` collection variable defaults to `http://127.0.0.1:8000`.

## Docker

Build the image from the project directory:

```powershell
docker build -t mini-api-project .
```

Run the container with your local `.env` file:

```powershell
docker run --name mini-api-project --env-file .env -p 8000:8000 mini-api-project
```

The container listens on port 8000. Test it using the same API URLs with `http://127.0.0.1:8000` as the base URL. Stop it with `Ctrl+C`, or stop a background container with:

```powershell
docker stop mini-api-project
```

## Design

- **Adapter pattern:** `CountriesNowClient` and `FrankfurterClient` wrap their respective external APIs, handle transport and response errors, and expose simple Python values.
- **Facade pattern:** `TravelService` combines client operations into country-information and budget-conversion features.
- **Dependency injection:** `main.py` wires the clients into `TravelService`; the route dependency provides the service to each handler.
- **Single Responsibility Principle:** Configuration, external API access, travel logic, HTTP routing, and exception translation live in separate modules.

## Tests

Run the API and configuration tests from PowerShell:

```powershell
python -m unittest discover -s tests -v
```
