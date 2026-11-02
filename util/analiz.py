import json
from pathlib import Path

import requests


URL = "https://zordoc.uz/api/mis/g2g/analysis/by-category?per_page=1000&clinic_id=3470"
JSON_FILE = Path(__file__).resolve().parent / "analiz.json"

headers = {
    "Device-Id": "4575853d-d610-4aea-ae71-8bbc3daf0e1b",
    "access_token": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczovL3pvcmRvYy51eiIsImlhdCI6MTc5MDc2MjE1NSwiZXhwIjoxODIyMjk4MTU1LCJuYmYiOjE3OTA3NjIxNTUsImp0aSI6ImZ3U2pyTHJ0cTVodHdOQVciLCJzdWIiOiI0MTU3MDk2MSIsInBydiI6IjkzOWY1N2JjYzViMjViZjhlNWI0NDIzYWJjN2M3MmI0Y2ZhOWM5NmEiLCJuYW1lIjoiSEFaUkFUT1YgWFVSU0hJRCBVTFVH4oCYQkVLIE_igJhH4oCYTEkiLCJlbWFpbCI6bnVsbCwicm9sZSI6ImRpcmVjdG9yIn0.P6W5NPBDUpA6nL8fE1qqiizwM41SvM40EAcyYoddtSk",
    "lang": "uz",
    "Authorization": "Bearer Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczovL3pvcmRvYy51eiIsImlhdCI6MTc5MDc2MjE1NSwiZXhwIjoxODIyMjk4MTU1LCJuYmYiOjE3OTA3NjIxNTUsImp0aSI6ImZ3U2pyTHJ0cTVodHdOQVciLCJzdWIiOiI0MTU3MDk2MSIsInBydiI6IjkzOWY1N2JjYzViMjViZjhlNWI0NDIzYWJjN2M3MmI0Y2ZhOWM5NmEiLCJuYW1lIjoiSEFaUkFUT1YgWFVSU0hJRCBVTFVH4oCYQkVLIE_igJhH4oCYTEkiLCJlbWFpbCI6bnVsbCwicm9sZSI6ImRpcmVjdG9yIn0.P6W5NPBDUpA6nL8fE1qqiizwM41SvM40EAcyYoddtSk",
}

response = requests.get(URL, headers=headers, timeout=60)
response.raise_for_status()
payload = response.json()

services = []
seen = set()
for category in payload.get("data") or []:
    for service in category.get("services") or []:
        service_id = service.get("id")
        if service_id in seen:
            continue
        seen.add(service_id)
        services.append({
            "id": service_id,
            "title": service.get("title") or "",
        })

with JSON_FILE.open("w", encoding="utf-8") as f:
    json.dump(services, f, ensure_ascii=False, indent=2)

print(f"{len(services)} ta service saqlandi: {JSON_FILE.name}")
