from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any
from .domain import CalendarDetails, Person, Shift
from .models import AlgorithmConfig, ScheduleRequest, ScheduleResult, SchedulerConfig


def load_request_from_directory(input_dir: str | os.PathLike[str] = "Input") -> ScheduleRequest:
    """Load a ScheduleRequest from the CLI input directory layout."""
    input_path = Path(input_dir)
    calendar_data = _read_json(input_path / "calendar.json")
    shifts_data = _read_json(input_path / "shifts.json")
    people_data = _read_json(input_path / "people.json")
    config_data = _read_json(input_path / "config.json")

    scheduler_config = SchedulerConfig(
        output_dir=config_data.get("output_dir", "./Output"),
        lambda_distribution=config_data.get("cost_function", {}).get("lambda_distribution", 50.0),
        lambda_load=config_data.get("cost_function", {}).get("lambda_load", 20.0),
        lambda_recency=config_data.get("cost_function", {}).get("lambda_recency", 0.3),
        one_shift_per_person_per_calendar_day=config_data.get("hard_constraints", {}).get(
            "one_shift_per_person_per_calendar_day",
            True,
        ),
    )

    return ScheduleRequest(
        calendar=CalendarDetails(
            start_date=calendar_data["start_date"],
            timezone=calendar_data["timezone"],
            organizer_email=calendar_data.get("organizer_email", ""),
        ),
        shifts=[_shift_from_dict(shift) for shift in shifts_data],
        people=[_person_from_dict(person) for person in people_data],
        scheduler_config=scheduler_config,
        algorithm_config=AlgorithmConfig(),
    )


def apply_algorithm_env(request: ScheduleRequest) -> ScheduleRequest:
    """Overlay optional CLI runtime tuning from environment variables."""
    request.algorithm_config = AlgorithmConfig(
        initial_temp=_env_float("SA_INITIAL_TEMP", request.algorithm_config.initial_temp),
        cooling_rate=_env_float("SA_COOLING_RATE", request.algorithm_config.cooling_rate),
        iterations=_env_int("SA_ITERATIONS", request.algorithm_config.iterations),
        runs=_env_int("SA_RUNS", request.algorithm_config.runs),
        max_workers=_env_int("MAX_WORKERS", request.algorithm_config.max_workers),
    )
    return request


def save_result_to_directory(result: ScheduleResult, output_dir: str | os.PathLike[str]) -> None:
    """Write ranked schedule JSON reports to an output directory."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    for ranked_schedule in result.ranked_schedules:
        filename = output_path / f"best_schedule_{ranked_schedule.rank}.json"
        with filename.open("w") as f:
            json.dump(ranked_schedule.to_dict(), f, indent=2)


def _read_json(path: Path) -> Any:
    """Read one JSON file and return its decoded value."""
    with path.open("r") as f:
        return json.load(f)


def _shift_from_dict(data: dict[str, Any]) -> Shift:
    """Build a Shift from decoded JSON data."""
    return Shift(
        id=data["id"],
        time_index=data["time_index"],
        assignment_weights=data["assignment_weights"],
        calendar_day=data["calendar_day"],
        calendar_start_day=data["calendar_start_day"],
        calendar_start_time=data["calendar_start_time"],
        calendar_end_day=data["calendar_end_day"],
        calendar_end_time=data["calendar_end_time"],
        fixed_assignments=data.get("fixed_assignments", []),
    )


def _person_from_dict(data: dict[str, Any]) -> Person:
    """Build a Person from decoded JSON data."""
    return Person(
        id=data["id"],
        email=data.get("email", ""),
        portion=data.get("portion"),
        historical_load_ratio=data.get("historical_load_ratio", 1.0),
        previous_schedule_final_shift_index=data.get("previous_schedule_final_shift_index"),
        previous_schedule_final_shift_weight=data.get("previous_schedule_final_shift_weight", 1.0),
        impossible_shifts=set(data.get("impossible_shifts", [])),
        unwanted_coeffs=data.get("unwanted_coeffs", {}),
    )


def _env_float(key: str, default: float) -> float:
    """Read a float environment variable with a fallback."""
    try:
        return float(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


def _env_int(key: str, default: int) -> int:
    """Read an integer environment variable with a fallback."""
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default
