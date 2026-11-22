"""Central configuration: paths, API settings and environment variables.

Every module imports its settings from here, so a path or a limit is
changed in one place only.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Repository root = the folder that contains src/
ROOT = Path(__file__).resolve().parent.parent

# Load secrets (Kaggle token, User-Agent...) from .env into os.environ.
# The kaggle CLI, called as a subprocess, inherits these variables.
load_dotenv(ROOT / ".env")

# ---------- Paths (storage layers) ----------
DATA_DIR = ROOT / "data"
RAW_API_DIR = DATA_DIR / "raw" / "tetrio"       # raw layer, D1 (one JSON per day)
RAW_KAGGLE_DIR = DATA_DIR / "raw" / "tl_data"   # raw layer, D2 (one-off download)
CURATED_DIR = DATA_DIR / "curated"              # cleaned + integrated tables
LOG_DIR = ROOT / "logs"

# ---------- D1: TETR.IO API ----------
TETRIO_BASE_URL = "https://ch.tetr.io/api"
TETRIO_USER_AGENT = os.getenv(
    "TETRIO_USER_AGENT", "tetrio-analytics-usj (student project)"
)
PAGE_LIMIT = 100          # players per request (API maximum)
REQUEST_DELAY_S = 1.0     # API rule: about one request per second
MAX_RETRIES = 5           # attempts per page before giving up
MAX_PAGES = 2000          # safety cap: stops an endless loop if pagination breaks

# ---------- D2: Kaggle 2023 snapshot ----------
KAGGLE_SLUG = "inferno2332/tl-data"
KAGGLE_FILE = "tl-data-09-2023.csv"
# The file name only gives the month; the 1st is used as an approximation.
KAGGLE_SNAPSHOT_DATE = "2023-09-01"
