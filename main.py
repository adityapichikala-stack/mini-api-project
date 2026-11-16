
import os

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query


load_dotenv()

API_1_BASE_URL = os.getenv("API_1_BASE_URL")
API_2_BASE_URL = os.getenv("API_2_BASE_URL")

TIMEOUT = 10.0

app = FastAPI(
    title="Mini API Project",
    description="Travel budget and country information API",
    version="1.0.0"
)




async def call_external_api(url: str, params: dict = None):
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=503,
            detail="External API request timed out"
        )

    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"External API returned status {exc.response.status_code}"
        )

    except (httpx.RequestError, ValueError):
        raise HTTPException(
            status_code=503,
            detail="External API is currently unavailable"
        )




def validate_country_response(data: dict, country: str):

    if data.get("error") or not data.get("data"):
        raise HTTPException(
            status_code=404,
            detail=f"Country '{country}' not found"
        )

    return data["data"]




@app.get("/health")
async def health_check():

    return {
        "status": "healthy",
        "message": "Mini API is running"
    }




@app.get("/countries/{name}")
async def get_country(name: str):

    capital_url = f"{API_1_BASE_URL}/capital/q"
    currency_url = f"{API_1_BASE_URL}/currency/q"

    # Get capital
    capital_response = await call_external_api(
        capital_url,
        params={"country": name}
    )

    capital_data = validate_country_response(
        capital_response, name
    )

    # Get currency
    currency_response = await call_external_api(
        currency_url,
        params={"country": name}
    )

    currency_data = validate_country_response(
        currency_response, name
    )

    return {
        "country": capital_data.get("name", name),
        "capital": capital_data.get("capital"),
        "currency": currency_data.get("currency")
    }




@app.get("/roam/{name}")
async def roam_country(
    name: str,
    budget_inr: float = Query(gt=0)
):

    currency_url = f"{API_1_BASE_URL}/currency/q"

    currency_response = await call_external_api(
        currency_url,
        params={"country": name}
    )

    currency_data = validate_country_response(
        currency_response, name
    )

    currency_code = currency_data.get("currency")

    if not currency_code:
        raise HTTPException(
            status_code=404,
            detail="Currency information not found"
        )

  
    rate_url = (
        f"{API_2_BASE_URL}/rate/INR/{currency_code}"
    )

    rate_response = await call_external_api(rate_url)

    rate = rate_response.get("rate")

    if rate is None:
        raise HTTPException(
            status_code=503,
            detail="Exchange rate could not be retrieved"
        )

   
    budget_local = budget_inr * rate

  
    return {
        "country": currency_data.get("name", name),
        "currency": currency_code,
        "rate": rate,
        "rate_date": rate_response.get("date"),
        "budget_inr": budget_inr,
        "budget_local": round(budget_local, 2)
    }
