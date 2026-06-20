from __future__ import annotations
import concurrent.futures
from .cost_engine import CostEngine
from .models import (
    RankedSchedule,
    ScheduleInfeasibleError,
    ScheduleRequest,
    ScheduleResult,
    ScheduleValidationError,
    ValidationIssue,
)
from .scheduler import Scheduler


def validate_schedule_request(request: ScheduleRequest) -> list[ValidationIssue]:
    """Return structural validation issues without running the optimizer."""
    issues: list[ValidationIssue] = []
    shift_ids = [shift.id for shift in request.shifts]
    person_ids = [person.id for person in request.people]
    shift_id_set = set(shift_ids)
    person_id_set = set(person_ids)

    if len(shift_ids) != len(shift_id_set):
        issues.append(ValidationIssue("duplicate_shift_id", "Shift IDs must be unique.", "shifts"))
    if len(person_ids) != len(person_id_set):
        issues.append(ValidationIssue("duplicate_person_id", "Person IDs must be unique.", "people"))

    if request.algorithm_config.runs <= 0:
        issues.append(ValidationIssue("invalid_runs", "Algorithm runs must be greater than 0.", "algorithm_config.runs"))
    if request.algorithm_config.max_workers <= 0:
        issues.append(ValidationIssue("invalid_max_workers", "Max workers must be greater than 0.", "algorithm_config.max_workers"))
    if request.algorithm_config.iterations < 0:
        issues.append(ValidationIssue("invalid_iterations", "Iterations cannot be negative.", "algorithm_config.iterations"))
    if request.algorithm_config.cooling_rate <= 0:
        issues.append(ValidationIssue("invalid_cooling_rate", "Cooling rate must be greater than 0.", "algorithm_config.cooling_rate"))

    for person_index, person in enumerate(request.people):
        if person.portion <= 0:
            issues.append(ValidationIssue("invalid_portion", "Portion must be greater than 0.", f"people[{person_index}].portion"))
        for shift_id in person.impossible_shifts:
            if shift_id not in shift_id_set:
                issues.append(ValidationIssue("unknown_impossible_shift", f"Unknown shift ID {shift_id}.", f"people[{person_index}].impossible_shifts"))
        for shift_id in person.unwanted_coeffs:
            try:
                parsed_shift_id = int(shift_id)
            except ValueError:
                issues.append(ValidationIssue("invalid_unwanted_shift_id", f"Unwanted shift key {shift_id!r} is not an integer shift ID.", f"people[{person_index}].unwanted_coeffs"))
                continue
            if parsed_shift_id not in shift_id_set:
                issues.append(ValidationIssue("unknown_unwanted_shift", f"Unknown shift ID {shift_id}.", f"people[{person_index}].unwanted_coeffs"))

    for shift_index, shift in enumerate(request.shifts):
        if len(shift.conflicting_shifts) != len(set(shift.conflicting_shifts)):
            issues.append(ValidationIssue("duplicate_conflicting_shift", "Conflicting shift IDs must be unique.", f"shifts[{shift_index}].conflicting_shifts"))
        for conflicting_shift_id in shift.conflicting_shifts:
            if conflicting_shift_id == shift.id:
                issues.append(ValidationIssue("self_conflicting_shift", "A shift cannot conflict with itself.", f"shifts[{shift_index}].conflicting_shifts"))
            elif conflicting_shift_id not in shift_id_set:
                issues.append(ValidationIssue("unknown_conflicting_shift", f"Unknown shift ID {conflicting_shift_id}.", f"shifts[{shift_index}].conflicting_shifts"))
        fixed_people = [person_id for person_id in shift.fixed_assignments if person_id is not None]
        if len(fixed_people) != len(set(fixed_people)):
            issues.append(ValidationIssue("duplicate_fixed_assignee", "A person cannot be fixed twice on the same shift.", f"shifts[{shift_index}].fixed_assignments"))
        for slot_index, person_id in enumerate(shift.fixed_assignments):
            if person_id is None:
                continue
            if person_id not in person_id_set:
                issues.append(ValidationIssue("unknown_fixed_assignee", f"Unknown person {person_id!r}.", f"shifts[{shift_index}].fixed_assignments[{slot_index}]"))
                continue
            person = next(p for p in request.people if p.id == person_id)
            if not person.can_work(shift.id):
                issues.append(ValidationIssue("fixed_impossible_shift", f"{person_id} is fixed to impossible shift {shift.id}.", f"shifts[{shift_index}].fixed_assignments[{slot_index}]"))

    return issues


def solve_schedule(request: ScheduleRequest) -> ScheduleResult:
    """Solve a schedule request and return ranked candidate schedules."""
    issues = validate_schedule_request(request)
    if issues:
        raise ScheduleValidationError(issues)

    results = []
    errors: list[str] = []
    max_workers = min(request.algorithm_config.max_workers, request.algorithm_config.runs)
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_run_simulation, run_id, request) for run_id in range(request.algorithm_config.runs)]
        for future in concurrent.futures.as_completed(futures):
            try:
                results.append(future.result())
            except ValueError as exc:
                errors.append(str(exc))

    if not results:
        message = errors[0] if errors else "No valid schedule can satisfy the active hard constraints."
        raise ScheduleInfeasibleError([ValidationIssue("infeasible_schedule", message)])

    results.sort(key=lambda result: result.energy)
    ranked_schedules = []
    for rank, simulation_result in enumerate(results[:3], start=1):
        simulation_result.rank = rank
        ranked_schedules.append(
            RankedSchedule(
                rank=rank,
                global_energy_score=simulation_result.energy,
                assignments=simulation_result.schedule.assignments,
                person_cost_breakdown=simulation_result.details,
            )
        )
    return ScheduleResult(ranked_schedules=ranked_schedules)


def _run_simulation(run_id: int, request: ScheduleRequest):
    """Run one independent annealing simulation for parallel search."""
    shift_map = {shift.id: shift for shift in request.shifts}
    engine = CostEngine(shift_map, request.scheduler_config.cost_params())
    solver = Scheduler(
        request.people,
        request.shifts,
        engine,
        request.algorithm_config,
    )
    return solver.solve(run_id)
