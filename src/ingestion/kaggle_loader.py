"""Ingestion of dataset D2: the September 2023 Tetra League snapshot (Kaggle).

This is a one-off load: the file never changes, so it is only downloaded if
it is not already in the raw layer. The download uses the kaggle CLI with the
KAGGLE_API_TOKEN loaded from .env by src/settings.py.
"""
import subprocess

from src import settings
from src.monitoring.logger import get_logger

log = get_logger("ingestion.kaggle")


def run(force: bool = False):
    """Download D2 unless it is already present; return the CSV path."""
    target = settings.RAW_KAGGLE_DIR / settings.KAGGLE_FILE
    if target.exists() and not force:
        log.info("D2 already in raw layer, skipping download: %s",
                 target.relative_to(settings.ROOT))
        return target

    settings.RAW_KAGGLE_DIR.mkdir(parents=True, exist_ok=True)
    log.info("Downloading Kaggle dataset %s", settings.KAGGLE_SLUG)
    subprocess.run(
        ["kaggle", "datasets", "download", "-d", settings.KAGGLE_SLUG,
         "-p", str(settings.RAW_KAGGLE_DIR), "--unzip"],
        check=True,          # raise an error if the download fails
    )
    if not target.exists():
        raise FileNotFoundError(f"Expected file not found after download: {target}")
    return target


if __name__ == "__main__":
    run()
