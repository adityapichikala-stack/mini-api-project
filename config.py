import math
import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    api_1_base_url: str
    api_2_base_url: str
    api_timeout_seconds: float


def load_settings() -> Settings:
    load_dotenv()

    required_variables = ("API_1_BASE_URL", "API_2_BASE_URL")
    missing_variables = [
        variable
        for variable in required_variables
        if not os.getenv(variable, "").strip()
    ]
    if missing_variables:
        names = ", ".join(missing_variables)
        raise RuntimeError(f"Missing required environment variable(s): {names}")

    timeout_value = os.getenv("API_TIMEOUT_SECONDS", "10")
    try:
        timeout_seconds = float(timeout_value)
    except ValueError as exc:
        raise RuntimeError("API_TIMEOUT_SECONDS must be a positive number") from exc

    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise RuntimeError("API_TIMEOUT_SECONDS must be a positive number")

    return Settings(
        api_1_base_url=os.environ["API_1_BASE_URL"].rstrip("/"),
        api_2_base_url=os.environ["API_2_BASE_URL"].rstrip("/"),
        api_timeout_seconds=timeout_seconds,
    )


settings = load_settings()
