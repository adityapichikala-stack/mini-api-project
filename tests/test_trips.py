import unittest
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from exceptions import CountryNotFoundError
from main import app


class TripEndpointTests(unittest.TestCase):
    def test_trip_crud_validation_currency_and_rate_cache(self) -> None:
        traveller = f"Trip-test-{uuid4()}"
        second_traveller = f"Trip-test-{uuid4()}"
        created_ids: list[int] = []

        async def lookup_currency(country: str) -> str:
            currencies = {"Japan": "JPY", "Canada": "CAD"}
            if country not in currencies:
                raise CountryNotFoundError(f"Country '{country}' not found")
            return currencies[country]

        with (
            TestClient(app) as client,
            patch(
                "main.countries_client.fetch_country_currency",
                new_callable=AsyncMock,
                side_effect=lookup_currency,
            ) as currency_lookup,
            patch(
                "main.rates_client.fetch_exchange_rate",
                new_callable=AsyncMock,
                return_value=0.0065,
            ) as rate_lookup,
        ):
            try:
                request_data = {
                    "traveller": traveller,
                    "country": "Japan",
                    "budget_inr": "1234.56",
                    "travel_date": date.today().isoformat(),
                }
                create_response = client.post("/trips", json=request_data)
                self.assertEqual(create_response.status_code, 201)
                first_trip = create_response.json()
                created_ids.append(first_trip["id"])
                self.assertEqual(first_trip["currency_code"], "JPY")
                self.assertEqual(first_trip["budget_inr"], "1234.56")
                currency_lookup.assert_awaited_once_with("Japan")

                second_response = client.post(
                    "/trips",
                    json={**request_data, "traveller": second_traveller},
                )
                self.assertEqual(second_response.status_code, 201)
                second_trip = second_response.json()
                created_ids.append(second_trip["id"])

                list_response = client.get("/trips")
                self.assertEqual(list_response.status_code, 200)
                trips = list_response.json()
                test_trips = [
                    trip
                    for trip in trips
                    if trip["traveller"] in {traveller, second_traveller}
                ]
                self.assertEqual(len(test_trips), 2)
                self.assertIn("rate", test_trips[0])
                self.assertIn("budget_local", test_trips[0])
                self.assertEqual(test_trips[0]["rate"], "0.0065")
                self.assertEqual(test_trips[0]["budget_local"], "8.02")
                self.assertEqual(
                    rate_lookup.await_count,
                    len({trip["currency_code"] for trip in trips}),
                )

                get_response = client.get(f"/trips/{first_trip['id']}")
                self.assertEqual(get_response.status_code, 200)
                self.assertEqual(get_response.json()["id"], first_trip["id"])
                self.assertNotIn("rate", get_response.json())

                update_response = client.patch(
                    f"/trips/{first_trip['id']}",
                    json={"country": "Canada", "budget_inr": "2000.00"},
                )
                self.assertEqual(update_response.status_code, 200)
                self.assertEqual(update_response.json()["country"], "Canada")
                self.assertEqual(update_response.json()["currency_code"], "CAD")
                self.assertEqual(update_response.json()["budget_inr"], "2000.00")
                currency_lookup.assert_any_await("Canada")

                invalid_country = client.patch(
                    f"/trips/{first_trip['id']}",
                    json={"country": "Atlantis"},
                )
                self.assertEqual(invalid_country.status_code, 404)

                invalid_id = client.get("/trips/not-an-integer")
                self.assertEqual(invalid_id.status_code, 422)
                invalid_range_id = client.get("/trips/0")
                self.assertEqual(invalid_range_id.status_code, 422)
                missing_trip = client.get("/trips/2147483647")
                self.assertEqual(missing_trip.status_code, 404)

                invalid_budget = client.post(
                    "/trips",
                    json={**request_data, "budget_inr": "0"},
                )
                self.assertEqual(invalid_budget.status_code, 422)
                negative_budget = client.post(
                    "/trips",
                    json={**request_data, "budget_inr": "-1"},
                )
                self.assertEqual(negative_budget.status_code, 422)
                missing_required_field = client.post(
                    "/trips",
                    json={
                        "traveller": traveller,
                        "country": "Japan",
                        "budget_inr": "100.00",
                    },
                )
                self.assertEqual(missing_required_field.status_code, 422)
                wrong_data_type = client.post(
                    "/trips",
                    json={**request_data, "traveller": 123},
                )
                self.assertEqual(wrong_data_type.status_code, 422)
                past_date = client.post(
                    "/trips",
                    json={
                        **request_data,
                        "travel_date": (date.today() - timedelta(days=1)).isoformat(),
                    },
                )
                self.assertEqual(past_date.status_code, 422)
                invalid_patch_date = client.patch(
                    f"/trips/{first_trip['id']}",
                    json={
                        "travel_date": (
                            date.today() - timedelta(days=1)
                        ).isoformat()
                    },
                )
                self.assertEqual(invalid_patch_date.status_code, 422)
                invalid_patch_budget = client.patch(
                    f"/trips/{first_trip['id']}",
                    json={"budget_inr": "-1"},
                )
                self.assertEqual(invalid_patch_budget.status_code, 422)
                invalid_patch_null = client.patch(
                    f"/trips/{first_trip['id']}",
                    json={"traveller": None},
                )
                self.assertEqual(invalid_patch_null.status_code, 422)

                delete_response = client.delete(f"/trips/{first_trip['id']}")
                self.assertEqual(delete_response.status_code, 204)
                self.assertEqual(delete_response.content, b"")
                created_ids.remove(first_trip["id"])

                deleted_trip = client.get(f"/trips/{first_trip['id']}")
                self.assertEqual(deleted_trip.status_code, 404)
            finally:
                for trip_id in created_ids:
                    client.delete(f"/trips/{trip_id}")


if __name__ == "__main__":
    unittest.main()
