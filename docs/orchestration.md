# Orchestration Plan

How the TETR.IO pipeline is scheduled to run every day: what runs today, what it will be replaced by, and why.

## 1. Why the pipeline must run daily

The TETR.IO API only exposes the **current** state of the leaderboard and keeps no daily history. A snapshot that is not taken on a given day **can never be recovered later**: there is no backfill. The progression analysis (TR, rank and playstyle over time) depends entirely on the pipeline running every day.

## 2. What one run does

A run is a single command, `python -m src.pipeline`, which executes the stages in a fixed order. Each stage only starts if the previous one succeeded.

| Order | Stage | Module | Output | Typical duration |
|---|---|---|---|---|
| 1 | Ingestion D2 (one-off) | `src/ingestion/kaggle_loader.py` | `data/raw/tl_data/` (skipped if present) | < 1 s |
| 2 | Ingestion D1 (daily) | `src/ingestion/tetrio_api.py` | `data/raw/tetrio/leaderboard_YYYY-MM-DD.json` | ~7 min (361 pages at 1 request/s) |
| 3 | Processing + quality + integration | `src/transformation/`, `src/quality/` | `data/curated/*.parquet` | ~1 s |
| 4 | Load | `src/load/warehouse.py` | `data/warehouse/tetrio.duckdb` | ~1 s |

Figures measured on the first full run (22 Nov 2026): 36,094 players, 361 pages, 420 s in total.

**Properties that make it safe to schedule:**

- **Idempotent:** the curated layer and the warehouse are rebuilt from all raw files, and the daily raw file is overwritten if the run is repeated on the same day. Running twice never creates duplicates.
- **Atomic writes:** the raw JSON is written to a temporary file and then renamed; the warehouse is rebuilt inside one transaction. A failed run leaves the previous valid state untouched.
- **Clear exit status:** the pipeline returns exit code `0` on success and `1` on failure, which any scheduler can use to detect failures.
- **Self-throttled:** the API rate limit (about 1 request/s) and retries on HTTP 429/5xx are handled inside the ingestion code, not by the scheduler.

## 3. Current solution: cron on a local machine (interim)

Configuration: [`orchestration/crontab.txt`](../orchestration/crontab.txt)

```cron
7 21 * * * cd <repo> && PATH=<repo>/.venv/bin:/usr/bin:/bin ./.venv/bin/python -m src.pipeline >> logs/cron.log 2>&1
```

- Runs every day at 21:07 (Europe/Madrid). Minute 7 avoids the moment when many scheduled jobs start at once.
- Output and early errors go to `logs/cron.log`; the pipeline's own log goes to `logs/pipeline.log`.
- Tested with an empty environment (`env -i`) to reproduce cron's minimal environment.

**Why this first:** it took minutes to set up and started collecting daily snapshots immediately, which matters because missed days cannot be recovered (Section 1).

**Limitations:** it only runs while the machine is on and awake; it depends on one personal computer; there is no built-in alerting on failure.

## 4. Options compared

| Criterion | cron (local) | GitHub Actions (scheduled workflow) | Apache Airflow | Cloud Scheduler + Cloud Run job (GCP) |
|---|---|---|---|---|
| Cost | Free | Free within the plan's included minutes (~7 min/day ≈ 210 min/month) | Server or managed service cost | Small; pay per execution |
| Reliability | Low: needs the machine on | High: runs on GitHub's servers | High, if operated well | High |
| Operational burden | Very low | Low: one YAML file in the repo | High: scheduler, workers, metadata DB | Medium: IAM, container image |
| Dependency handling | None (one command) | Steps within a job | Full DAGs, retries per task | None (one job) |
| Failure notification | None | Built-in e-mail on failure | Built-in | Via Cloud Monitoring |
| Lock-in | None | GitHub | None (open source) | GCP |
| Environmental footprint | Machine must be awake at run time | Runner exists only during the run | Always-on scheduler and workers | Scales to zero between runs |
| Fit for this project | Interim | **Target** | Overkill for one daily job | Good alternative if fully on GCP |

Service names, free quotas and limits may have changed; check the providers' current documentation before relying on them.

## 5. Target solution: GitHub Actions + cloud storage

A scheduled GitHub Actions workflow will run the same command every day on GitHub's servers, independently of any personal computer.

**Key design constraint:** the GitHub Actions runner is **temporary**: its disk is deleted when the job ends. The pipeline must therefore read its previous state from, and write its results to, **persistent cloud storage** (planned: Google Cloud Storage for the raw and curated layers, BigQuery as the cloud warehouse), instead of the local `data/` folder.

**Planned workflow** (not active yet; it will live in `.github/workflows/daily_pipeline.yml`):

```yaml
name: Daily pipeline

on:
  schedule:
    - cron: "7 20 * * *"      # 20:07 UTC = 21:07 Madrid (winter time)
  workflow_dispatch:           # also allows a manual run from the GitHub UI

jobs:
  run-pipeline:
    runs-on: ubuntu-latest
    timeout-minutes: 30        # a normal run takes ~7 min
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: pytest            # do not run the pipeline if the code is broken
      - run: python -m src.pipeline
        env:
          KAGGLE_API_TOKEN: ${{ secrets.KAGGLE_API_TOKEN }}
          TETRIO_USER_AGENT: ${{ vars.TETRIO_USER_AGENT }}
          GOOGLE_APPLICATION_CREDENTIALS_JSON: ${{ secrets.GCP_SA_KEY }}
```

Notes:

- GitHub cron schedules are written in **UTC**: the hour must be adjusted when Spain changes between winter and summer time.
- Secrets (Kaggle token, GCP service-account key) are stored as **GitHub Secrets**, never in the repository.
- Scheduled workflows can start several minutes late when GitHub is busy; this does not matter for one daily snapshot.

**Migration steps:**

1. Create the GCP project, a Cloud Storage bucket and a BigQuery dataset; create a service account with minimum permissions.
2. Change the storage functions (`src/settings.py`, `save_raw`, the curated writers and the warehouse loader) to read from and write to cloud storage.
3. Add the secrets to the GitHub repository.
4. Add the workflow file and trigger it once manually (`workflow_dispatch`).
5. After a few successful daily runs, remove the cron job.

## 6. Failure handling and monitoring hooks

- Any exception stops the run and is logged with its full traceback (`log.exception` in `src/pipeline.py`); the process exits with code `1`.
- Temporary API errors (HTTP 429/5xx, network errors) are retried up to 5 times with increasing waits before the run fails.
- The alerting design (which conditions notify the team, and through which channel) is described in the logging and alerting design document; `src/pipeline.py` already contains the hook where alerts will be sent.

## 7. Environmental impact

One run per day uses about 7 minutes of compute, most of it waiting between API requests rather than processing. The target solution uses compute only while the job runs (no always-on server), and the daily batch is the lowest frequency that still captures every daily snapshot. Running more often would multiply API calls and energy use without adding information, because the analysis is based on daily progression.
