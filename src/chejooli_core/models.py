from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any
from .domain import CalendarDetails, Person, PersonCostDetails, Shift

@dataclass
class SchedulerConfig:
    lambda_distribution: float = 50.0
    lambda_load: float = 20.0
    lambda_recency: float = 0.3
    one_shift_per_person_per_calendar_day: bool = True
    output_dir: str = "./Output"

    def cost_params(self) -> dict[str, float]:
        return {
            "lambda1_distribution": self.lambda_distribution,
            "lambda2_load": self.lambda_load,
            "lambda3_recency": self.lambda_recency,
        }

@dataclass
class AlgorithmConfig:
    initial_temp: float = 1000.0
    cooling_rate: float = 0.995
    iterations: int = 10000
    runs: int = 10
    max_workers: int = 5

@dataclass
class ScheduleRequest:
    calendar: CalendarDetails
    shifts: list[Shift]
    people: list[Person]
    scheduler_config: SchedulerConfig
    algorithm_config: AlgorithmConfig

@dataclass
class RankedSchedule:
    rank: int
    global_energy_score: float
    assignments: dict[int, list[str]]
    person_cost_breakdown: dict[str, PersonCostDetails]

    def to_dict(self) -> dict[str, Any]:
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
    ranked_schedules: list[RankedSchedule]

@dataclass
class ValidationIssue:
    code: str
    message: str
    path: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)

class ChejooliError(Exception):
    pass

class ScheduleValidationError(ChejooliError):
    def __init__(self, issues: list[ValidationIssue]):
        self.issues = issues
        super().__init__("Schedule request is invalid")

class ScheduleInfeasibleError(ChejooliError):
    def __init__(self, issues: list[ValidationIssue]):
        self.issues = issues
        super().__init__("No feasible schedule satisfies the active hard constraints")
