class NotFoundError(Exception):
    pass


class TripNotFoundError(NotFoundError):
    def __init__(self, trip_id: int) -> None:
        super().__init__(f"Trip {trip_id} not found")


class CountryNotFoundError(Exception):
    pass


class ExternalAPIError(Exception):
    pass
