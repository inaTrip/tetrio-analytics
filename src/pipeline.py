"""End-to-end pipeline: ingestion -> processing -> integration.

Run from the repository root:
    python -m src.pipeline              # full run (fetches today's snapshot)
    python -m src.pipeline --skip-fetch # reuse existing raw files (no API calls)
"""
import argparse
import sys
import time

from src.ingestion import kaggle_loader, tetrio_api
from src.monitoring.logger import get_logger
from src.transformation import integrate

log = get_logger("main")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TETR.IO daily pipeline")
    parser.add_argument("--skip-fetch", action="store_true",
                        help="do not call the API; process existing raw files")
    args = parser.parse_args(argv)

    started = time.monotonic()
    log.info("Pipeline started")
    try:
        kaggle_loader.run()                 # D2: one-off, skipped if present
        if args.skip_fetch:
            log.info("--skip-fetch: using existing raw API snapshots")
        else:
            tetrio_api.run()                # D1: today's snapshot
        integrate.run()                     # processing + integration
    except Exception:
        # log.exception records the full traceback in logs/pipeline.log.
        # This is the hook where the alerting step will be added.
        log.exception("Pipeline FAILED after %.0f s", time.monotonic() - started)
        return 1

    log.info("Pipeline finished OK in %.0f s", time.monotonic() - started)
    return 0


if __name__ == "__main__":
    sys.exit(main())
