from __future__ import annotations
import math
import random
from typing import Dict, List
from .domain import Schedule, Person, Shift, SimulationResult
from .cost_engine import CostEngine
from .models import AlgorithmConfig, SchedulerConfig

class Scheduler:
    def __init__(self, people: List[Person], shifts: List[Shift], cost_engine: CostEngine, scheduler_config: SchedulerConfig, algorithm_config: AlgorithmConfig):
        self.people = people
        self.people_by_id = {p.id: p for p in people}
        self.shifts = shifts
        self.shift_map = {s.id: s for s in shifts}
        self.cost_engine = cost_engine
        self.shift_ids = [s.id for s in shifts]
        self.enforce_one_shift_per_day = scheduler_config.one_shift_per_person_per_calendar_day
        self.fixed_roles_by_person_day = self._build_fixed_roles_by_person_day()
        self.mutable_slots = [
            (s.id, slot_index)
            for s in shifts
            for slot_index in range(s.slot_count())
            if not s.is_fixed_slot(slot_index)
        ]

        # Optimization Params
        self.initial_temp = algorithm_config.initial_temp
        self.cooling_rate = algorithm_config.cooling_rate
        self.iterations = algorithm_config.iterations

    def _build_fixed_roles_by_person_day(self) -> Dict[tuple[str, int], List[tuple[int, int]]]:
        fixed_roles: Dict[tuple[str, int], List[tuple[int, int]]] = {}
        for shift in self.shifts:
            fixed_people = [pid for pid in shift.fixed_assignments if pid is not None]
            if len(fixed_people) != len(set(fixed_people)):
                raise ValueError(f"Shift {shift.id} has duplicate fixed assignments.")
            for slot_index, person_id in enumerate(shift.fixed_assignments):
                if person_id is None:
                    continue
                self._validate_fixed_assignment(shift, slot_index, person_id, [])
                key = (person_id, shift.calendar_day)
                fixed_roles.setdefault(key, []).append((shift.id, slot_index))

        if self.enforce_one_shift_per_day:
            for (person_id, calendar_day), roles in fixed_roles.items():
                if len(roles) > 1:
                    raise ValueError(
                        f"{person_id} has multiple fixed assignments on calendar day {calendar_day}: {roles}."
                    )
        return fixed_roles

    def _eligible_people_for_slot(
        self,
        shift_id: int,
        existing_assignments: List[str],
        assignments: Dict[int, List[str]],
        excluded_person_id: str | None = None,
        current_role: tuple[int, int] | None = None,
    ) -> List[str]:
        return [
            p.id for p in self.people
            if p.can_work(shift_id)
            and p.id not in existing_assignments
            and p.id != excluded_person_id
            and not self._violates_daily_limit(p.id, shift_id, assignments, current_role)
        ]

    def _violates_daily_limit(
        self,
        person_id: str,
        shift_id: int,
        assignments: Dict[int, List[str]],
        current_role: tuple[int, int] | None = None,
    ) -> bool:
        if not self.enforce_one_shift_per_day:
            return False

        calendar_day = self.shift_map[shift_id].calendar_day
        for assigned_shift_id, assigned_people in assignments.items():
            if self.shift_map[assigned_shift_id].calendar_day != calendar_day:
                continue
            for slot_index, assigned_person_id in enumerate(assigned_people):
                if current_role == (assigned_shift_id, slot_index):
                    continue
                if assigned_person_id == person_id:
                    return True

        for fixed_role in self.fixed_roles_by_person_day.get((person_id, calendar_day), []):
            if current_role != fixed_role:
                return True
        return False

    def _validate_fixed_assignment(self, shift: Shift, slot_index: int, person_id: str, assignments: List[str]):
        person = self.people_by_id.get(person_id)
        if person is None:
            raise ValueError(f"Shift {shift.id} slot {slot_index} is fixed to unknown person {person_id}.")
        if not person.can_work(shift.id):
            raise ValueError(f"Shift {shift.id} slot {slot_index} is fixed to {person_id}, but that shift is impossible for them.")
        if person_id in assignments:
            raise ValueError(f"Shift {shift.id} assigns {person_id} more than once.")

    def _generate_initial_valid_schedule(self) -> Schedule:
        assignments: Dict[int, List[str | None]] = {
            shift.id: [None] * shift.slot_count()
            for shift in self.shifts
        }

        for shift in self.shifts:
            for slot_index, fixed_person_id in enumerate(shift.fixed_assignments):
                if fixed_person_id is None:
                    continue
                if self._violates_daily_limit(fixed_person_id, shift.id, assignments, (shift.id, slot_index)):
                    raise ValueError(
                        f"Shift {shift.id} slot {slot_index} is fixed to {fixed_person_id}, "
                        f"but they already have a shift on calendar day {shift.calendar_day}."
                    )
                if fixed_person_id in [pid for pid in assignments[shift.id] if pid is not None]:
                    raise ValueError(f"Shift {shift.id} assigns {fixed_person_id} more than once.")
                assignments[shift.id][slot_index] = fixed_person_id

        mutable_slots = [
            (shift.id, slot_index)
            for shift in self.shifts
            for slot_index in range(shift.slot_count())
            if assignments[shift.id][slot_index] is None
        ]

        def candidate_ids(shift_id: int, slot_index: int) -> List[str]:
            existing_people = [
                pid for idx, pid in enumerate(assignments[shift_id])
                if idx != slot_index and pid is not None
            ]
            return self._eligible_people_for_slot(
                shift_id,
                existing_people,
                assignments,
                current_role=(shift_id, slot_index),
            )

        def assign_remaining() -> bool:
            unassigned_slots = [
                role for role in mutable_slots
                if assignments[role[0]][role[1]] is None
            ]
            if not unassigned_slots:
                return True

            shift_id, slot_index = min(unassigned_slots, key=lambda role: len(candidate_ids(*role)))
            candidates = candidate_ids(shift_id, slot_index)
            random.shuffle(candidates)
            for person_id in candidates:
                assignments[shift_id][slot_index] = person_id
                if assign_remaining():
                    return True
                assignments[shift_id][slot_index] = None
            return False

        if not assign_remaining():
            raise ValueError("No valid schedule can satisfy the active hard constraints.")

        return Schedule({
            shift_id: [person_id for person_id in people if person_id is not None]
            for shift_id, people in assignments.items()
        })

    def solve(self, run_id: int) -> SimulationResult:
        current_schedule = self._generate_initial_valid_schedule()
        current_energy = self.cost_engine.calculate_total_global_energy(self.people, current_schedule)

        best_schedule = current_schedule.copy()
        best_energy = current_energy

        temp = self.initial_temp

        for _ in range(self.iterations):
            if not self.mutable_slots:
                break

            # 1. Mutate one non-fixed assignment slot
            shift_to_swap, slot_index = random.choice(self.mutable_slots)
            current_shift_assignments = current_schedule.assignments[shift_to_swap]
            current_owner = current_shift_assignments[slot_index]
            existing_people = [pid for idx, pid in enumerate(current_shift_assignments) if idx != slot_index]
            candidates = self._eligible_people_for_slot(
                shift_to_swap,
                existing_people,
                current_schedule.assignments,
                excluded_person_id=current_owner,
                current_role=(shift_to_swap, slot_index),
            )

            if not candidates:
                temp *= self.cooling_rate
                continue

            new_owner = random.choice(candidates)

            # Create neighbor
            neighbor_schedule = current_schedule.copy()
            neighbor_schedule.assignments[shift_to_swap][slot_index] = new_owner

            # 2. Evaluate
            neighbor_energy = self.cost_engine.calculate_total_global_energy(self.people, neighbor_schedule)

            # 3. Acceptance Logic
            delta = neighbor_energy - current_energy

            if delta < 0:
                current_schedule = neighbor_schedule
                current_energy = neighbor_energy
                if current_energy < best_energy:
                    best_energy = current_energy
                    best_schedule = current_schedule.copy()
            else:
                if random.random() < math.exp(-delta / temp):
                    current_schedule = neighbor_schedule
                    current_energy = neighbor_energy

            # 4. Cool down
            temp *= self.cooling_rate

        # 5. Generate full details for the best result
        final_details = {}
        total_portion = sum(p.portion for p in self.people)
        for p in self.people:
            roles = best_schedule.get_person_roles(p.id)
            final_details[p.id] = self.cost_engine.calculate_person_details(p, roles, total_portion)

        return SimulationResult(
            rank=0, # Assigned later
            energy=best_energy,
            schedule=best_schedule,
            details=final_details
        )
