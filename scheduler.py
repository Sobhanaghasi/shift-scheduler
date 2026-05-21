from __future__ import annotations
import math
import random
import copy
from typing import List, Dict, Tuple
from domain import Schedule, Person, Shift, SimulationResult
from cost_engine import CostEngine
from config import Config

class Scheduler:
    def __init__(self, people: List[Person], shifts: List[Shift], cost_engine: CostEngine):
        self.people = people
        self.shifts = shifts
        self.cost_engine = cost_engine
        self.shift_ids = [s.id for s in shifts]
        
        # Optimization Params
        self.initial_temp = Config.SA_INITIAL_TEMP
        self.cooling_rate = Config.SA_COOLING_RATE
        self.iterations = Config.SA_ITERATIONS

    def _generate_initial_valid_schedule(self) -> Schedule:
        assignments = {}
        for s_id in self.shift_ids:
            candidates = [p.id for p in self.people if s_id in p.allowed_shifts]
            if not candidates:
                raise ValueError(f"Shift {s_id} cannot be assigned to anyone (Hard Constraint Violation).")
            assignments[s_id] = random.choice(candidates)
        return Schedule(assignments)

    def solve(self, run_id: int) -> SimulationResult:
        current_schedule = self._generate_initial_valid_schedule()
        current_energy = self.cost_engine.calculate_total_global_energy(self.people, current_schedule)
        
        best_schedule = current_schedule.copy()
        best_energy = current_energy
        
        temp = self.initial_temp
        
        for _ in range(self.iterations):
            # 1. Mutate
            shift_to_swap = random.choice(self.shift_ids)
            current_owner = current_schedule.assignments[shift_to_swap]
            
            # Find candidates excluding current owner
            candidates = [
                p.id for p in self.people 
                if shift_to_swap in p.allowed_shifts and p.id != current_owner
            ]
            
            if not candidates:
                temp *= self.cooling_rate
                continue
                
            new_owner = random.choice(candidates)
            
            # Create neighbor
            neighbor_schedule = current_schedule.copy()
            neighbor_schedule.assignments[shift_to_swap] = new_owner
            
            # 2. Evaluate
            neighbor_energy = self.cost_engine.calculate_total_global_energy(self.people, neighbor_schedule)
            
            # 3. Acceptance Logic
            delta = neighbor_energy - current_energy
            
            if delta < 0:
                # Better solution
                current_schedule = neighbor_schedule
                current_energy = neighbor_energy
                if current_energy < best_energy:
                    best_energy = current_energy
                    best_schedule = current_schedule.copy()
            else:
                # Worse solution - accept with probability
                if random.random() < math.exp(-delta / temp):
                    current_schedule = neighbor_schedule
                    current_energy = neighbor_energy
            
            # 4. Cool down
            temp *= self.cooling_rate

        # 5. Generate full details for the best result
        final_details = {}
        for p in self.people:
            sids = best_schedule.get_person_shifts(p.id)
            final_details[p.id] = self.cost_engine.calculate_person_details(p, sids)

        return SimulationResult(
            rank=0, # Assigned later
            energy=best_energy,
            schedule=best_schedule,
            details=final_details
        )