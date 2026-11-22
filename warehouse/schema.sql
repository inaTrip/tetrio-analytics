-- =====================================================================
-- Star schema of the TETR.IO data warehouse (DuckDB SQL dialect)
--
-- Fact grain: one player on one snapshot date.
-- Dimensions: player (SCD type 2), date, rank tier.
--
-- The warehouse is rebuilt from the curated layer on every run (full
-- refresh), so this file drops and recreates every table. The fact table
-- is dropped first because it references the dimensions (foreign keys).
-- =====================================================================

DROP TABLE IF EXISTS fact_player_snapshot;
DROP TABLE IF EXISTS dim_player;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_rank_tier;

-- ---------------------------------------------------------------------
-- dim_date: one row per calendar day, so time-based queries and
-- dashboards can group by year, month or weekday without date maths.
-- ---------------------------------------------------------------------
CREATE TABLE dim_date (
    date_key     INTEGER  PRIMARY KEY,   -- YYYYMMDD, e.g. 20261122
    full_date    DATE     NOT NULL UNIQUE,
    year         SMALLINT NOT NULL,
    quarter      TINYINT  NOT NULL,
    month        TINYINT  NOT NULL,
    day          TINYINT  NOT NULL,
    day_of_week  TINYINT  NOT NULL,      -- ISO: 1 = Monday ... 7 = Sunday
    is_weekend   BOOLEAN  NOT NULL
);

-- ---------------------------------------------------------------------
-- dim_rank_tier: the TETR.IO rank ladder with an explicit order, so
-- ranks can be sorted and compared ("d" < "c" < ... < "x+").
-- Codes are taken from the source, never derived from TR thresholds.
-- ---------------------------------------------------------------------
CREATE TABLE dim_rank_tier (
    rank_key    INTEGER PRIMARY KEY,
    rank_code   VARCHAR NOT NULL UNIQUE, -- as given by TETR.IO
    rank_order  INTEGER,                 -- 0 = unranked, 1 = lowest; NULL = unknown code
    rank_group  VARCHAR                  -- letter family: D, C, B, A, S, SS, U, X
);

-- ---------------------------------------------------------------------
-- dim_player: slowly changing dimension, type 2.
-- A new version (new player_key) is created whenever the username or
-- the country changes, so history is kept instead of overwritten.
-- ---------------------------------------------------------------------
CREATE TABLE dim_player (
    player_key  INTEGER PRIMARY KEY,     -- surrogate key, one per version
    player_id   VARCHAR NOT NULL,        -- natural key (TETR.IO user ID)
    username    VARCHAR,
    country     VARCHAR,
    valid_from  DATE    NOT NULL,
    valid_to    DATE    NOT NULL,        -- 9999-12-31 for the current version
    is_current  BOOLEAN NOT NULL
);

-- ---------------------------------------------------------------------
-- fact_player_snapshot: the measures of one player on one date.
-- ---------------------------------------------------------------------
CREATE TABLE fact_player_snapshot (
    player_key     INTEGER NOT NULL REFERENCES dim_player (player_key),
    date_key       INTEGER NOT NULL REFERENCES dim_date (date_key),
    rank_key       INTEGER REFERENCES dim_rank_tier (rank_key),
    best_rank_key  INTEGER REFERENCES dim_rank_tier (rank_key),
    source         VARCHAR NOT NULL,     -- degenerate dimension: kaggle_2023 / tetrio_api
    tr             DOUBLE,               -- TETRA Rating (0 - 25,000)
    glicko         DOUBLE,
    rd             DOUBLE,               -- rating deviation (uncertainty)
    gxe            DOUBLE,               -- not available in 2023 (NULL)
    apm            DOUBLE,               -- attack per minute
    pps            DOUBLE,               -- pieces per second
    vs             DOUBLE,               -- versus score
    games_played   INTEGER,
    games_won      INTEGER,
    is_decaying    BOOLEAN,              -- not available in 2023 (NULL)
    PRIMARY KEY (player_key, date_key)
);
