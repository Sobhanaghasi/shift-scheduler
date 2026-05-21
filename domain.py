from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

AssignedRole = Tuple[int, int]  # (shift_id, assignment_slot_index)

@dataclass
class Shift:
    id: int
    time_index: int
    assignment_weights: List[float]
    calendar_block: str
    fixed_assignments: List[Optional[str]] = field(default_factory=list)

    def __post_init__(self):
        if not self.assignment_weights:
            raise ValueError(f"Shift {self.id} must have at least one assignment slot")
        if any(weight <= 0 for weight in self.assignment_weights):
            raise ValueError(f"Shift {self.id} assignment weights must be greater than 0")
        if len(self.fixed_assignments) > len(self.assignment_weights):
            raise ValueError(f"Shift {self.id} has more fixed assignments than assignment slots")
        self.fixed_assignments = self.fixed_assignments + [None] * (len(self.assignment_weights) - len(self.fixed_assignments))

    def slot_count(self) -> int:
        return len(self.assignment_weights)

    def slot_weight(self, slot_index: int) -> float:
        return self.assignment_weights[slot_index]

    def is_fixed_slot(self, slot_index: int) -> bool:
        return self.fixed_assignments[slot_index] is not None

@dataclass
class CalendarDetails:
    start_date: str
    timezone: str


@dataclass
class PersonCostDetails:
    """Holds the granular breakdown of a person's cost calculation."""
    # Raw values (Before Lambdas)
    raw_preference_cost: float = 0.0
    raw_distribution_score: float = 0.0  # Electrostatic repulsion
    actual_load: float = 0.0
    expected_load: float = 0.0
    current_load_ratio: float = 0.0
    previous_load_ratio: float = 1.0
    effective_load_ratio: float = 1.0
    load_ratio_deviation: float = 0.0

    # Weighted values (After Lambdas)
    weighted_dist_cost: float = 0.0
    weighted_load_cost: float = 0.0
    portion: float = 1.0

    # Final aggregation
    total_cost: float = 0.0

@dataclass
class Person:
    id: str
    portion: float
    previous_load_ratio: float
    last_week_final_shift_index: Optional[int]
    impossible_shifts: set[int]
    unwanted_coeffs: Dict[str, float]
    calendar_color: str = ""

    def can_work(self, shift_id: int) -> bool:
        return shift_id not in self.impossible_shifts

@dataclass
class Schedule:
    """Represents a specific state of assignments."""
    assignments: Dict[int, List[str]] = field(default_factory=dict) # shift_id -> assignment-slot people

    def copy(self) -> 'Schedule':
        return Schedule({sid: people.copy() for sid, people in self.assignments.items()})
    
    def get_person_shifts(self, person_id: str) -> List[int]:
        return [sid for sid, people in self.assignments.items() if person_id in people]

    def get_person_roles(self, person_id: str) -> List[AssignedRole]:
        roles = []
        for sid, people in self.assignments.items():
            for slot_index, assigned_person_id in enumerate(people):
                if assigned_person_id == person_id:
                    roles.append((sid, slot_index))
        return roles

@dataclass
class SimulationResult:
    rank: int
    energy: float
    schedule: Schedule
    details: Dict[str, PersonCostDetails]
