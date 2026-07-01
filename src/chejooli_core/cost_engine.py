from __future__ import annotations
from typing import Dict, List
from .domain import AssignedRole, Person, PersonCostDetails, Shift

class CostEngine:
    """Calculates preference, distribution, and load fairness costs."""

    def __init__(self, shifts: Dict[int, Shift], params: Dict[str, float]):
        """Cache shift data and cost parameters for repeated evaluations."""
        self.shifts = shifts
        self.params = params
        self.total_schedule_load = sum(
            slot_weight
            for shift in shifts.values()
            for slot_weight in shift.assignment_weights
        )
        self.shift_time_indices = {s.id: s.time_index for s in shifts.values()}

    def calculate_person_details(self, person: Person, assigned_roles: List[AssignedRole], total_portion: float) -> PersonCostDetails:
        """Return the full cost breakdown for one person."""
        details = PersonCostDetails()

        pref_cost = 0.0
        for sid, slot_index in assigned_roles:
            coeff = person.unwanted_coeffs.get(str(sid), 0.0)
            weight = self.shifts[sid].slot_weight(slot_index)
            pref_cost += weight * coeff
        details.raw_preference_cost = pref_cost
        details.weighted_preference_cost = self.params["lambda_preference"] * pref_cost

        repulsion_score = self._calculate_repulsion(person, assigned_roles)
        details.raw_distribution_score = repulsion_score
        details.weighted_dist_cost = self.params["lambda1_distribution"] * repulsion_score

        load_details = self._calculate_load_fairness(person, assigned_roles, total_portion)
        details.actual_load = load_details["actual_load"]
        details.expected_load = load_details["expected_load"]
        details.current_load_ratio = load_details["current_load_ratio"]
        details.historical_load_ratio = person.historical_load_ratio
        details.effective_load_ratio = load_details["effective_load_ratio"]
        details.load_ratio_deviation = load_details["load_ratio_deviation"]
        details.weighted_load_cost = self.params["lambda2_load"] * abs(details.load_ratio_deviation)
        details.portion = person.portion
        details.total_cost = (
            details.weighted_preference_cost + details.weighted_dist_cost + details.weighted_load_cost
        )

        return details

    def _calculate_repulsion(self, person: Person, assigned_roles: List[AssignedRole]) -> float:
        """Calculate load-weighted spacing pressure for a person's roles."""
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
        for i in range(len(role_loads)):
            time_i, weight_i = role_loads[i]
            for j in range(i + 1, len(role_loads)):
                time_j, weight_j = role_loads[j]
                dist = abs(time_i - time_j)
                total_repulsion += (weight_i * weight_j) / (dist ** 2) if dist > 0 else 1000.0 * weight_i * weight_j

        if person.previous_schedule_final_shift_index is not None:
            first_time, first_weight = role_loads[0]
            previous_weight = person.previous_schedule_final_shift_weight
            dist = abs(first_time - person.previous_schedule_final_shift_index)
            total_repulsion += (first_weight * previous_weight) / (dist ** 2) if dist > 0 else 1000.0 * first_weight * previous_weight

        return total_repulsion / actual_load

    def _calculate_load_fairness(self, person: Person, assigned_roles: List[AssignedRole], total_portion: float) -> Dict[str, float]:
        """Calculate current and historical load ratios for one person."""
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
        """Return the additive global cost for a complete schedule."""
        total_cost = 0.0
        total_portion = sum(p.portion for p in people)
        for p in people:
            roles = schedule.get_person_roles(p.id)
            details = self.calculate_person_details(p, roles, total_portion)
            total_cost += details.total_cost
        return total_cost
