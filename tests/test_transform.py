"""Unit tests for the processing step (run with: pytest)."""
import json

from src.quality.checks import validate
from src.transformation.transform import UNIFIED_COLUMNS, transform_api_file


def _write_snapshot(tmp_path, players):
    path = tmp_path / "leaderboard_2026-11-25.json"
    path.write_text(json.dumps({"snapshot_date": "2026-11-25", "players": players}))
    return path


def _player(pid, tr=20000.0, gamesplayed=100):
    return {"_id": pid, "username": " Osk ", "country": "es",
            "league": {"tr": tr, "rank": "X+", "gamesplayed": gamesplayed,
                       "apm": 100.0, "pps": 2.5, "vs": 200.0}}


def test_api_file_gets_unified_schema(tmp_path):
    df = transform_api_file(_write_snapshot(tmp_path, [_player("a1")]))
    assert list(df.columns) == UNIFIED_COLUMNS
    row = df.iloc[0]
    assert row["player_id"] == "a1"
    assert row["username"] == "Osk"          # trimmed
    assert row["country"] == "ES"            # upper-case ISO code
    assert row["rank"] == "x+"               # lower-case rank


def test_negative_sentinel_becomes_null(tmp_path):
    df = transform_api_file(_write_snapshot(tmp_path, [_player("a1", gamesplayed=-1)]))
    assert df["gamesplayed"].isna().iloc[0]


def test_quality_removes_duplicates_and_bad_tr(tmp_path):
    players = [_player("a1"), _player("a1"), _player("b2", tr=99999.0)]
    df = validate(transform_api_file(_write_snapshot(tmp_path, players)), "test")
    assert list(df["player_id"]) == ["a1"]
