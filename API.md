# Chejooli Core API

The backend should use the Python API, not CLI files.

## Install

During backend development:

```bash
pip install -e ../chejooli-core
```

Install from Hamravesh Artifactory with a pinned package version (matches the git release tag):

```toml
chejooli-core==5.2
```

```bash
pip install chejooli-core==5.2 \
  --index-url https://repo.hsre.ir/artifactory/api/pypi/pypi/simple
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

Hard constraints live on `Person.impossible_shifts`, `Shift.conflicting_shifts`, and fixed assignments.

`SchedulerConfig` contains scheduler policy:

- cost lambdas
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
    issues = [issue.to_dict() for issue in exc.issues]
except ScheduleInfeasibleError as exc:
    issues = [issue.to_dict() for issue in exc.issues]
```

Validation errors mean the request is malformed or inconsistent. Infeasible errors mean the request is valid but no schedule satisfies the hard constraints.
