from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional

@dataclass
class Shift:
    id: int
    weight: float
    time_index: int

@dataclass
class PersonCostDetails:
    """Holds the granular breakdown of a person's cost calculation."""
    # Raw values (Before Lambdas)
    raw_preference_cost: float = 0.0
    raw_distribution_score: float = 0.0  # Electrostatic repulsion
    raw_load_score: float = 0.0          # Current load (moving average input)
    
    # Weighted values (After Lambdas)
    weighted_dist_cost: float = 0.0
    weighted_load_cost: float = 0.0
    portion: float = 1.0
    portioned_weighted_load_cost: float = 0.0
    
    # Final steps
    final_cost_linear: float = 0.0 # (Sum / Portion)
    final_cost_squared: float = 0.0 # (Sum / Portion)^2 (Contribution to global energy)

@dataclass
class Person:
    id: str
    portion: float
    previous_load: float
    last_week_final_shift_index: Optional[int]
    impossible_shifts: set[int]
    unwanted_coeffs: Dict[str, float]

    def can_work(self, shift_id: int) -> bool:
        return shift_id not in self.impossible_shifts

@dataclass
class Schedule:
    """Represents a specific state of assignments."""
    assignments: Dict[int, str] = field(default_factory=dict) # shift_id -> person_id

    def copy(self) -> 'Schedule':
        return Schedule(self.assignments.copy())
    
    def get_person_shifts(self, person_id: str) -> List[int]:
        return [sid for sid, pid in self.assignments.items() if pid == person_id]

@dataclass
class SimulationResult:
    rank: int
    energy: float
    schedule: Schedule
    details: Dict[str, PersonCostDetails]