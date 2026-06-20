# Chejooli Core

`chejooli-core` is the scheduling engine for Chejooli. It can be used as a simple CLI app or installed as a Python package by the backend.

For optimization formulas, see [FORMULAS.md](FORMULAS.md). For Python/backend usage, see [API.md](API.md).

## Install for Local Use

```bash
python -m venv .venv
.venv/bin/pip install -e .
```

## CLI

Default input/output folders:

```bash
chejooli solve
```

Explicit folders:

```bash
chejooli solve --input ./Input --output ./Output
```

Generate calendar files too:

```bash
chejooli solve --ics
```

By default the CLI writes JSON reports only. `--ics` also writes `.ics` files.

## Input Files

The CLI reads four files from the input directory.

### `calendar.json`

```json
{
  "start_date": "2026/05/23",
  "timezone": "Asia/Tehran",
  "organizer_email": "oncall@example.com"
}
```

- `start_date`: day 1 of the schedule unit, in `YYYY/MM/DD`.
- `timezone`: IANA timezone used in ICS exports.
- `organizer_email`: organizer written into calendar events.

### `shifts.json`

```json
{
  "id": 10,
  "time_index": 10,
  "assignment_weights": [1.4, 0.6],
  "conflicting_shifts": [9, 11],
  "fixed_assignments": [null, "Mostafa"],
  "calendar_start_day": 6,
  "calendar_start_time": "20:00",
  "calendar_end_day": 7,
  "calendar_end_time": "08:00"
}
```

- `id`: unique shift ID.
- `time_index`: chronological index used by spacing/distribution cost.
- `assignment_weights`: one required person per item; order means primary, secondary, third, etc.
- `conflicting_shifts`: hard constraints; a person assigned here cannot also be assigned to these shifts. Conflicts are treated as symmetric.
- `fixed_assignments`: optional list aligned with `assignment_weights`; use `null` for scheduler-chosen roles.
- `calendar_start_day` / `calendar_end_day`: event day numbers relative to `calendar.start_date`.
- `calendar_start_time` / `calendar_end_time`: event times in `HH:MM`.

### `people.json`

```json
{
  "id": "Sobhan",
  "email": "sobhan@example.com",
  "portion": 1.0,
  "historical_load_ratio": 1.0,
  "previous_schedule_final_shift_index": -2,
  "previous_schedule_final_shift_weight": 1.0,
  "impossible_shifts": [1, 2],
  "unwanted_coeffs": {"6": 40}
}
```

- `portion`: relative expected workload share.
- `historical_load_ratio`: moving load history; `1` means balanced.
- `previous_schedule_final_shift_index`: previous schedule boundary index; use `null` if unavailable.
- `previous_schedule_final_shift_weight`: workload of that previous boundary shift.
- `impossible_shifts`: hard constraints.
- `unwanted_coeffs`: soft penalties by shift ID.

All shifts not listed in `impossible_shifts` are allowed.

### `config.json`

```json
{
  "output_dir": "./Output",
  "cost_function": {
    "lambda_distribution": 2400.0,
    "lambda_load": 360.0,
    "lambda_recency": 0.6
  }
}
```

- `lambda_distribution`: importance of spreading workload over time.
- `lambda_load`: importance of fair portion-based load.
- `lambda_recency`: current schedule weight in load history; `0.6` means 60% current and 40% history.

## Algorithm Environment

Optional `.env` values tune the annealing search:

```env
SA_INITIAL_TEMP=20
SA_COOLING_RATE=0.9985
SA_ITERATIONS=2000
SA_RUNS=25
MAX_WORKERS=25
```

These are CLI/runtime settings, not scheduling policy.

## Outputs

For each top schedule:

- `best_schedule_N.json`: assignments and cost breakdown.
- `best_schedule_N.ics`: optional calendar export when `--ics` is used.

Lower global cost is better.
