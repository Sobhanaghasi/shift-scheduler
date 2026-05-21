from __future__ import annotations
import json
import os
import re
import uuid
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, List
from domain import CalendarDetails, Person, Shift, SimulationResult
from config import Config

class IOHandler:
    @staticmethod
    def load_input(filepath: str) -> Tuple[Dict[str, float], CalendarDetails, List[Person], List[Shift]]:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # 1. Load Parameters directly from Environment (Config)
        # The scheduler expects these specific keys
        params = {
            "lambda1_distribution": Config.LAMBDA_DIST,
            "lambda2_load": Config.LAMBDA_LOAD,
            "lambda3_recency": Config.LAMBDA_RECENCY
        }

        calendar_data = data.get("calendar", {})
        calendar = CalendarDetails(
            start_date=calendar_data["start_date"],
            timezone=calendar_data["timezone"],
        )

        # 2. Parse Shifts
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
        
        # 3. Parse People
        people = []
        for p_data in data.get("people", []):
            p = Person(
                id=p_data["id"],
                portion=p_data.get("portion"),
                previous_load_ratio=p_data.get("previous_load_ratio", 1.0),
                last_week_final_shift_index=p_data.get("last_week_final_shift_index"),
                impossible_shifts=set(p_data.get("impossible_shifts", [])),
                unwanted_coeffs=p_data.get("unwanted_coeffs", {}),
                calendar_color=p_data.get("calendar_color", ""),
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
                f.write(IOHandler._build_ics(res, calendar, people_by_id, shifts_by_id))
                
        print(f"Successfully saved {len(results)} schedules to {Config.OUTPUT_DIR}/")

    @staticmethod
    def _build_ics(res: SimulationResult, calendar: CalendarDetails, people_by_id: Dict[str, Person], shifts_by_id: Dict[int, Shift]) -> str:
        now_stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Shift Scheduler//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "X-WR-CALNAME:Shift Schedule",
            f"X-WR-TIMEZONE:{calendar.timezone}",
        ]

        for shift_id in sorted(res.schedule.assignments):
            shift = shifts_by_id[int(shift_id)]
            start_dt, end_dt = IOHandler._shift_datetimes(calendar, shift.calendar_block)
            assignees = res.schedule.assignments[shift_id]
            all_assignees = ", ".join(assignees)
            for slot_index, person_id in enumerate(assignees):
                person = people_by_id[person_id]
                slot_weight = shift.slot_weight(slot_index)
                uid = f"schedule-{res.rank}-shift-{shift.id}-slot-{slot_index}-{uuid.uuid4()}@shift-scheduler"
                summary = f"Shift {shift.id}: {person_id}"
                description = f"Shift {shift.id}\nSlot: {slot_index + 1}\nWeight: {slot_weight}\nAssignees: {all_assignees}"
                lines.extend([
                    "BEGIN:VEVENT",
                    f"UID:{uid}",
                    f"DTSTAMP:{now_stamp}",
                    f"DTSTART;TZID={calendar.timezone}:{start_dt.strftime('%Y%m%dT%H%M%S')}",
                    f"DTEND;TZID={calendar.timezone}:{end_dt.strftime('%Y%m%dT%H%M%S')}",
                    f"SUMMARY:{IOHandler._escape_ics_text(summary)}",
                    f"DESCRIPTION:{IOHandler._escape_ics_text(description)}",
                    f"CATEGORIES:{IOHandler._escape_ics_text(person_id)}",
                ])
                if person.calendar_color:
                    lines.append(f"COLOR:{person.calendar_color}")
                    lines.append(f"X-GOOGLE-CALENDAR-COLOR:{person.calendar_color}")
                lines.append("END:VEVENT")

        lines.append("END:VCALENDAR")
        return "\r\n".join(lines) + "\r\n"

    @staticmethod
    def _shift_datetimes(calendar: CalendarDetails, calendar_block: str) -> Tuple[datetime, datetime]:
        match = re.fullmatch(r"\s*(\d+)\s*-\s*(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})\s*", calendar_block)
        if not match:
            raise ValueError(f"Invalid calendar_block: {calendar_block}. Expected like '1 - 08:00-15:00'.")

        day_number = int(match.group(1))
        start_time = IOHandler._parse_time(match.group(2))
        end_time = IOHandler._parse_time(match.group(3))
        start_date = datetime.strptime(calendar.start_date, "%Y/%m/%d") + timedelta(days=day_number - 1)
        start_dt = start_date.replace(hour=start_time[0], minute=start_time[1])
        end_dt = start_date.replace(hour=end_time[0], minute=end_time[1])
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)
        return start_dt, end_dt

    @staticmethod
    def _parse_time(value: str) -> Tuple[int, int]:
        hour_str, minute_str = value.split(":")
        hour = int(hour_str)
        minute = int(minute_str)
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError(f"Invalid time value: {value}")
        return hour, minute

    @staticmethod
    def _escape_ics_text(value: str) -> str:
        return (
            value.replace("\\", "\\\\")
            .replace(";", "\\;")
            .replace(",", "\\,")
            .replace("\n", "\\n")
        )
