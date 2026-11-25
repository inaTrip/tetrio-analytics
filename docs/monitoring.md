# Monitoring: Logging and Alerting Design

How the pipeline records what happens on every run (logging, **implemented**) and how the team will be notified when something goes wrong (alerting, **designed**; implementation planned before the oral presentation).

## 1. Logging (implemented)

### 1.1 How it works

All modules log through one shared logger (`src/monitoring/logger.py`). Every message goes to two places:

| Destination | Content | Written by |
|---|---|---|
| Console | Same as the file, for manual runs | `logging.StreamHandler` |
| `logs/pipeline.log` | Every message of every run, appended | `logging.FileHandler` |
| `logs/cron.log` | Console output of scheduled runs, including errors that happen before Python's logger starts (e.g. Python not found) | cron redirection (`>> logs/cron.log 2>&1`) |

Format: one line per event, `timestamp | level | module | message`, for example:

```
2026-11-23 21:14:26,666 | INFO     | pipeline.quality | [leaderboard_2026-11-23] rows in=35994 | no id=0 | duplicates=0 | invalid TR=0 | rows out=35994
```

The module name (`pipeline.ingestion.tetrio`, `pipeline.quality`, …) shows which stage produced each line, so a problem can be located without reading the code.

### 1.2 What each stage logs

| Stage | Logged events | Level |
|---|---|---|
| Start / end | `Pipeline started`, `Pipeline finished OK in N s` | INFO |
| Ingestion (API) | Progress every 50 pages; total players, pages and duration; saved file | INFO |
| Ingestion (API) | Retries on HTTP 429/5xx or network errors, with the waiting time | WARNING |
| Ingestion (API) | Missing pagination cursor, page cap reached | WARNING |
| Ingestion (Kaggle) | Download or "already present, skipped" | INFO |
| Processing | Number of negative sentinel values converted to null, per column | INFO |
| Quality checks | Rows in, rows rejected per rule (no ID, duplicates, invalid TR), rows out | INFO |
| Integration | Rows in the snapshots table; overlap between 2023 and the latest snapshot | INFO |
| Load | Integrity check (staged rows = fact rows), rows per table; unknown rank codes | INFO / WARNING |
| Any failure | `Pipeline FAILED after N s` with the full traceback | ERROR |

### 1.3 Levels

- **INFO:** normal operation and the key figures of each run.
- **WARNING:** something unusual that the pipeline handled by itself (a retry, an unknown rank code). Worth reading, not urgent.
- **ERROR:** the run stopped. The previous valid data is kept (atomic raw write, transactional load), but today's snapshot is missing.

### 1.4 Retention

Logs are kept for **30 days** (see `docs/architecture.md`). Log rotation is not implemented yet; it is planned with the cloud migration. At the current size (a few KB per run) this is not urgent.

### 1.5 Real example: what the logs already showed

- 22/11, first run: the quality checks removed **2 duplicate players** (players who moved between pages while the leaderboard was being read).
- 22/11 and 23/11, scheduled runs: 36,059 and 35,994 players, ~450 s each, integrity check OK.

## 2. Alerting (design)

Logging records what happened; **alerting tells someone** when action is needed, without anyone reading the logs.

### 2.1 Alert conditions

Thresholds are based on the runs observed so far: the daily player count changed by about **0.2%** between the first two scheduled runs, and a run takes **~450 s**.

| # | Condition | How it is detected | Severity | Threshold |
|---|---|---|---|---|
| A1 | Pipeline failed | Exception caught in `src/pipeline.py` (exit code 1) | **Critical** | Any failure |
| A2 | 0 players ingested | Ingestion raises an error when the fetch returns no players | **Critical** | 0 rows |
| A3 | Player count changed abnormally vs. the previous day | Compare today's and yesterday's snapshot counts after the load | **Critical** if > 20%, **warning** if > 5% | 5% / 20% |
| A4 | Too many rows rejected by quality checks | Rows rejected / rows in, from the quality step | Warning | > 1% |
| A5 | Run much slower than usual | Total duration | Warning | > 900 s (2× normal) |
| A6 | Many API retries | Number of retry warnings in one run | Warning | > 10 |
| A7 | **No snapshot for more than 26 hours** | External check of the newest raw file's date (see 2.2) | **Critical** | 26 h |
| A8 | Integrity check failed (staged rows ≠ fact rows) | Load step raises an error → covered by A1 | Critical | Any |

### 2.2 The "silent failure" problem (A7)

If the scheduler does not run at all (computer off, cron removed, GitHub Actions disabled), the pipeline never starts, so **it cannot send an alert about itself**. A7 therefore needs a check that runs **outside** the pipeline: a *heartbeat* or *dead man's switch*. Options:

- A second, independent scheduled job that only checks the date of the newest snapshot.
- An external monitoring service that expects a "ping" from every successful run and alerts when the ping does not arrive.

With GitHub Actions (planned), a separate small scheduled workflow can do this check.

### 2.3 Severity and response

| Severity | Meaning | Expected response |
|---|---|---|
| Critical | Today's snapshot is missing or wrong; it cannot be recovered later because the API keeps no history | Same day: check `logs/pipeline.log`, fix, re-run |
| Warning | Data was collected but something looks unusual | Within the week: investigate, adjust thresholds if it was a false alarm |

### 2.4 Channel

| Channel | Pros | Cons |
|---|---|---|
| E-mail | Everyone has it; no setup for GitHub Actions failures (built-in) | Easy to miss; mixes with other mail |
| Discord / Slack webhook | Instant, visible to the whole team in one channel; one HTTP POST from Python; free | Needs a team server/workspace; the webhook URL is a secret |
| GitHub Actions failure e-mail | Built in, no code | Only covers A1 (job failure), not data problems |

**Decision:** a **Discord webhook** to a team channel for all alerts (the URL is stored as `ALERT_WEBHOOK_URL` in `.env` and as a GitHub Secret, never committed), **plus** GitHub's built-in failure e-mail as a second layer once the pipeline runs on GitHub Actions.

### 2.5 Avoiding alert fatigue

Too many alerts make people ignore them. Rules:

- **One message per run**, listing every triggered condition, instead of one message per problem or per retry.
- **No message on a normal run.** (Optionally, a weekly summary instead of daily "all OK" messages.)
- **Retries are not alerts:** temporary API errors are handled automatically and only alert (A6) if they become frequent.
- **Thresholds reviewed** after the first weeks of data, using the real day-to-day variation.

### 2.6 Implementation plan

1. Create `src/monitoring/alerts.py` with a function that sends one message to the webhook (`requests.post`), and does nothing if `ALERT_WEBHOOK_URL` is not set (so local runs never fail because of alerting).
2. Call it from the `except` block in `src/pipeline.py` (A1, A2, A8).
3. After a successful run, compute the run's figures (count vs. yesterday, rejection rate, duration, retries) and send one message if any condition is met (A3–A6). The comparison logic already exists in `notebooks/check_daily.py`.
4. Add the heartbeat check (A7) as a separate scheduled job.
5. Test by forcing a failure (e.g. a wrong API URL) and checking that the alert arrives.

Tracked in the issue *Implement alerting* (milestone: Oral presentation).
