"""Tests for the star schema load, especially the SCD type 2 logic."""
import duckdb
import pandas as pd

from src.load.warehouse import build


def _snapshots(tmp_path):
    rows = [
        # player a1 renames between 2023 and 2026 -> two versions expected
        ("a1", "2023-09-01", "kaggle_2023", "oldname", "ES", "s", 18000.0),
        ("a1", "2026-11-21", "tetrio_api", "newname", "ES", "x", 24800.0),
        ("a1", "2026-11-22", "tetrio_api", "newname", "ES", "x+", 24900.0),
        # player b2 never changes -> one version
        ("b2", "2026-11-22", "tetrio_api", "bob", None, "a", 12000.0),
    ]
    df = pd.DataFrame(rows, columns=["player_id", "snapshot_date", "source",
                                     "username", "country", "rank", "tr"])
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])
    for col in ["bestrank"]:
        df[col] = df["rank"]
    for col in ["glicko", "rd", "gxe", "apm", "pps", "vs"]:
        df[col] = 1.0
    df["gamesplayed"], df["gameswon"], df["decaying"] = 10, 5, False
    path = tmp_path / "player_snapshots.parquet"
    df.to_parquet(path, index=False)
    return path


def test_scd2_creates_versions_and_point_in_time_join(tmp_path):
    con = duckdb.connect()                       # in-memory database
    counts = build(con, _snapshots(tmp_path))

    assert counts["fact_player_snapshot"] == 4
    assert counts["dim_player"] == 3             # a1 x 2 versions + b2

    versions = con.execute("""
        SELECT username, valid_from::VARCHAR, valid_to::VARCHAR, is_current
        FROM dim_player WHERE player_id = 'a1' ORDER BY valid_from
    """).fetchall()
    assert versions == [
        ("oldname", "2023-09-01", "2026-11-20", False),
        ("newname", "2026-11-21", "9999-12-31", True),
    ]

    # The 2023 fact row must point to the OLD version of the player.
    name_2023 = con.execute("""
        SELECT p.username FROM fact_player_snapshot f
        JOIN dim_player p USING (player_key) WHERE f.source = 'kaggle_2023'
    """).fetchone()[0]
    assert name_2023 == "oldname"


def test_rank_order_is_respected(tmp_path):
    con = duckdb.connect()
    build(con, _snapshots(tmp_path))
    order = dict(con.execute("SELECT rank_code, rank_order FROM dim_rank_tier").fetchall())
    assert order["a"] < order["s"] < order["x"] < order["x+"]
