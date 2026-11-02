import json
from collections import defaultdict

import psycopg2
import requests


URL = "https://zordoc.uz/api/mis/v2/hospitalizations"

HEADERS = {
    "Device-Id": "4575853d-d610-4aea-ae71-8bbc3daf0e1b",
    "access_token": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczovL3pvcmRvYy51eiIsImlhdCI6MTc5MDc2MjE1NSwiZXhwIjoxODIyMjk4MTU1LCJuYmYiOjE3OTA3NjIxNTUsImp0aSI6ImZ3U2pyTHJ0cTVodHdOQVciLCJzdWIiOiI0MTU3MDk2MSIsInBydiI6IjkzOWY1N2JjYzViMjViZjhlNWI0NDIzYWJjN2M3MmI0Y2ZhOWM5NmEiLCJuYW1lIjoiSEFaUkFUT1YgWFVSU0hJRCBVTFVH4oCYQkVLIE_igJhH4oCYTEkiLCJlbWFpbCI6bnVsbCwicm9sZSI6ImRpcmVjdG9yIn0.P6W5NPBDUpA6nL8fE1qqiizwM41SvM40EAcyYoddtSk",
    "service_access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzUxMiJ9.eyJpYXQiOjE3OTA3NjIxNTUuMzI2MDEsImlzcyI6Imh0dHBzOi8vem9yZG9jLnV6IiwiZXhwIjoxNzkwODQ4NTU1LjMyNjAxLCJwaW5mbCI6IjMxOTAxOTc1MjgwMDY5IiwibmFtZSI6IlhVUlNISUQiLCJ1dWlkIjoiZTBhMjczNTktYjZlZS00ZDEyLWEyMmEtNjRjN2NiYjhkOTkxIiwic3VybmFtZSI6IkhBWlJBVE9WIiwicGF0cm9ueW1pYyI6IlVMVUfigJhCRUsgT-KAmEfigJhMSSIsInJvbGVzIjpbImRpcmVjdG9yIl0sInNwZWNpYWx0aWVzIjpbXSwiY2xpbmljX3V1aWQiOiJiYzAyMmEyYi0wMDQwLTRlYmQtYjYyYy0zMWQxZTZmYjA0MzkiLCJjbGluaWNfdGl0bGUiOiJCdXhvcm8gdmlsb3lhdCBrbydwIHRhcm1vcWxpIHRpYmJpeW90IG1hcmthemkiLCJwb3NpdGlvbnMiOlsiY29tbWlzc2lvbl9",
    "Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczovL3pvcmRvYy51eiIsImlhdCI6MTc5MDc2MjE1NSwiZXhwIjoxODIyMjk4MTU1LCJuYmYiOjE3OTA3NjIxNTUsImp0aSI6ImZ3U2pyTHJ0cTVodHdOQVciLCJzdWIiOiI0MTU3MDk2MSIsInBydiI6IjkzOWY1N2JjYzViMjViZjhlNWI0NDIzYWJjN2M3MmI0Y2ZhOWM5NmEiLCJuYW1lIjoiSEFaUkFUT1YgWFVSU0hJRCBVTFVH4oCYQkVLIE_igJhH4oCYTEkiLCJlbWFpbCI6bnVsbCwicm9sZSI6ImRpcmVjdG9yIn0.P6W5NPBDUpA6nL8fE1qqiizwM41SvM40EAcyYoddtSk",
}

DOCTOR_ID = "551007"
DEPARTMENT_ID = "3470"
START_DATE = "2026-09-01"
END_DATE = "2026-09-30"
PER_PAGE = 100

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monitoring",
    "user": "postgres",
    "password": "1",
}


def patient_name(patient):
    parts = [
        patient.get("name") or "",
        patient.get("surname") or "",
        patient.get("patronymic") or "",
    ]
    return " ".join(part.strip() for part in parts if part.strip())


def hospitalizations():
    page = 1
    items = []

    while True:
        response = requests.get(
            URL,
            headers=HEADERS,
            params={
                "doctors[0]": DOCTOR_ID,
                "department_id": DEPARTMENT_ID,
                "start_date": START_DATE,
                "end_date": END_DATE,
                "status": "provided",
                "type_list": "emergency_room",
                "page": page,
                "per_page": PER_PAGE,
            },
            timeout=30,
        )

        if response.status_code == 404:
            return None

        if response.status_code != 200:
            raise RuntimeError(
                f"status {response.status_code}: {response.text[:300]}"
            )

        result = response.json()
        items.extend(result.get("data") or [])

        if not (result.get("meta") or {}).get("has_more_pages", False):
            break

        page += 1

    return items


def by_day(items):
    grouped = defaultdict(list)
    doctor_name = ""
    doctor_id = str(DOCTOR_ID)

    for item in items:
        doctor = item.get("doctor") or {}
        patient = item.get("patient") or {}
        if doctor.get("name"):
            doctor_name = doctor["name"]
        if doctor.get("id"):
            doctor_id = str(doctor["id"])

        department = item.get("department") or {}
        day = str(item.get("start_at") or "")[:10]
        if not day:
            continue

        grouped[day].append({
            "kasal nomi": patient_name(patient),
            "uuid": patient.get("uuid") or "",
            "start_date": str(item.get("start_at") or "")[:10] or None,
            "end_date": str(item.get("end_at") or "")[:10] or None,
            "branch": (department.get("title") or "").strip(),
            "is_branch": True,
        })

    return [
        {
            "doctor": doctor_name,
            "dmed_id": doctor_id,
            "sana": day,
            "qabullar": len(patients),
            "is_branch": True,
            "kasal_dmed_id": patients,
        }
        for day, patients in sorted(grouped.items())
    ]


def local_doctor_id(cursor, dmed_id):
    cursor.execute(
        "SELECT id FROM doctors WHERE dmed_id = %s",
        (str(dmed_id),),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def save_days(days):
    """Kelgan kunlarni qo'shadi. Bor qatorni o'zgartirmaydi va o'chirmaydi."""

    if not days:
        return {"saqlandi": 0}

    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    doctor_id = local_doctor_id(cursor, days[0]["dmed_id"])
    saved = 0

    if not doctor_id:
        cursor.close()
        conn.close()
        return {"saqlandi": 0, "holat": "shifokor topilmadi"}

    for day in days:
        patients = day["kasal_dmed_id"]
        cursor.execute(
            """
            INSERT INTO month_monitor_monthmonitor (
                doctor_id, appointment_date, patient_count, is_branch
            )
            VALUES (%s, %s, %s, TRUE)
            RETURNING id
            """,
            (doctor_id, day["sana"], len(patients)),
        )
        monitor_id = cursor.fetchone()[0]

        for patient in patients:
            cursor.execute(
                """
                INSERT INTO month_patient (
                    month_monitor_id,
                    patient,
                    uuid,
                    reception_date,
                    branch,
                    start_date,
                    end_date,
                    is_branch,
                    is_rezident
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, FALSE)
                """,
                (
                    monitor_id,
                    patient["kasal nomi"],
                    patient["uuid"],
                    day["sana"],
                    patient["branch"],
                    patient["start_date"],
                    patient["end_date"],
                ),
            )
        saved += 1

    conn.commit()
    cursor.close()
    conn.close()
    return {"saqlandi": saved}


def main():
    items = hospitalizations()
    if items is None:
        print(json.dumps({"status": 404, "data": []}, ensure_ascii=False, indent=4))
        return

    days = by_day(items)
    result = save_days(days)
    print(json.dumps(days, ensure_ascii=False, indent=4))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
