"""Processing: convert each raw source into one common, clean table schema.

Both sources end up with exactly the same columns and types (UNIFIED_COLUMNS),
which is what makes the integration step a simple concatenation and join.
"""
import json
from pathlib import Path

import pandas as pd

from src import settings
from src.monitoring.logger import get_logger

log = get_logger("transformation")

# Common schema for one player on one snapshot date.
UNIFIED_COLUMNS = [
    "player_id", "snapshot_date", "source", "username", "country",
    "rank", "bestrank", "tr", "glicko", "rd", "gxe",
    "apm", "pps", "vs", "gamesplayed", "gameswon", "decaying",
]
FLOAT_COLUMNS = ["tr", "glicko", "rd", "gxe", "apm", "pps", "vs"]
COUNT_COLUMNS = ["gamesplayed", "gameswon"]
TEXT_COLUMNS = ["player_id", "source", "username", "country", "rank", "bestrank"]


def transform_api_file(path: Path) -> pd.DataFrame:
    """D1: flatten one raw leaderboard JSON into the unified schema."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    # json_normalize turns {"league": {"tr": ...}} into a column "league.tr"
    df = pd.json_normalize(payload["players"])
    df.columns = [c.removeprefix("league.") for c in df.columns]
    df = df.rename(columns={"_id": "player_id"})
    df["snapshot_date"] = payload["snapshot_date"]
    df["source"] = "tetrio_api"
    return standardise(df, label=path.stem)


def transform_kaggle_file(path: Path) -> pd.DataFrame:
    """D2: map the 2023 CSV onto the unified schema."""
    df = pd.read_csv(path)
    # 40l_sprint and blitz are not in the API leaderboard: they are dropped by
    # standardise(), which keeps only UNIFIED_COLUMNS.
    df = df.rename(columns={"id": "player_id"})
    df["snapshot_date"] = settings.KAGGLE_SNAPSHOT_DATE
    df["source"] = "kaggle_2023"
    return standardise(df, label="kaggle_2023")


def standardise(df: pd.DataFrame, label: str) -> pd.DataFrame:
    """Same columns, same types and same conventions for every source."""
    # Columns missing in a source (e.g. gxe, decaying in 2023) become null.
    for col in UNIFIED_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    df = df[UNIFIED_COLUMNS].copy()

    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])

    # Numbers: nullable dtypes (Float64/Int64) keep missing values as <NA>
    # instead of silently turning integer columns into floats.
    # Negative values are sentinels (the API uses -1 for "hidden/unknown"):
    # none of these metrics can be negative, so they are converted to null.
    for col in FLOAT_COLUMNS + COUNT_COLUMNS:
        values = pd.to_numeric(df[col], errors="coerce")
        n_sentinel = int((values < 0).sum())
        if n_sentinel:
            log.info("[%s] %s: %d negative sentinel values -> null",
                     label, col, n_sentinel)
        values = values.mask(values < 0)
        df[col] = values.astype("Int64" if col in COUNT_COLUMNS else "Float64")

    # Text: trimmed, consistent case (ranks lower-case, ISO country upper-case).
    for col in TEXT_COLUMNS:
        df[col] = df[col].astype("string").str.strip()
    df["rank"] = df["rank"].str.lower()
    df["bestrank"] = df["bestrank"].str.lower()
    df["country"] = df["country"].str.upper()

    df["decaying"] = df["decaying"].astype("boolean")
    return df
