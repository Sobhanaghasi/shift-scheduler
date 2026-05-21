from __future__ import annotations
from typing import List, Dict
from domain import Person, Shift, PersonCostDetails, AssignedRole

class CostEngine:
    def __init__(self, shifts: Dict[int, Shift], params: Dict[str, float]):
        self.shifts = shifts
        self.params = params
        self.total_week_load = sum(
            slot_weight
            for shift in shifts.values()
            for slot_weight in shift.assignment_weights
        )
        
        # Mapping for fast time index lookups
        self.shift_time_indices = {s.id: s.time_index for s in shifts.values()}

    def calculate_person_details(self, person: Person, assigned_roles: List[AssignedRole], total_portion: float) -> PersonCostDetails:
        details = PersonCostDetails()
        assigned_shift_ids = [sid for sid, _ in assigned_roles]
        
        # 1. Preference Cost (Role Weight * Unwanted Coefficient)
        pref_cost = 0.0
        for sid, slot_index in assigned_roles:
            # Coeffs are stored as strings in JSON usually, convert if needed
            coeff = person.unwanted_coeffs.get(str(sid), 0.0)
            weight = self.shifts[sid].slot_weight(slot_index)
            pref_cost += weight * coeff
        details.raw_preference_cost = pref_cost

        # 2. Distribution (Electrostatic Repulsion)
        repulsion_score = self._calculate_repulsion(person, assigned_shift_ids)
        details.raw_distribution_score = repulsion_score
        
        lambda1 = self.params["lambda1_distribution"]
        details.weighted_dist_cost = lambda1 * repulsion_score

        # 3. Load Fairness (Moving Average of normalized load ratio)
        load_details = self._calculate_load_fairness(person, assigned_roles, total_portion)
        details.actual_load = load_details["actual_load"]
        details.expected_load = load_details["expected_load"]
        details.current_load_ratio = load_details["current_load_ratio"]
        details.previous_load_ratio = person.previous_load_ratio
        details.effective_load_ratio = load_details["effective_load_ratio"]
        details.load_ratio_deviation = load_details["load_ratio_deviation"]
        
        lambda2 = self.params["lambda2_load"]
        details.weighted_load_cost = lambda2 * abs(details.load_ratio_deviation)

        details.portion = person.portion

        # 4. Final Aggregation
        details.total_cost = details.raw_preference_cost + details.weighted_dist_cost + details.weighted_load_cost
        
        return details

    def _calculate_repulsion(self, person: Person, assigned_shift_ids: List[int]) -> float:
        indices = sorted([self.shift_time_indices[sid] for sid in assigned_shift_ids])
        total_repulsion = 0.0
        count_interactions = 0

        # Internal Repulsion
        for i in range(len(indices)):
            for j in range(i + 1, len(indices)):
                dist = abs(indices[i] - indices[j])
                # Avoid div by zero
                total_repulsion += 1.0 / (dist ** 2) if dist > 0 else 1000.0
                count_interactions += 1

        # History Repulsion (Ghost Slot)
        if person.last_week_final_shift_index is not None:
            ghost_idx = person.last_week_final_shift_index
            for idx in indices:
                dist = abs(idx - ghost_idx)
                total_repulsion += 1.0 / (dist ** 2) if dist > 0 else 1000.0
                count_interactions += 1
        
        # Average by assigned shift count to avoid punishing people only for having more shifts.
        num_shifts = len(indices)
        if num_shifts > 0:
             return total_repulsion / num_shifts
        return 0.0

    def _calculate_load_fairness(self, person: Person, assigned_roles: List[AssignedRole], total_portion: float) -> Dict[str, float]:
        if person.portion <= 0:
            raise ValueError(f"Portion must be greater than 0 for person {person.id}")
        if total_portion <= 0:
            raise ValueError("Total portion must be greater than 0")

        actual_load = sum(self.shifts[sid].slot_weight(slot_index) for sid, slot_index in assigned_roles)
        expected_load = self.total_week_load * person.portion / total_portion
        if expected_load <= 0:
            raise ValueError(f"Expected load must be greater than 0 for person {person.id}")

        current_load_ratio = actual_load / expected_load
        lambda3 = self.params["lambda3_recency"]
        effective_load_ratio = (lambda3 * current_load_ratio) + ((1.0 - lambda3) * person.previous_load_ratio)
        load_ratio_deviation = effective_load_ratio - 1.0

        return {
            "actual_load": actual_load,
            "expected_load": expected_load,
            "current_load_ratio": current_load_ratio,
            "effective_load_ratio": effective_load_ratio,
            "load_ratio_deviation": load_ratio_deviation,
        }

    def calculate_total_global_energy(self, people: List[Person], schedule) -> float:
        """Sum of all interpretable per-person costs."""
        total_cost = 0.0
        total_portion = sum(p.portion for p in people)
        for p in people:
            roles = schedule.get_person_roles(p.id)
            details = self.calculate_person_details(p, roles, total_portion)
            total_cost += details.total_cost
        return total_cost
