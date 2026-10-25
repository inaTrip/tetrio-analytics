"""Fetch a few leaderboard pages and check the overlap with the 2023 data."""
import json
import time
import pandas as pd
import requests

HEADERS = {"User-Agent": "tetrio-analytics-usj (student project)"}
URL = "https://ch.tetr.io/api/users/by/league"
PAGES = 5

users, after = [], None
for page in range(PAGES):
    params = {"limit": 100}
    if after:
        params["after"] = after
    r = requests.get(URL, headers=HEADERS, params=params, timeout=10)
    body = r.json()
    if page == 0:
        print("Status:", r.status_code)
        print("Cache info:", body.get("cache"))
        print("First entry:", json.dumps(body["data"]["entries"][0], indent=2)[:1500])
    entries = body["data"]["entries"]
    users.extend(entries)
    after = entries[-1].get("p", {})
    after = f'{after.get("pri")}:{after.get("sec")}:{after.get("ter")}' if after else None
    time.sleep(1)

live_ids = {u["_id"] for u in users}
tl = pd.read_csv("data/raw/tl_data/tl-data-09-2023.csv")
overlap = live_ids & set(tl["id"])
print(f"\nLive players fetched: {len(live_ids)}")
print(f"Also in 2023 data:    {len(overlap)} ({len(overlap)/len(live_ids):.0%})")
