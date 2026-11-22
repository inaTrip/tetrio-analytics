-- =====================================================================
-- Load the star schema from the staging view "stg_snapshots"
-- (= data/curated/player_snapshots.parquet, created by the Python loader).
-- Dimensions are loaded first, because the fact table references them.
-- =====================================================================

-- 1. dim_date: every day between the first and the last snapshot.
INSERT INTO dim_date
SELECT
    CAST(strftime(d, '%Y%m%d') AS INTEGER) AS date_key,
    d                                      AS full_date,
    year(d), quarter(d), month(d), day(d),
    isodow(d)                              AS day_of_week,
    isodow(d) >= 6                         AS is_weekend
FROM (
    SELECT CAST(unnest(generate_series(
               MIN(snapshot_date), MAX(snapshot_date), INTERVAL 1 DAY)) AS DATE) AS d
    FROM stg_snapshots
);

-- 2. dim_rank_tier: the known ladder plus any new code found in the data
--    (so a rank introduced by TETR.IO in the future does not break the load).
INSERT INTO dim_rank_tier
WITH known (rank_code, rank_order, rank_group) AS (
    VALUES ('z', 0, 'Unranked'),
           ('d', 1, 'D'),  ('d+', 2, 'D'),
           ('c-', 3, 'C'), ('c', 4, 'C'),  ('c+', 5, 'C'),
           ('b-', 6, 'B'), ('b', 7, 'B'),  ('b+', 8, 'B'),
           ('a-', 9, 'A'), ('a', 10, 'A'), ('a+', 11, 'A'),
           ('s-', 12, 'S'), ('s', 13, 'S'), ('s+', 14, 'S'),
           ('ss', 15, 'SS'), ('u', 16, 'U'), ('x', 17, 'X'), ('x+', 18, 'X')
),
seen AS (
    SELECT rank AS rank_code FROM stg_snapshots WHERE rank IS NOT NULL
    UNION
    SELECT bestrank FROM stg_snapshots WHERE bestrank IS NOT NULL
),
all_codes AS (
    SELECT rank_code FROM known
    UNION
    SELECT rank_code FROM seen
)
SELECT
    row_number() OVER (ORDER BY k.rank_order NULLS LAST, a.rank_code) AS rank_key,
    a.rank_code, k.rank_order, k.rank_group
FROM all_codes AS a
LEFT JOIN known AS k USING (rank_code);

-- 3. dim_player (SCD type 2).
--    a) order each player's snapshots by date and look at the previous one;
--    b) keep the rows where a version starts: first appearance, or a change
--       in a tracked attribute (username, country);
--    c) a version ends the day before the next version starts.
INSERT INTO dim_player
WITH ordered AS (
    SELECT
        player_id, username, country,
        CAST(snapshot_date AS DATE) AS snapshot_date,
        lag(username) OVER w        AS prev_username,
        lag(country)  OVER w        AS prev_country,
        row_number()  OVER w        AS rn
    FROM stg_snapshots
    WINDOW w AS (PARTITION BY player_id ORDER BY snapshot_date)
),
version_starts AS (
    SELECT player_id, username, country, snapshot_date AS valid_from
    FROM ordered
    WHERE rn = 1
       OR username IS DISTINCT FROM prev_username   -- NULL-safe comparison
       OR country  IS DISTINCT FROM prev_country
),
versions AS (
    SELECT *,
           lead(valid_from) OVER (PARTITION BY player_id ORDER BY valid_from) AS next_from
    FROM version_starts
)
SELECT
    row_number() OVER (ORDER BY player_id, valid_from) AS player_key,
    player_id, username, country, valid_from,
    COALESCE(next_from - 1, DATE '9999-12-31')         AS valid_to,
    next_from IS NULL                                  AS is_current
FROM versions;

-- 4. fact_player_snapshot.
--    Point-in-time join: each snapshot is linked to the player version
--    that was valid on that date, not simply to the current version.
INSERT INTO fact_player_snapshot
SELECT
    p.player_key,
    CAST(strftime(s.snapshot_date, '%Y%m%d') AS INTEGER) AS date_key,
    r.rank_key,
    br.rank_key AS best_rank_key,
    s.source,
    s.tr, s.glicko, s.rd, s.gxe, s.apm, s.pps, s.vs,
    s.gamesplayed, s.gameswon, s.decaying
FROM stg_snapshots AS s
JOIN dim_player AS p
  ON p.player_id = s.player_id
 AND CAST(s.snapshot_date AS DATE) BETWEEN p.valid_from AND p.valid_to
LEFT JOIN dim_rank_tier AS r  ON r.rank_code  = s.rank
LEFT JOIN dim_rank_tier AS br ON br.rank_code = s.bestrank;
