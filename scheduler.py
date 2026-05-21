from __future__ import annotations
import math
import random
from typing import List, Tuple
from domain import Schedule, Person, Shift, SimulationResult
from cost_engine import CostEngine
from config import Config

class Scheduler:
    def __init__(self, people: List[Person], shifts: List[Shift], cost_engine: CostEngine):
        self.people = people
        self.shifts = shifts
        self.shift_map = {s.id: s for s in shifts}
        self.cost_engine = cost_engine
        self.shift_ids = [s.id for s in shifts]
        self.mutable_slots = [
            (s.id, slot_index)
            for s in shifts
            for slot_index in range(s.slot_count())
            if not s.is_fixed_slot(slot_index)
        ]
        
        # Optimization Params
        self.initial_temp = Config.SA_INITIAL_TEMP
        self.cooling_rate = Config.SA_COOLING_RATE
        self.iterations = Config.SA_ITERATIONS

    def _eligible_people_for_slot(self, shift_id: int, existing_assignments: List[str], excluded_person_id: str | None = None) -> List[str]:
        return [
            p.id for p in self.people
            if p.can_work(shift_id)
            and p.id not in existing_assignments
            and p.id != excluded_person_id
        ]

    def _validate_fixed_assignment(self, shift: Shift, slot_index: int, person_id: str, assignments: List[str]):
        person = next((p for p in self.people if p.id == person_id), None)
        if person is None:
            raise ValueError(f"Shift {shift.id} slot {slot_index} is fixed to unknown person {person_id}.")
        if not person.can_work(shift.id):
            raise ValueError(f"Shift {shift.id} slot {slot_index} is fixed to {person_id}, but that shift is impossible for them.")
        if person_id in assignments:
            raise ValueError(f"Shift {shift.id} assigns {person_id} more than once.")

    def _generate_initial_valid_schedule(self) -> Schedule:
        assignments = {}
        for shift in self.shifts:
            fixed_people = [pid for pid in shift.fixed_assignments if pid is not None]
            if len(fixed_people) != len(set(fixed_people)):
                raise ValueError(f"Shift {shift.id} has duplicate fixed assignments.")
            for slot_index, fixed_person_id in enumerate(shift.fixed_assignments):
                if fixed_person_id is not None:
                    self._validate_fixed_assignment(shift, slot_index, fixed_person_id, [])

            shift_assignments: List[str] = []
            for slot_index in range(shift.slot_count()):
                fixed_person_id = shift.fixed_assignments[slot_index]
                if fixed_person_id is not None:
                    shift_assignments.append(fixed_person_id)
                    continue

                reserved_people = [
                    pid for idx, pid in enumerate(shift.fixed_assignments)
                    if pid is not None and idx > slot_index
                ]
                candidates = self._eligible_people_for_slot(shift.id, shift_assignments + reserved_people)
                if not candidates:
                    raise ValueError(f"Shift {shift.id} slot {slot_index} cannot be assigned to anyone (Hard Constraint Violation).")
                shift_assignments.append(random.choice(candidates))

            assignments[shift.id] = shift_assignments
        return Schedule(assignments)

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
                excluded_person_id=current_owner,
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
