from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv
load_dotenv()

CONFIG_FILE = "config.json"
CALENDAR_FILE = "calendar.json"
SHIFTS_FILE = "shifts.json"
PEOPLE_FILE = "people.json"


def load_json_config() -> Dict[str, Any]:
    path = Path(CONFIG_FILE)
    if not path.exists():
        return {}
    with path.open("r") as f:
        return json.load(f)


def get_nested(data: Dict[str, Any], keys: tuple[str, ...], default: Any) -> Any:
    value: Any = data
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return default
        value = value[key]
    return value


class Config:
    CONFIG_FILE = CONFIG_FILE
    CALENDAR_FILE = CALENDAR_FILE
    SHIFTS_FILE = SHIFTS_FILE
    PEOPLE_FILE = PEOPLE_FILE

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

    CONFIG_DATA = load_json_config()

    # Algorithm tuning stays in .env.
    SA_INITIAL_TEMP = get_env_float("SA_INITIAL_TEMP", 1000.0)
    SA_COOLING_RATE = get_env_float("SA_COOLING_RATE", 0.995)
    SA_ITERATIONS = get_env_int("SA_ITERATIONS", 10000)
    SA_RUNS = get_env_int("SA_RUNS", 10)
    MAX_WORKERS = get_env_int("MAX_WORKERS", 5)

    # Scheduler policy comes from config.json.
    OUTPUT_DIR = get_nested(CONFIG_DATA, ("output_dir",), "./results")
    ONE_SHIFT_PER_PERSON_PER_CALENDAR_DAY = get_nested(
        CONFIG_DATA,
        ("hard_constraints", "one_shift_per_person_per_calendar_day"),
        True,
    )
    LAMBDA_DIST = get_nested(CONFIG_DATA, ("cost_function", "lambda_distribution"), 50.0)
    LAMBDA_LOAD = get_nested(CONFIG_DATA, ("cost_function", "lambda_load"), 20.0)
    LAMBDA_RECENCY = get_nested(CONFIG_DATA, ("cost_function", "lambda_recency"), 0.3)
