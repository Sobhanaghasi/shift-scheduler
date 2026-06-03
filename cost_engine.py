from __future__ import annotations
from typing import List, Dict
from domain import Person, Shift, PersonCostDetails, AssignedRole

class CostEngine:
    def __init__(self, shifts: Dict[int, Shift], params: Dict[str, float]):
        self.shifts = shifts
        self.params = params
        self.total_schedule_load = sum(
            slot_weight
            for shift in shifts.values()
            for slot_weight in shift.assignment_weights
        )

        # Mapping for fast time index lookups
        self.shift_time_indices = {s.id: s.time_index for s in shifts.values()}

    def calculate_person_details(self, person: Person, assigned_roles: List[AssignedRole], total_portion: float) -> PersonCostDetails:
        details = PersonCostDetails()

        # 1. Preference Cost (Role Weight * Unwanted Coefficient)
        pref_cost = 0.0
        for sid, slot_index in assigned_roles:
            # Coeffs are stored as strings in JSON usually, convert if needed
            coeff = person.unwanted_coeffs.get(str(sid), 0.0)
            weight = self.shifts[sid].slot_weight(slot_index)
            pref_cost += weight * coeff
        details.raw_preference_cost = pref_cost

        # 2. Distribution (load-weighted electrostatic repulsion)
        repulsion_score = self._calculate_repulsion(person, assigned_roles)
        details.raw_distribution_score = repulsion_score

        lambda1 = self.params["lambda1_distribution"]
        details.weighted_dist_cost = lambda1 * repulsion_score

        # 3. Load Fairness (Moving Average of normalized load ratio)
        load_details = self._calculate_load_fairness(person, assigned_roles, total_portion)
        details.actual_load = load_details["actual_load"]
        details.expected_load = load_details["expected_load"]
        details.current_load_ratio = load_details["current_load_ratio"]
        details.historical_load_ratio = person.historical_load_ratio
        details.effective_load_ratio = load_details["effective_load_ratio"]
        details.load_ratio_deviation = load_details["load_ratio_deviation"]

        lambda2 = self.params["lambda2_load"]
        details.weighted_load_cost = lambda2 * abs(details.load_ratio_deviation)

        details.portion = person.portion

        # 4. Final Aggregation
        details.total_cost = details.raw_preference_cost + details.weighted_dist_cost + details.weighted_load_cost

        return details

    def _calculate_repulsion(self, person: Person, assigned_roles: List[AssignedRole]) -> float:
        role_loads = sorted(
            (
                self.shift_time_indices[sid],
                self.shifts[sid].slot_weight(slot_index),
            )
            for sid, slot_index in assigned_roles
        )
        actual_load = sum(weight for _, weight in role_loads)
        if actual_load <= 0:
            return 0.0

        total_repulsion = 0.0

        # Internal current-schedule repulsion: nearby heavy roles are worse than nearby light roles.
        for i in range(len(role_loads)):
            time_i, weight_i = role_loads[i]
            for j in range(i + 1, len(role_loads)):
                time_j, weight_j = role_loads[j]
                dist = abs(time_i - time_j)
                total_repulsion += (weight_i * weight_j) / (dist ** 2) if dist > 0 else 1000.0 * weight_i * weight_j

        # Boundary repulsion: only the first current role is compared to the previous schedule's final role.
        if person.previous_schedule_final_shift_index is not None:
            first_time, first_weight = role_loads[0]
            previous_weight = person.previous_schedule_final_shift_weight
            dist = abs(first_time - person.previous_schedule_final_shift_index)
            total_repulsion += (first_weight * previous_weight) / (dist ** 2) if dist > 0 else 1000.0 * first_weight * previous_weight

        return total_repulsion / actual_load

    def _calculate_load_fairness(self, person: Person, assigned_roles: List[AssignedRole], total_portion: float) -> Dict[str, float]:
        if person.portion <= 0:
            raise ValueError(f"Portion must be greater than 0 for person {person.id}")
        if total_portion <= 0:
            raise ValueError("Total portion must be greater than 0")

        actual_load = sum(self.shifts[sid].slot_weight(slot_index) for sid, slot_index in assigned_roles)
        expected_load = self.total_schedule_load * person.portion / total_portion
        if expected_load <= 0:
            raise ValueError(f"Expected load must be greater than 0 for person {person.id}")

        current_load_ratio = actual_load / expected_load
        lambda3 = self.params["lambda3_recency"]
        effective_load_ratio = (lambda3 * current_load_ratio) + ((1.0 - lambda3) * person.historical_load_ratio)
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
