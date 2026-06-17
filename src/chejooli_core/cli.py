from __future__ import annotations
import argparse
import sys
from dotenv import load_dotenv
from .api import solve_schedule
from .ics_exporter import save_ics_files
from .json_io import apply_algorithm_env, load_request_from_directory, save_result_to_directory
from .models import ScheduleInfeasibleError, ScheduleValidationError


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments and dispatch the requested command."""
    parser = argparse.ArgumentParser(prog="chejooli")
    subparsers = parser.add_subparsers(dest="command")

    solve_parser = subparsers.add_parser("solve", help="solve a schedule")
    solve_parser.add_argument("--input", default="Input", help="input directory containing calendar.json, shifts.json, people.json, config.json")
    solve_parser.add_argument("--output", default=None, help="output directory; defaults to output_dir from config.json")
    solve_parser.add_argument("--ics", action="store_true", help="also write .ics calendar files")

    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        argv = ["solve"]
    args = parser.parse_args(argv)
    if args.command == "solve":
        return _solve(args)
    parser.print_help()
    return 1


def _solve(args) -> int:
    """Load file inputs, solve the request, and write selected outputs."""
    load_dotenv()
    try:
        request = apply_algorithm_env(load_request_from_directory(args.input))
        if args.output is not None:
            request.scheduler_config.output_dir = args.output
        result = solve_schedule(request)
        save_result_to_directory(result, request.scheduler_config.output_dir)
        if args.ics:
            save_ics_files(
                result.ranked_schedules,
                request.calendar,
                request.people,
                request.shifts,
                request.scheduler_config.output_dir,
            )
    except ScheduleValidationError as exc:
        print("Invalid schedule request:", file=sys.stderr)
        for issue in exc.issues:
            location = f"{issue.path}: " if issue.path else ""
            print(f"- {location}{issue.message}", file=sys.stderr)
        return 2
    except ScheduleInfeasibleError as exc:
        print("No feasible schedule found:", file=sys.stderr)
        for issue in exc.issues:
            print(f"- {issue.message}", file=sys.stderr)
        return 3

    print(f"Successfully saved {len(result.ranked_schedules)} schedules to {request.scheduler_config.output_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
