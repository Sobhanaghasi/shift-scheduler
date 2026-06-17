# Chejooli Core API

The backend should use the Python API, not CLI files.

## Install

During backend development:

```bash
pip install -e ../chejooli-core
```

In production, depend on a pinned package version:

```toml
chejooli-core==0.1.0
```

## Main Interface

```python
from chejooli_core import solve_schedule
from chejooli_core.models import ScheduleRequest

result = solve_schedule(request)
```

The core interface is always:

```text
ScheduleRequest -> solve_schedule() -> ScheduleResult
```

The backend adapter should convert database/API data into `ScheduleRequest`, call `solve_schedule`, then store the structured result.

## Request Model

```python
from chejooli_core import (
    AlgorithmConfig,
    CalendarDetails,
    Person,
    ScheduleRequest,
    SchedulerConfig,
    Shift,
)

request = ScheduleRequest(
    calendar=CalendarDetails(...),
    shifts=[Shift(...)],
    people=[Person(...)],
    scheduler_config=SchedulerConfig(...),
    algorithm_config=AlgorithmConfig(...),
)
```

`SchedulerConfig` contains scheduling policy:

- cost lambdas
- hard constraints
- output directory for CLI use

`AlgorithmConfig` contains runtime search settings:

- initial temperature
- cooling rate
- iterations
- independent runs
- max workers

For backend usage, pass both configs explicitly. Do not rely on `.env` or `Input/` files.

## Result Model

```python
result.ranked_schedules[0].rank
result.ranked_schedules[0].global_energy_score
result.ranked_schedules[0].assignments
result.ranked_schedules[0].person_cost_breakdown
```

Use `ranked_schedule.to_dict()` to serialize a schedule result.

## Errors

```python
from chejooli_core import ScheduleInfeasibleError, ScheduleValidationError

try:
    result = solve_schedule(request)
except ScheduleValidationError as exc:
    # invalid input, map to HTTP 400
    issues = [issue.to_dict() for issue in exc.issues]
except ScheduleInfeasibleError as exc:
    # valid input, impossible hard constraints, map to HTTP 422
    issues = [issue.to_dict() for issue in exc.issues]
```

Validation errors mean the request is malformed or inconsistent. Infeasible errors mean the request is valid but no schedule satisfies the hard constraints.

## Optional ICS Export

ICS is not part of solving. Generate it explicitly only when needed:

```python
from chejooli_core.ics_exporter import build_ics

ics_text = build_ics(
    result.ranked_schedules[0],
    request.calendar,
    request.people,
    request.shifts,
)
```

The backend can ignore ICS completely unless it wants calendar exports.
