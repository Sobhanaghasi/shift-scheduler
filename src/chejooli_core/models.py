from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any
from .domain import CalendarDetails, Person, PersonCostDetails, Shift

@dataclass
class SchedulerConfig:
    """Business policy for costs and CLI output."""

    lambda_distribution: float = 50.0
    lambda_load: float = 20.0
    lambda_recency: float = 0.3
    output_dir: str = "./Output"

    def cost_params(self) -> dict[str, float]:
        """Return the cost-engine parameter names expected by the legacy engine."""
        return {
            "lambda1_distribution": self.lambda_distribution,
            "lambda2_load": self.lambda_load,
            "lambda3_recency": self.lambda_recency,
        }

@dataclass
class AlgorithmConfig:
    """Runtime controls for the simulated annealing search."""

    initial_temp: float = 1000.0
    cooling_rate: float = 0.995
    iterations: int = 10000
    runs: int = 10
    max_workers: int = 5

@dataclass
class ScheduleRequest:
    """Complete input contract consumed by solve_schedule()."""

    calendar: CalendarDetails
    shifts: list[Shift]
    people: list[Person]
    scheduler_config: SchedulerConfig
    algorithm_config: AlgorithmConfig

@dataclass
class RankedSchedule:
    """One candidate schedule, ordered by increasing global cost."""

    rank: int
    global_energy_score: float
    assignments: dict[int, list[str]]
    person_cost_breakdown: dict[str, PersonCostDetails]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the ranked schedule for JSON responses or reports."""
        return {
            "rank": self.rank,
            "global_energy_score": self.global_energy_score,
            "schedule_assignments": self.assignments,
            "person_cost_breakdown": {
                person_id: asdict(details)
                for person_id, details in self.person_cost_breakdown.items()
            },
        }

@dataclass
class ScheduleResult:
    """Successful solve output containing the best ranked schedules."""

    ranked_schedules: list[RankedSchedule]

@dataclass
class ValidationIssue:
    """Structured problem description for API and CLI error handling."""

    code: str
    message: str
    path: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        """Serialize the issue for API responses or CLI diagnostics."""
        return asdict(self)

class ChejooliError(Exception):
    """Base exception for expected Chejooli failures."""

class ScheduleValidationError(ChejooliError):
    """Raised when the request is malformed or internally inconsistent."""

    def __init__(self, issues: list[ValidationIssue]):
        """Store validation issues for callers to serialize or display."""
        self.issues = issues
        super().__init__("Schedule request is invalid")

class ScheduleInfeasibleError(ChejooliError):
    """Raised when valid inputs cannot satisfy the active hard constraints."""

    def __init__(self, issues: list[ValidationIssue]):
        """Store infeasibility issues for callers to serialize or display."""
        self.issues = issues
        super().__init__("No feasible schedule satisfies the active hard constraints")
