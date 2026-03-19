"""
Optional scheduler — runs the pipeline on a recurring schedule,
mimicking the Make.com scheduled trigger (the clock icon on the Dropbox module).

Usage:
    python scheduler.py              # runs every 24 hours (default)
    python scheduler.py --hours 12   # runs every 12 hours
"""

import argparse
import time
from datetime import datetime

from main import run_pipeline


def run_on_schedule(interval_hours: float):
    """Run the pipeline immediately, then repeat on the given interval."""
    interval_seconds = interval_hours * 3600
    print(f"[Scheduler] Running every {interval_hours} hour(s). Press Ctrl+C to stop.\n")

    while True:
        print(f"[Scheduler] Starting run at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        try:
            run_pipeline()
        except Exception as e:
            print(f"[Scheduler] Pipeline error: {e}")

        print(f"[Scheduler] Next run in {interval_hours} hour(s)...\n")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scheduled LinkedIn Content Generator")
    parser.add_argument(
        "--hours",
        type=float,
        default=24,
        help="Interval between runs in hours (default: 24)",
    )
    args = parser.parse_args()
    run_on_schedule(args.hours)
