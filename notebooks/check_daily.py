"""Daily sanity check: rows per snapshot and day-over-day consistency."""
import duckdb

from src import settings

con = duckdb.connect(str(settings.WAREHOUSE_PATH), read_only=True)

print("Rows per snapshot:")
print(con.sql("""
    SELECT d.full_date, f.source, count(*) AS players, round(avg(f.tr)) AS avg_tr
    FROM fact_player_snapshot f JOIN dim_date d USING (date_key)
    GROUP BY ALL ORDER BY d.full_date
"""))

print("Last two API days compared:")
print(con.sql("""
    WITH days AS (
        SELECT DISTINCT d.full_date FROM fact_player_snapshot f
        JOIN dim_date d USING (date_key) WHERE f.source = 'tetrio_api'
        ORDER BY d.full_date DESC LIMIT 2
    ), snap AS (
        SELECT p.player_id, d.full_date, f.tr
        FROM fact_player_snapshot f
        JOIN dim_player p USING (player_key)
        JOIN dim_date d USING (date_key)
        WHERE d.full_date IN (SELECT full_date FROM days)
    )
    SELECT count(*)                                   AS players_both_days,
           count(*) FILTER (WHERE a.tr <> b.tr)       AS players_tr_changed,
           round(max(abs(a.tr - b.tr)))               AS max_tr_change
    FROM snap a JOIN snap b
      ON a.player_id = b.player_id AND a.full_date < b.full_date
"""))
con.close()
