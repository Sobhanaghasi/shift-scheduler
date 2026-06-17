from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

AssignedRole = Tuple[int, int]

@dataclass
class Shift:
    """A schedulable time block with one or more weighted assignment slots."""

    id: int
    time_index: int
    assignment_weights: List[float]
    calendar_day: int
    calendar_start_day: int
    calendar_start_time: str
    calendar_end_day: int
    calendar_end_time: str
    fixed_assignments: List[Optional[str]] = field(default_factory=list)

    def __post_init__(self):
        """Normalize fixed slots and reject impossible shift definitions."""
        if not self.assignment_weights:
            raise ValueError(f"Shift {self.id} must have at least one assignment slot")
        if any(weight <= 0 for weight in self.assignment_weights):
            raise ValueError(f"Shift {self.id} assignment weights must be greater than 0")
        if len(self.fixed_assignments) > len(self.assignment_weights):
            raise ValueError(f"Shift {self.id} has more fixed assignments than assignment slots")
        if self.calendar_day <= 0 or self.calendar_start_day <= 0 or self.calendar_end_day <= 0:
            raise ValueError(f"Shift {self.id} calendar day fields must be greater than 0")
        self.fixed_assignments = self.fixed_assignments + [None] * (len(self.assignment_weights) - len(self.fixed_assignments))

    def slot_count(self) -> int:
        """Return how many people this shift requires."""
        return len(self.assignment_weights)

    def slot_weight(self, slot_index: int) -> float:
        """Return the workload weight for one assignment slot."""
        return self.assignment_weights[slot_index]

    def is_fixed_slot(self, slot_index: int) -> bool:
        """Return whether one assignment slot is manually fixed."""
        return self.fixed_assignments[slot_index] is not None

@dataclass
class CalendarDetails:
    """Calendar metadata shared by generated schedule exports."""

    start_date: str
    timezone: str
    organizer_email: str = ""

@dataclass
class PersonCostDetails:
    """Cost breakdown for one person in one ranked schedule."""

    raw_preference_cost: float = 0.0
    raw_distribution_score: float = 0.0
    actual_load: float = 0.0
    expected_load: float = 0.0
    current_load_ratio: float = 0.0
    historical_load_ratio: float = 1.0
    effective_load_ratio: float = 1.0
    load_ratio_deviation: float = 0.0
    weighted_dist_cost: float = 0.0
    weighted_load_cost: float = 0.0
    portion: float = 1.0
    total_cost: float = 0.0

@dataclass
class Person:
    """A schedulable person with capacity, history, and preferences."""

    id: str
    portion: float
    historical_load_ratio: float
    previous_schedule_final_shift_index: Optional[int]
    previous_schedule_final_shift_weight: float
    impossible_shifts: set[int]
    unwanted_coeffs: Dict[str, float]
    email: str = ""

    def can_work(self, shift_id: int) -> bool:
        """Return whether the shift is not explicitly impossible for this person."""
        return shift_id not in self.impossible_shifts

@dataclass
class Schedule:
    """Concrete assignment of people to every shift slot."""

    assignments: Dict[int, List[str]] = field(default_factory=dict)

    def copy(self) -> 'Schedule':
        """Return a deep-enough copy for annealing mutations."""
        return Schedule({sid: people.copy() for sid, people in self.assignments.items()})

    def get_person_shifts(self, person_id: str) -> List[int]:
        """Return IDs of shifts assigned to a person."""
        return [sid for sid, people in self.assignments.items() if person_id in people]

    def get_person_roles(self, person_id: str) -> List[AssignedRole]:
        """Return all assigned shift-slot pairs for a person."""
        roles = []
        for sid, people in self.assignments.items():
            for slot_index, assigned_person_id in enumerate(people):
                if assigned_person_id == person_id:
                    roles.append((sid, slot_index))
        return roles

@dataclass
class SimulationResult:
    """Best schedule found by one independent optimization run."""

    rank: int
    energy: float
    schedule: Schedule
    details: Dict[str, PersonCostDetails]
