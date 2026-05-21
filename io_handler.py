from __future__ import annotations
import json
import os
from dataclasses import asdict
from typing import Dict, Any, Tuple, List
from domain import Person, Shift, SimulationResult
from config import Config

class IOHandler:
    @staticmethod
    def load_input(filepath: str) -> Tuple[Dict[str, float], List[Person], List[Shift]]:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # 1. Load Parameters directly from Environment (Config)
        # The scheduler expects these specific keys
        params = {
            "lambda1_distribution": Config.LAMBDA_DIST,
            "lambda2_load": Config.LAMBDA_LOAD,
            "lambda3_recency": Config.LAMBDA_RECENCY
        }

        # 2. Parse Shifts
        shifts = []
        for s_data in data.get("shifts", []):
            shift = Shift(
                id=s_data["id"],
                time_index=s_data["time_index"],
                assignment_weights=s_data["assignment_weights"],
                fixed_assignments=s_data.get("fixed_assignments", []),
            )
            shifts.append(shift)
        
        # 3. Parse People
        people = []
        for p_data in data.get("people", []):
            p = Person(
                id=p_data["id"],
                portion=p_data.get("portion"),
                previous_load_ratio=p_data.get("previous_load_ratio", 1.0),
                last_week_final_shift_index=p_data.get("last_week_final_shift_index"),
                impossible_shifts=set(p_data.get("impossible_shifts", [])),
                unwanted_coeffs=p_data.get("unwanted_coeffs", {})
            )
            people.append(p)
            
        return params, people, shifts

    @staticmethod
    def save_results(results: List[SimulationResult]):
        os.makedirs(Config.OUTPUT_DIR, exist_ok=True)
        
        for i, res in enumerate(results):
            res.rank = i + 1
            filename = os.path.join(Config.OUTPUT_DIR, f"best_schedule_{res.rank}.json")
            
            # Convert Dataclasses to Dict
            output_dict = {
                "rank": res.rank,
                "global_energy_score": res.energy,
                "schedule_assignments": res.schedule.assignments,
                "person_cost_breakdown": {
                    pid: asdict(details) for pid, details in res.details.items()
                }
            }
            
            with open(filename, 'w') as f:
                json.dump(output_dict, f, indent=2)
                
        print(f"Successfully saved {len(results)} schedules to {Config.OUTPUT_DIR}/")