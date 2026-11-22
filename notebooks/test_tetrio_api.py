"""One test call to the TETR.IO API to check access, fields and limits."""
import json
import requests

HEADERS = {"User-Agent": "tetrio-analytics-usj (student project)"}
URL = "https://ch.tetr.io/api/users/osk"

r = requests.get(URL, headers=HEADERS, timeout=10)
print("Status:", r.status_code)
print(json.dumps(r.json(), indent=2)[:2000])
