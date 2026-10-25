# TETR.IO Player Progression Analytics

Data Engineering (34623) – Universidad San Jorge – Semester Project

## Overview
Daily data pipeline that snapshots the TETR.IO Tetra League leaderboard,
integrates it with historical player data and replays, and loads the result
into a data warehouse to analyse player progression.

## Team
| Member | Role |
|---|---|
| Everyone | Ingestion & Storage Lead |
| Name | Platform & Cloud Lead |
| Hermes Benito | Orchestration & Quality Lead |
| Name | Delivery & Presentation Lead |

## Datasets
1. TETR.IO public API – daily snapshot
2. Kaggle – TETR.IO Player data
3. Kaggle – Tetr.io Top Players Replays (Considered, but removed)

## Setup
pip install -r requirements.txt
cp .env.example .env   # then fill in your keys

## Run
python -m src.pipeline

## Documentation
See the `docs/` folder.
