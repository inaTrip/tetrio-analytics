# AI Usage Disclosure

Required by Section 8 of the project kickoff document: which parts of the project were generated or assisted by AI, the model, the prompts, and what was modified afterwards.

This document covers how AI was used **to build the project**. It is separate from the AI applicability reflection, which discusses how AI could help inside the pipeline itself.

**How to keep it up to date:** every team member adds a row for each significant AI-generated fragment (a function, class, pipeline step, configuration file or document) in the same pull request as the fragment itself.

## Tool

| Member | Tool and model | Access |
|---|---|---|
| Hermes Benito Andrés | Claude (Anthropic), model Claude Opus 5.5 | Claude desktop application |
| Eduardo Lázaro Esperón | ||
| Mariano Latre López | ||

## Record

| Date | Member | What was generated (files / components) | Prompt(s) used | Modifications after generation |
|---|---|---|---|---|
| 25/10/2026 | Hermes | **Dataset search:** candidate data sources for the Tetris theme, their role in the warehouse, join keys and risks (the AI ran web searches) | "Can it be of tetris?", "Can you propose datasets of kaggle?", "I want to do the tetris part." | Theme chosen by the team; licences and API usage rules read and summarised by the team |
| 25/10/2026 | Hermes | **Repository structure:** folder layout, `.gitignore`, `.env.example`, `requirements.txt`, first `README.md` | "We have to create the repository, what should be in it?", "ok i will create the skeleton of the repository" | Team, roles and dataset list in the README edited by the team |
| 25/10/2026 | Hermes | **Dataset validation scripts:** `notebooks/profile_datasets.py`, `notebooks/test_tetrio_api.py` (also `check_rank_join.py` and `test_leaderboard.py`, run during validation) and the interpretation of their outputs | "Ok how do I know if the datasets are good?", "What do I do if I have my token copied?" | Scripts run by the team on real data; the decision to discard the replays dataset was taken by the team |
| 25/10/2026 | Hermes | **Checkpoint 1 status update:** `docs/checkpoints/checkpoint1_status_update.tex` (structure, tables, diagram, wording) | "Can you make me a latex template for the first checkpoint?" | Team composition, roles, licences and API usage rules written by the team |
| 22/11/2026 | Hermes | **Ingestion, processing, quality and integration:** `src/settings.py`, `src/pipeline.py`, `src/ingestion/tetrio_api.py`, `src/ingestion/kaggle_loader.py`, `src/transformation/transform.py`, `src/transformation/integrate.py`, `src/quality/checks.py`, `src/monitoring/logger.py`, `tests/test_transform.py`, `pytest.ini` | "OK, then guide me to do step 3" | No changes to the code; run on real data by the team. `.env` / `.env.example` User-Agent and Kaggle variable fixed with AI-provided commands |
| 22/11/2026 | Hermes | **Data warehouse:** `warehouse/schema.sql`, `warehouse/load.sql`, `warehouse/queries.sql`, `src/load/warehouse.py`, `tests/test_warehouse.py`, `notebooks/explore_warehouse.py` | "Lets go with step 4 and then we can do all the small fixes in the document and .md" | A grouping error in query Q1 became visible when the team ran it on real data; fixed with an AI-provided command |
| 22/11/2026 | Hermes | **Scheduling:** `orchestration/crontab.txt` | "Ok, lets set the cron job. Is this needed for checkpoint 2?" | Schedule time chosen and tested on the team member's machine |
| 22/11/2026 | Hermes | **Orchestration plan:** `docs/orchestration.md`; text of GitHub issues #1 and #2 (tasks for the architecture and monitoring documents) | "Okay, what is the best option for the orchestration plan? "| None |
| 22/11/2026 | Hermes | **Checkpoint 2 status update** (sections not marked as team work), **this disclosure file** and the updated **`README.md`** | "Ok, the issues are created. What should be the next steps?" | Sections 2, 3 and 8 (alerting) of the status update to be written by the team (issues #1 and #2) |
| 23/11/2026 | Hermes | **Daily sanity check:** `notebooks/check_daily.py` | "tell me what to check tonight" | None |
| 24/11/2026 | Hermes | **Architecture document:** `docs/architecture.md` (lifecycle mapping, architecture diagram, cluster design, warehouse choice, environmental impact) | "guide me thriugh the steps" | None |

## Responsibility

All AI output was reviewed and run by the team. The team is responsible for the final content and can explain and defend every part of it.
