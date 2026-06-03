from __future__ import annotations
import os
from typing import Dict, Any
from dotenv import load_dotenv
load_dotenv()

class Config:
    @staticmethod
    def get_env_float(key: str, default: float) -> float:
        try:
            return float(os.getenv(key))
        except (ValueError, TypeError):
            return default

    @staticmethod
    def get_env_int(key: str, default: int) -> int:
        try:
            return int(os.getenv(key, default))
        except (ValueError, TypeError):
            return default

    @staticmethod
    def get_env_str(key: str, default: str) -> str:
        return os.getenv(key, default)

    @staticmethod
    def get_env_bool(key: str, default: bool) -> bool:
        value = os.getenv(key)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    # Algorithm Settings
    SA_INITIAL_TEMP = get_env_float("SA_INITIAL_TEMP", 1000.0)
    SA_COOLING_RATE = get_env_float("SA_COOLING_RATE", 0.995)
    SA_ITERATIONS = get_env_int("SA_ITERATIONS", 10000)
    SA_RUNS = get_env_int("SA_RUNS", 10)
    MAX_WORKERS = get_env_int("MAX_WORKERS", 5)
    OUTPUT_DIR = get_env_str("OUTPUT_DIR", "./results")
    ONE_SHIFT_PER_PERSON_PER_CALENDAR_DAY = get_env_bool("ONE_SHIFT_PER_PERSON_PER_CALENDAR_DAY", True)

    # Business Logic Parameters (Primary Source)
    LAMBDA_DIST = get_env_float("LAMBDA_DIST", 50.0)
    LAMBDA_LOAD = get_env_float("LAMBDA_LOAD", 20.0)
    LAMBDA_RECENCY = get_env_float("LAMBDA_RECENCY", 0.3)