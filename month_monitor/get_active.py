import json
from collections import defaultdict

import psycopg2
import requests


URL = "https://zordoc.uz/api/mis/v2/appointments"

HEADERS = {
    "Device-Id": "4575853d-d610-4aea-ae71-8bbc3daf0e1b",
    "access_token": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczovL3pvcmRvYy51eiIsImlhdCI6MTc5MDc2MjE1NSwiZXhwIjoxODIyMjk4MTU1LCJuYmYiOjE3OTA3NjIxNTUsImp0aSI6ImZ3U2pyTHJ0cTVodHdOQVciLCJzdWIiOiI0MTU3MDk2MSIsInBydiI6IjkzOWY1N2JjYzViMjViZjhlNWI0NDIzYWJjN2M3MmI0Y2ZhOWM5NmEiLCJuYW1lIjoiSEFaUkFUT1YgWFVSU0hJRCBVTFVH4oCYQkVLIE_igJhH4oCYTEkiLCJlbWFpbCI6bnVsbCwicm9sZSI6ImRpcmVjdG9yIn0.P6W5NPBDUpA6nL8fE1qqiizwM41SvM40EAcyYoddtSk",
    "service_access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzUxMiJ9.eyJpYXQiOjE3OTA3NjIxNTUuMzI2MDEsImlzcyI6Imh0dHBzOi8vem9yZG9jLnV6IiwiZXhwIjoxNzkwODQ4NTU1LjMyNjAxLCJwaW5mbCI6IjMxOTAxOTc1MjgwMDY5IiwibmFtZSI6IlhVUlNISUQiLCJ1dWlkIjoiZTBhMjczNTktYjZlZS00ZDEyLWEyMmEtNjRjN2NiYjhkOTkxIiwic3VybmFtZSI6IkhBWlJBVE9WIiwicGF0cm9ueW1pYyI6IlVMVUfigJhCRUsgT-KAmEfigJhMSSIsInJvbGVzIjpbImRpcmVjdG9yIl0sInNwZWNpYWx0aWVzIjpbXSwiY2xpbmljX3V1aWQiOiJiYzAyMmEyYi0wMDQwLTRlYmQtYjYyYy0zMWQxZTZmYjA0MzkiLCJjbGluaWNfdGl0bGUiOiJCdXhvcm8gdmlsb3lhdCBrbydwIHRhcm1vcWxpIHRpYmJpeW90IG1hcmthemkiLCJwb3NpdGlvbnMiOlsiY29tbWlzc2lvbl9",
    "Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczovL3pvcmRvYy51eiIsImlhdCI6MTc5MDc2MjE1NSwiZXhwIjoxODIyMjk4MTU1LCJuYmYiOjE3OTA3NjIxNTUsImp0aSI6ImZ3U2pyTHJ0cTVodHdOQVciLCJzdWIiOiI0MTU3MDk2MSIsInBydiI6IjkzOWY1N2JjYzViMjViZjhlNWI0NDIzYWJjN2M3MmI0Y2ZhOWM5NmEiLCJuYW1lIjoiSEFaUkFUT1YgWFVSU0hJRCBVTFVH4oCYQkVLIE_igJhH4oCYTEkiLCJlbWFpbCI6bnVsbCwicm9sZSI6ImRpcmVjdG9yIn0.P6W5NPBDUpA6nL8fE1qqiizwM41SvM40EAcyYoddtSk",
}

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monitoring",
    "user": "postgres",
    "password": "1",
}

START_DATE = "2026-09-01"
END_DATE = "2026-09-30"
PER_PAGE = 100


def patient_name(patient):
    parts = [
        patient.get("name") or "",
        patient.get("surname") or "",
        patient.get("patronymic") or "",
    ]
    return " ".join(part.strip() for part in parts if part.strip())


def polyclinic_doctors():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, full_name, dmed_id
        FROM doctors
        WHERE polyclinic IS TRUE
          AND dmed_id IS NOT NULL
          AND dmed_id <> ''
        ORDER BY id
        """
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def appointments(dmed_id):
    page = 1
    items = []

    while True:
        response = requests.get(
            URL,
            headers=HEADERS,
            params={
                "excluded_statuses[0]": "canceled",
                "excluded_statuses[1]": "provided",
                "doctors[0]": dmed_id,
                "start_at": START_DATE,
                "end_at": END_DATE,
                "page": page,
                "per_page": PER_PAGE,
            },
            timeout=30,
        )

        if response.status_code == 404:
            print(f"404, keyingi shifokor: {dmed_id}", flush=True)
            return None

        if response.status_code != 200:
            raise RuntimeError(
                f"doctor {dmed_id} status {response.status_code}: {response.text[:300]}"
            )

        result = response.json()
        items.extend(result.get("data") or [])

        if not (result.get("meta") or {}).get("has_more_pages", False):
            break

        page += 1

    return items


def by_day(items, dmed_id):
    grouped = defaultdict(list)

    for item in items:
        doctor = item.get("doctor") or {}
        if str(doctor.get("id") or "") != str(dmed_id):
            continue

        day = str(item.get("start_at") or "")[:10]
        if not day or day < START_DATE or day > END_DATE:
            continue

        patient = item.get("patient") or {}
        grouped[day].append({
            "kasal nomi": patient_name(patient),
            "uuid": patient.get("uuid") or "",
        })

    return grouped


def main():
    results = []

    for _, full_name, dmed_id in polyclinic_doctors():
        if str(dmed_id).strip().lower() in {"none", "null"}:
            print(f"dmed_id yo'q, keyingi shifokor: {full_name}", flush=True)
            continue

        items = appointments(dmed_id)
        if items is None:
            continue

        total = sum(len(patients) for patients in by_day(items, dmed_id).values())
        if not total:
            continue

        results.append({
            "doctor": full_name,
            "qabullar": total,
        })

    print(json.dumps(results, ensure_ascii=False, indent=4))


if __name__ == "__main__":
    main()
