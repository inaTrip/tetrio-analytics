"""Load stage: build the star schema in a DuckDB warehouse.

Reads data/curated/player_snapshots.parquet and builds the tables defined in
warehouse/schema.sql using the SQL in warehouse/load.sql.

DuckDB is used as a local, file-based analytical warehouse for development:
no server, free, standard SQL, reads Parquet directly. The SQL is kept in
separate files so it can be ported to a cloud warehouse (e.g. BigQuery) later.
"""
from pathlib import Path

import duckdb

from src import settings
from src.monitoring.logger import get_logger

log = get_logger("load.warehouse")

SCHEMA_SQL = settings.WAREHOUSE_SQL_DIR / "schema.sql"
LOAD_SQL = settings.WAREHOUSE_SQL_DIR / "load.sql"
TABLES = ["dim_date", "dim_rank_tier", "dim_player", "fact_player_snapshot"]


def build(con: duckdb.DuckDBPyConnection, snapshots_path: Path) -> dict[str, int]:
    """Create and load all tables on an open connection; return row counts."""
    # Staging view: the curated Parquet file, read in place (no copy).
    safe_path = str(snapshots_path).replace("'", "''")
    con.execute(f"CREATE OR REPLACE TEMP VIEW stg_snapshots AS "
                f"SELECT * FROM read_parquet('{safe_path}')")

    con.execute(SCHEMA_SQL.read_text(encoding="utf-8"))   # drop + create tables
    con.execute(LOAD_SQL.read_text(encoding="utf-8"))     # dimensions, then fact

    counts = {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in TABLES}
    _check(con, counts)
    return counts


def _check(con: duckdb.DuckDBPyConnection, counts: dict[str, int]) -> None:
    """Integrity checks: every staged row must land in the fact table once."""
    staged = con.execute("SELECT count(*) FROM stg_snapshots").fetchone()[0]
    if counts["fact_player_snapshot"] != staged:
        # Fewer rows = a snapshot matched no player version; more = matched two.
        raise ValueError(f"Fact rows ({counts['fact_player_snapshot']}) "
                         f"!= staged rows ({staged}): SCD2 join is inconsistent")

    unknown = con.execute(
        "SELECT list(rank_code) FROM dim_rank_tier WHERE rank_order IS NULL"
    ).fetchone()[0]
    if unknown:
        log.warning("Unknown rank codes added to dim_rank_tier: %s", unknown)

    no_rank = con.execute(
        "SELECT count(*) FROM fact_player_snapshot WHERE rank_key IS NULL"
    ).fetchone()[0]
    log.info("Integrity OK: %d staged rows = %d fact rows (%d without rank)",
             staged, counts["fact_player_snapshot"], no_rank)


def run() -> dict[str, int]:
    """Rebuild the warehouse file inside one transaction."""
    snapshots_path = settings.CURATED_DIR / "player_snapshots.parquet"
    if not snapshots_path.exists():
        raise FileNotFoundError(f"Run the integration step first: {snapshots_path}")

    settings.WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(settings.WAREHOUSE_PATH))
    try:
        # One transaction: if anything fails, the previous warehouse is kept
        # unchanged instead of being left half-rebuilt.
        con.begin()
        counts = build(con, snapshots_path)
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

    for table, n in counts.items():
        log.info("Loaded %-22s %9d rows", table, n)
    log.info("Warehouse saved: %s", settings.WAREHOUSE_PATH.relative_to(settings.ROOT))
    return counts


if __name__ == "__main__":
    run()
