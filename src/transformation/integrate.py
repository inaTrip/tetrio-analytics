"""Integration: combine D1 and D2 into the curated tables.

Outputs (data/curated/, Parquet):
  - player_snapshots.parquet : one row per player per snapshot, both sources
  - players.parquet          : one row per player (latest name, first/last seen)
  - player_progression.parquet : players present in 2023 AND in the latest
                                 API snapshot, joined on player_id

The curated layer is rebuilt from all raw files on every run. At the current
volume this takes seconds and makes the step idempotent: re-running it never
creates duplicates. At larger scales it would become incremental.
"""
import pandas as pd

from src import settings
from src.monitoring.logger import get_logger
from src.quality.checks import validate
from src.transformation.transform import transform_api_file, transform_kaggle_file

log = get_logger("integration")

PROGRESSION_METRICS = ["rank", "tr", "apm", "pps", "vs"]


def build_snapshots() -> pd.DataFrame:
    """Transform and validate every raw file, then stack them."""
    kaggle_path = settings.RAW_KAGGLE_DIR / settings.KAGGLE_FILE
    frames = [validate(transform_kaggle_file(kaggle_path), "kaggle_2023")]

    api_files = sorted(settings.RAW_API_DIR.glob("leaderboard_*.json"))
    if not api_files:
        raise FileNotFoundError("No raw API snapshots found in data/raw/tetrio/")
    for path in api_files:
        frames.append(validate(transform_api_file(path), path.stem))

    snapshots = pd.concat(frames, ignore_index=True)
    log.info("Snapshots table: %d rows, %d API days + 2023 baseline",
             len(snapshots), len(api_files))
    return snapshots


def build_players(snapshots: pd.DataFrame) -> pd.DataFrame:
    """One row per player, keeping the most recent username and country."""
    ordered = snapshots.sort_values("snapshot_date")
    players = ordered.groupby("player_id").agg(
        username=("username", "last"),      # usernames can change over time
        country=("country", "last"),
        first_seen=("snapshot_date", "min"),
        last_seen=("snapshot_date", "max"),
        n_snapshots=("snapshot_date", "nunique"),
    ).reset_index()
    ids_2023 = set(snapshots.loc[snapshots["source"] == "kaggle_2023", "player_id"])
    players["in_2023"] = players["player_id"].isin(ids_2023)
    return players


def build_progression(snapshots: pd.DataFrame) -> pd.DataFrame:
    """Join the 2023 baseline with the latest API snapshot on player_id."""
    base = snapshots[snapshots["source"] == "kaggle_2023"]
    api = snapshots[snapshots["source"] == "tetrio_api"]
    latest = api[api["snapshot_date"] == api["snapshot_date"].max()]

    cols = ["player_id"] + PROGRESSION_METRICS
    progression = base[cols].merge(
        latest[cols + ["username"]], on="player_id", how="inner",
        suffixes=("_2023", "_now"),
    )
    progression["tr_change"] = progression["tr_now"] - progression["tr_2023"]

    log.info("Join 2023 <-> latest snapshot: %d of %d current players were "
             "already ranked in 2023 (%.0f%%)",
             len(progression), len(latest),
             100 * len(progression) / max(len(latest), 1))
    return progression


def run():
    """Build and save all curated tables."""
    snapshots = build_snapshots()
    players = build_players(snapshots)
    progression = build_progression(snapshots)

    settings.CURATED_DIR.mkdir(parents=True, exist_ok=True)
    for name, table in [("player_snapshots", snapshots), ("players", players),
                        ("player_progression", progression)]:
        path = settings.CURATED_DIR / f"{name}.parquet"
        table.to_parquet(path, index=False)
        log.info("Saved %s (%d rows)", path.relative_to(settings.ROOT), len(table))
    return snapshots, players, progression


if __name__ == "__main__":
    run()
