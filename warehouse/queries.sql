-- =====================================================================
-- Example analytical queries on the star schema.
-- Run them all with:  python -m notebooks.explore_warehouse
-- =====================================================================

-- Q1. Players per rank group: 2023 baseline vs latest snapshot
SELECT r.rank_group,
       count(*) FILTER (WHERE f.source = 'kaggle_2023') AS players_2023,
       count(*) FILTER (WHERE d.full_date = (SELECT max(full_date) FROM dim_date)) AS players_latest
FROM fact_player_snapshot AS f
JOIN dim_rank_tier AS r ON r.rank_key = f.rank_key
JOIN dim_date      AS d ON d.date_key = f.date_key
GROUP BY r.rank_group
ORDER BY min(r.rank_order);

-- Q2. Top 10 TR improvements between 2023 and the latest snapshot
WITH base AS (
    SELECT p.player_id, f.tr AS tr_2023
    FROM fact_player_snapshot f JOIN dim_player p USING (player_key)
    WHERE f.source = 'kaggle_2023'
), latest AS (
    SELECT p.player_id, p.username, f.tr AS tr_now
    FROM fact_player_snapshot f
    JOIN dim_player p USING (player_key)
    JOIN dim_date d USING (date_key)
    WHERE d.full_date = (SELECT max(full_date) FROM dim_date)
)
SELECT l.username, round(b.tr_2023) AS tr_2023, round(l.tr_now) AS tr_now,
       round(l.tr_now - b.tr_2023) AS tr_change
FROM base b JOIN latest l USING (player_id)
ORDER BY tr_change DESC
LIMIT 10;

-- Q3. Average playstyle per rank in the latest snapshot
SELECT r.rank_code,
       count(*)              AS players,
       round(avg(f.apm), 1)  AS avg_apm,
       round(avg(f.pps), 2)  AS avg_pps,
       round(avg(f.vs), 1)   AS avg_vs
FROM fact_player_snapshot f
JOIN dim_rank_tier r ON r.rank_key = f.rank_key
JOIN dim_date d      ON d.date_key = f.date_key
WHERE d.full_date = (SELECT max(full_date) FROM dim_date)
GROUP BY r.rank_code, r.rank_order
ORDER BY r.rank_order;
