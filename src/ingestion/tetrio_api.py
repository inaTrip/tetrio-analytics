"""Ingestion of dataset D1: the TETR.IO Tetra League leaderboard.

Fetches the complete leaderboard page by page and saves it as one raw JSON
file per day: data/raw/tetrio/leaderboard_YYYY-MM-DD.json

API usage rules respected: identifying User-Agent, one X-Session-ID for this
series of related requests, about one request per second, retries with
waiting time when the API is busy (HTTP 429) or failing (HTTP 5xx).
"""
import json
import time
import uuid
from datetime import date, datetime, timezone

import requests

from src import settings
from src.monitoring.logger import get_logger

log = get_logger("ingestion.tetrio")

# Data minimisation (privacy): only these fields are stored. Anything else
# the API may return (e.g. linked social accounts, bio) is never written.
KEEP_FIELDS = ("_id", "username", "country", "league")


def _wait_seconds(response: requests.Response | None, attempt: int) -> int:
    """Use the server's Retry-After header if present, else exponential backoff."""
    if response is not None:
        try:
            return int(response.headers["Retry-After"])
        except (KeyError, ValueError):
            pass
    return 2 ** attempt          # 2, 4, 8, 16, 32 seconds


def _get_page(session: requests.Session, after: str | None) -> list[dict]:
    """Download one leaderboard page, retrying on temporary errors."""
    url = f"{settings.TETRIO_BASE_URL}/users/by/league"
    params = {"limit": settings.PAGE_LIMIT}
    if after:
        params["after"] = after

    for attempt in range(1, settings.MAX_RETRIES + 1):
        response = None
        try:
            response = session.get(url, params=params, timeout=15)
        except requests.RequestException as exc:      # network problem
            wait = _wait_seconds(None, attempt)
            log.warning("Network error (%s), retry %d/%d in %d s",
                        exc, attempt, settings.MAX_RETRIES, wait)
            time.sleep(wait)
            continue

        if response.status_code == 429 or response.status_code >= 500:
            wait = _wait_seconds(response, attempt)
            log.warning("HTTP %d, retry %d/%d in %d s",
                        response.status_code, attempt, settings.MAX_RETRIES, wait)
            time.sleep(wait)
            continue

        response.raise_for_status()      # other 4xx: a bug on our side, fail now
        body = response.json()
        if not body.get("success"):
            raise RuntimeError(f"API returned success=false: {body.get('error')}")
        return body["data"]["entries"]

    raise RuntimeError(f"Giving up on page after {settings.MAX_RETRIES} retries")


def _next_cursor(entry: dict) -> str | None:
    """Build the 'after' cursor (pri:sec:ter) from the last entry of a page."""
    p = entry.get("p")
    if not p:
        return None
    return f'{p["pri"]}:{p["sec"]}:{p["ter"]}'


def fetch_leaderboard() -> list[dict]:
    """Fetch the complete leaderboard and return the minimised player records."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": settings.TETRIO_USER_AGENT,
        "X-Session-ID": str(uuid.uuid4()),   # one ID for this run only
    })

    players: list[dict] = []
    after = None
    started = time.monotonic()

    for page in range(1, settings.MAX_PAGES + 1):
        entries = _get_page(session, after)
        players.extend({k: e.get(k) for k in KEEP_FIELDS} for e in entries)

        if page % 50 == 0:
            log.info("Progress: %d pages, %d players", page, len(players))

        if len(entries) < settings.PAGE_LIMIT:    # short page = last page
            break
        after = _next_cursor(entries[-1])
        if after is None:
            log.warning("No pagination cursor on page %d, stopping early", page)
            break
        time.sleep(settings.REQUEST_DELAY_S)      # respect the rate limit
    else:
        log.warning("Stopped at MAX_PAGES=%d: leaderboard may be incomplete",
                    settings.MAX_PAGES)

    log.info("Fetched %d players in %d pages (%.0f s)",
             len(players), page, time.monotonic() - started)
    return players


def save_raw(players: list[dict], snapshot_date: date | None = None):
    """Write the players to the raw layer as one JSON file for the day."""
    snapshot_date = snapshot_date or datetime.now(timezone.utc).date()
    settings.RAW_API_DIR.mkdir(parents=True, exist_ok=True)
    path = settings.RAW_API_DIR / f"leaderboard_{snapshot_date.isoformat()}.json"

    payload = {
        "snapshot_date": snapshot_date.isoformat(),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "n_players": len(players),
        "players": players,
    }
    # Write to a temporary file first, then rename: if the run crashes while
    # writing, yesterday's valid file is never replaced by a half-written one.
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    tmp.replace(path)
    log.info("Saved raw snapshot: %s", path.relative_to(settings.ROOT))
    return path


def run():
    """Ingestion entry point used by the pipeline."""
    players = fetch_leaderboard()
    if not players:
        raise RuntimeError("Leaderboard fetch returned 0 players")
    return save_raw(players)


if __name__ == "__main__":
    run()
