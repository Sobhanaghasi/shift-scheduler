# Chejooli

A small shift scheduler using simulated annealing, hard constraints, and interpretable soft costs.

For optimization formulas, see [FORMULAS.md](FORMULAS.md).

## Run

Edit the files in `Input/`, then run:

```bash
venv/bin/python main.py
```

The best three schedules are saved in `Output/`.

## Input Files

### `Input/calendar.json`

```json
{
  "start_date": "2026/05/23",
  "timezone": "Asia/Tehran",
  "organizer_email": "oncall@example.com"
}
```

- `start_date`: day 1 of this schedule unit, in `YYYY/MM/DD`.
- `timezone`: IANA timezone used by ICS events.
- `organizer_email`: organizer written into calendar events.

### `Input/shifts.json`

```json
{
  "id": 10,
  "time_index": 10,
  "assignment_weights": [1.4, 0.6],
  "fixed_assignments": [null, "Mostafa"],
  "calendar_day": 6,
  "calendar_start_day": 6,
  "calendar_start_time": "20:00",
  "calendar_end_day": 7,
  "calendar_end_time": "08:00"
}
```

- `id`: unique numeric shift identifier.
- `time_index`: chronological position used by the distribution cost.
- `assignment_weights`: one entry per required person. Order defines primary, secondary, third, etc.; weight represents workload.
- `fixed_assignments`: optional list aligned with `assignment_weights`. Use a person ID to fix that role or `null` to let the scheduler assign it.
- `calendar_day`: logical day used by the one-shift-per-day hard constraint.
- `calendar_start_day` / `calendar_end_day`: day numbers relative to `calendar.start_date`.
- `calendar_start_time` / `calendar_end_time`: 24-hour `HH:MM` values used in the ICS calendar.

`calendar_day` is separate from event start/end days so an overnight shift can belong to one logical day while ending the next day.

### `Input/people.json`

```json
{
  "id": "Sobhan",
  "email": "sobhan@example.com",
  "portion": 1.0,
  "historical_load_ratio": 1.0,
  "previous_schedule_final_shift_index": -2,
  "previous_schedule_final_shift_weight": 1.0,
  "impossible_shifts": [1, 2],
  "unwanted_coeffs": {
    "6": 40,
    "10": 20
  }
}
```

- `id`: unique person ID; also used by fixed assignments.
- `email`: attendee address written into ICS events.
- `portion`: relative workload capacity. A person with portion `2` should receive twice the load of someone with portion `1`.
- `historical_load_ratio`: moving historical fairness ratio. `1` is balanced, above `1` is historically overloaded, below `1` is underloaded.
- `previous_schedule_final_shift_index`: time index of this person's final assignment in the previous schedule unit. Use `null` when unavailable.
- `previous_schedule_final_shift_weight`: workload weight of that previous final assignment.
- `impossible_shifts`: hard constraint; these shift IDs can never be assigned.
- `unwanted_coeffs`: soft penalties keyed by shift ID. Higher values make the assignment less desirable.

All shifts not listed in `impossible_shifts` are allowed.

### `Input/config.json`

```json
{
  "output_dir": "./Output",
  "cost_function": {
    "lambda_distribution": 2400.0,
    "lambda_load": 360.0,
    "lambda_recency": 0.6
  },
  "hard_constraints": {
    "one_shift_per_person_per_calendar_day": true
  }
}
```

- `output_dir`: destination for generated reports and calendars.
- `lambda_distribution`: importance of spreading workload across time.
- `lambda_load`: importance of matching each person's portion-based fair load.
- `lambda_recency`: current schedule weight in load history, from `0` to `1`. For example, `0.6` means 60% current and 40% historical.
- `one_shift_per_person_per_calendar_day`: when `true`, a person cannot receive two shifts with the same `calendar_day`.

Unwanted-shift cost has no separate lambda; its coefficients are defined per person in `people.json`.

## Algorithm Settings

`.env` contains implementation-level simulated-annealing settings:

- `SA_INITIAL_TEMP`: starting exploration temperature.
- `SA_COOLING_RATE`: temperature multiplier per iteration.
- `SA_ITERATIONS`: iterations per simulation.
- `SA_RUNS`: number of independent simulations.
- `MAX_WORKERS`: maximum parallel processes.

Most users should only edit files under `Input/`.

## Outputs

For each of the top three schedules:

- `best_schedule_N.json`: assignments, global score, and per-person cost breakdown.
- `best_schedule_N.ics`: one calendar file containing all assigned events.

Lower global cost is better. Generated files in `Output/` are overwritten on the next run.
