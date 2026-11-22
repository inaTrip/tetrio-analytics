"""Data quality checks applied to every source after transformation.

Invalid rows are removed and counted, so the logs show exactly how much data
each rule rejected. A check that removes everything stops the pipeline.
"""
import pandas as pd

from src.monitoring.logger import get_logger

log = get_logger("quality")

TR_MIN, TR_MAX = 0, 25_000      # TETR.IO's TR scale


def validate(df: pd.DataFrame, label: str) -> pd.DataFrame:
    """Drop rows breaking the rules below and log what was removed."""
    n_in = len(df)

    # Rule 1: every row needs the join key.
    no_id = df["player_id"].isna()
    df = df[~no_id]

    # Rule 2: one row per player per snapshot (pagination can repeat a player
    # if the leaderboard changes while it is being read).
    dup = df.duplicated(subset=["player_id", "snapshot_date"], keep="last")
    df = df[~dup]

    # Rule 3: TR must be inside the official scale (null is allowed).
    bad_tr = df["tr"].notna() & ~df["tr"].between(TR_MIN, TR_MAX)
    df = df[~bad_tr]

    log.info("[%s] rows in=%d | no id=%d | duplicates=%d | invalid TR=%d | rows out=%d",
             label, n_in, int(no_id.sum()), int(dup.sum()), int(bad_tr.sum()), len(df))

    if df.empty:
        raise ValueError(f"[{label}] no valid rows left after quality checks")
    return df.reset_index(drop=True)
