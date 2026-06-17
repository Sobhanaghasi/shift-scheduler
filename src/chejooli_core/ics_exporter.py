from __future__ import annotations
import uuid
from datetime import datetime, timedelta
from typing import Dict, Tuple
from .domain import CalendarDetails, Person, Shift
from .models import RankedSchedule


def build_ics(
    ranked_schedule: RankedSchedule,
    calendar: CalendarDetails,
    people: list[Person],
    shifts: list[Shift],
) -> str:
    people_by_id = {person.id: person for person in people}
    shifts_by_id = {shift.id: shift for shift in shifts}
    now_stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Chejooli//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:REQUEST",
        "X-WR-CALNAME:Shift Schedule",
        f"X-WR-TIMEZONE:{calendar.timezone}",
    ]

    for shift_id in sorted(ranked_schedule.assignments):
        shift = shifts_by_id[int(shift_id)]
        start_dt, end_dt = _shift_datetimes(calendar, shift)
        assignees = ranked_schedule.assignments[shift_id]
        for slot_index, person_id in enumerate(assignees):
            person = people_by_id[person_id]
            uid = f"schedule-{ranked_schedule.rank}-shift-{shift.id}-slot-{slot_index}-{uuid.uuid4()}@chejooli"
            summary = f"Shift {shift.id}: {person_id}"
            description = _role_label(slot_index)
            lines.extend([
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{now_stamp}",
                f"DTSTART;TZID={calendar.timezone}:{start_dt.strftime('%Y%m%dT%H%M%S')}",
                f"DTEND;TZID={calendar.timezone}:{end_dt.strftime('%Y%m%dT%H%M%S')}",
                "SEQUENCE:0",
                f"SUMMARY:{_escape_ics_text(summary)}",
                f"DESCRIPTION:{_escape_ics_text(description)}",
                f"CATEGORIES:{_escape_ics_text(person_id)}",
            ])
            if calendar.organizer_email:
                lines.append(f"ORGANIZER;CN=Shift Scheduler:mailto:{calendar.organizer_email}")
            if person.email:
                attendee_name = _escape_ics_param(person_id)
                lines.append(
                    f"ATTENDEE;CN={attendee_name};CUTYPE=INDIVIDUAL;ROLE=REQ-PARTICIPANT;"
                    f"PARTSTAT=NEEDS-ACTION;RSVP=TRUE:mailto:{person.email}"
                )
            lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def save_ics_files(
    ranked_schedules: list[RankedSchedule],
    calendar: CalendarDetails,
    people: list[Person],
    shifts: list[Shift],
    output_dir: str,
) -> None:
    from pathlib import Path
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    for ranked_schedule in ranked_schedules:
        filename = output_path / f"best_schedule_{ranked_schedule.rank}.ics"
        filename.write_text(build_ics(ranked_schedule, calendar, people, shifts))


def _role_label(slot_index: int) -> str:
    if slot_index == 0:
        return "Primary On-Call"
    if slot_index == 1:
        return "Secondary On-Call"
    return f"{_ordinal(slot_index + 1)} On-Call"


def _ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def _shift_datetimes(calendar: CalendarDetails, shift: Shift) -> Tuple[datetime, datetime]:
    start_time = _parse_time(shift.calendar_start_time)
    end_time = _parse_time(shift.calendar_end_time)
    schedule_start = datetime.strptime(calendar.start_date, "%Y/%m/%d")
    start_date = schedule_start + timedelta(days=shift.calendar_start_day - 1)
    end_date = schedule_start + timedelta(days=shift.calendar_end_day - 1)
    start_dt = start_date.replace(hour=start_time[0], minute=start_time[1])
    end_dt = end_date.replace(hour=end_time[0], minute=end_time[1])
    if end_dt <= start_dt:
        raise ValueError(f"Shift {shift.id} calendar end must be after calendar start.")
    return start_dt, end_dt


def _parse_time(value: str) -> Tuple[int, int]:
    hour_str, minute_str = value.split(":")
    hour = int(hour_str)
    minute = int(minute_str)
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Invalid time value: {value}")
    return hour, minute


def _escape_ics_param(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace(":", "\\:")


def _escape_ics_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
