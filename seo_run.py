"""
SEO/AEO/GEO Engine — command-line entry point.

    python seo_run.py                 # generate + publish ONE article, then exit
    python seo_run.py --schedule      # run every 24h, forever
    python seo_run.py --schedule --hours 12
    python seo_run.py --rebuild       # re-render the site from stored articles
    python seo_run.py --no-email      # skip the notification email

The GitHub Actions workflow (.github/workflows/seo-engine.yml) runs the
single-shot mode on a daily cron — that is the fully hands-off setup.
"""

import argparse
import time
from datetime import datetime


def main():
    parser = argparse.ArgumentParser(description="G Squared SEO/AEO/GEO Engine")
    parser.add_argument("--schedule", action="store_true",
                        help="Keep running on an interval instead of once")
    parser.add_argument("--hours", type=float, default=24,
                        help="Interval between runs in hours (default: 24)")
    parser.add_argument("--rebuild", action="store_true",
                        help="Only re-render the site from stored articles")
    parser.add_argument("--no-email", action="store_true",
                        help="Skip the notification email")
    args = parser.parse_args()

    if args.rebuild:
        from seo_engine import publisher
        publisher.build_site()
        return

    from seo_engine import engine

    if not args.schedule:
        engine.run_cycle(notify=not args.no_email)
        return

    print(f"[SEO Engine] Scheduled mode: every {args.hours}h. Ctrl+C to stop.\n")
    while True:
        print(f"[SEO Engine] Run starting {datetime.now():%Y-%m-%d %H:%M:%S}")
        try:
            engine.run_cycle(notify=not args.no_email)
        except Exception as e:
            print(f"[SEO Engine] Run failed: {e}")
        print(f"[SEO Engine] Next run in {args.hours}h\n")
        time.sleep(args.hours * 3600)


if __name__ == "__main__":
    main()
