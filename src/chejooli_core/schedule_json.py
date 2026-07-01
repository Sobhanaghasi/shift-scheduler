from __future__ import annotations
from dataclasses import asdict
from typing import Any

from .domain import CalendarDetails, Person, Schedule, Shift
from .models import AlgorithmConfig, RankedSchedule, ScheduleRequest, ScheduleResult, SchedulerConfig


def request_to_dict(request: ScheduleRequest) -> dict[str, Any]:
    """Serialize a schedule request to the same JSON shape as the CLI input files."""
    return {
        "calendar": asdict(request.calendar),
        "shifts": [_shift_to_dict(shift) for shift in request.shifts],
        "people": [_person_to_dict(person) for person in request.people],
        "config": _scheduler_config_to_dict(request.scheduler_config),
        "algorithm": asdict(request.algorithm_config),
    }


def result_to_dict(result: ScheduleResult) -> dict[str, Any]:
    """Serialize a solve result with ranked schedules and cost breakdowns."""
    return {
        "ranked_schedules": [ranked_schedule.to_dict() for ranked_schedule in result.ranked_schedules],
    }


def schedule_report_to_dict(request: ScheduleRequest, result: ScheduleResult) -> dict[str, Any]:
    """Serialize the full input and solve output for export or API download."""
    return {
        "request": request_to_dict(request),
        "result": result_to_dict(result),
    }


def assignment_report_to_dict(
    request: ScheduleRequest,
    assignments: dict[int, list[str]],
    *,
    rank: int = 1,
) -> dict[str, Any]:
    """Serialize the input plus one concrete assignment map and its cost breakdown."""
    from .api import evaluate_assignments

    evaluated = evaluate_assignments(request, assignments, rank=rank)
    return {
        "request": request_to_dict(request),
        "schedule": evaluated.to_dict(),
    }


def _scheduler_config_to_dict(config: SchedulerConfig) -> dict[str, Any]:
    return {
        "output_dir": config.output_dir,
        "cost_function": {
            "lambda_preference": config.lambda_preference,
            "lambda_distribution": config.lambda_distribution,
            "lambda_load": config.lambda_load,
            "lambda_recency": config.lambda_recency,
        },
    }


def _shift_to_dict(shift: Shift) -> dict[str, Any]:
    return {
        "id": shift.id,
        "time_index": shift.time_index,
        "assignment_weights": shift.assignment_weights,
        "conflicting_shifts": shift.conflicting_shifts,
        "fixed_assignments": shift.fixed_assignments,
        "calendar_start_day": shift.calendar_start_day,
        "calendar_start_time": shift.calendar_start_time,
        "calendar_end_day": shift.calendar_end_day,
        "calendar_end_time": shift.calendar_end_time,
    }


def _person_to_dict(person: Person) -> dict[str, Any]:
    return {
        "id": person.id,
        "email": person.email,
        "portion": person.portion,
        "historical_load_ratio": person.historical_load_ratio,
        "previous_schedule_final_shift_index": person.previous_schedule_final_shift_index,
        "previous_schedule_final_shift_weight": person.previous_schedule_final_shift_weight,
        "impossible_shifts": sorted(person.impossible_shifts),
        "unwanted_coeffs": person.unwanted_coeffs,
    }
