from __future__ import annotations
import json
import os
from dataclasses import asdict
from typing import Dict, Any, Tuple, List
from domain import CalendarDetails, Person, Shift, SimulationResult
from config import Config
from ics_exporter import ICSExporter

class IOHandler:
    @staticmethod
    def load_input(filepath: str) -> Tuple[Dict[str, float], CalendarDetails, List[Person], List[Shift]]:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        params = {
            "lambda1_distribution": Config.LAMBDA_DIST,
            "lambda2_load": Config.LAMBDA_LOAD,
            "lambda3_recency": Config.LAMBDA_RECENCY
        }

        calendar_data = data.get("calendar", {})
        calendar = CalendarDetails(
            start_date=calendar_data["start_date"],
            timezone=calendar_data["timezone"],
            organizer_email=calendar_data.get("organizer_email", ""),
        )

        shifts = []
        for s_data in data.get("shifts", []):
            shift = Shift(
                id=s_data["id"],
                time_index=s_data["time_index"],
                assignment_weights=s_data["assignment_weights"],
                calendar_block=s_data["calendar_block"],
                fixed_assignments=s_data.get("fixed_assignments", []),
            )
            shifts.append(shift)
        
        people = []
        for p_data in data.get("people", []):
            p = Person(
                id=p_data["id"],
                email=p_data.get("email", ""),
                portion=p_data.get("portion"),
                previous_load_ratio=p_data.get("previous_load_ratio", 1.0),
                last_week_final_shift_index=p_data.get("last_week_final_shift_index"),
                impossible_shifts=set(p_data.get("impossible_shifts", [])),
                unwanted_coeffs=p_data.get("unwanted_coeffs", {}),
            )
            people.append(p)
            
        return params, calendar, people, shifts

    @staticmethod
    def save_results(results: List[SimulationResult], calendar: CalendarDetails, people: List[Person], shifts: List[Shift]):
        os.makedirs(Config.OUTPUT_DIR, exist_ok=True)
        people_by_id = {p.id: p for p in people}
        shifts_by_id = {s.id: s for s in shifts}
        
        for i, res in enumerate(results):
            res.rank = i + 1
            base_path = os.path.join(Config.OUTPUT_DIR, f"best_schedule_{res.rank}")
            json_filename = f"{base_path}.json"
            ics_filename = f"{base_path}.ics"
            
            output_dict = {
                "rank": res.rank,
                "global_energy_score": res.energy,
                "schedule_assignments": res.schedule.assignments,
                "person_cost_breakdown": {
                    pid: asdict(details) for pid, details in res.details.items()
                }
            }
            
            with open(json_filename, 'w') as f:
                json.dump(output_dict, f, indent=2)

            with open(ics_filename, 'w') as f:
                f.write(ICSExporter.build(res, calendar, people_by_id, shifts_by_id))
                
        print(f"Successfully saved {len(results)} schedules to {Config.OUTPUT_DIR}/")
