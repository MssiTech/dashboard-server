import json
from collections import defaultdict

import requests
import psycopg2


# =========================================================
# API
# =========================================================

URL = "https://zordoc.uz/api/mis/v2/appointments"

HEADERS = {
    "Device-Id": "4575853d-d610-4aea-ae71-8bbc3daf0e1b",
    "access_token": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczovL3pvcmRvYy51eiIsImlhdCI6MTc5MDc2MjE1NSwiZXhwIjoxODIyMjk4MTU1LCJuYmYiOjE3OTA3NjIxNTUsImp0aSI6ImZ3U2pyTHJ0cTVodHdOQVciLCJzdWIiOiI0MTU3MDk2MSIsInBydiI6IjkzOWY1N2JjYzViMjViZjhlNWI0NDIzYWJjN2M3MmI0Y2ZhOWM5NmEiLCJuYW1lIjoiSEFaUkFUT1YgWFVSU0hJRCBVTFVH4oCYQkVLIE_igJhH4oCYTEkiLCJlbWFpbCI6bnVsbCwicm9sZSI6ImRpcmVjdG9yIn0.P6W5NPBDUpA6nL8fE1qqiizwM41SvM40EAcyYoddtSk",
    "service_access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzUxMiJ9.eyJpYXQiOjE3OTA3NjIxNTUuMzI2MDEsImlzcyI6Imh0dHBzOi8vem9yZG9jLnV6IiwiZXhwIjoxNzkwODQ4NTU1LjMyNjAxLCJwaW5mbCI6IjMxOTAxOTc1MjgwMDY5IiwibmFtZSI6IlhVUlNISUQiLCJ1dWlkIjoiZTBhMjczNTktYjZlZS00ZDEyLWEyMmEtNjRjN2NiYjhkOTkxIiwic3VybmFtZSI6IkhBWlJBVE9WIiwicGF0cm9ueW1pYyI6IlVMVUfigJhCRUsgT-KAmEfigJhMSSIsInJvbGVzIjpbImRpcmVjdG9yIl0sInNwZWNpYWx0aWVzIjpbXSwiY2xpbmljX3V1aWQiOiJiYzAyMmEyYi0wMDQwLTRlYmQtYjYyYy0zMWQxZTZmYjA0MzkiLCJjbGluaWNfdGl0bGUiOiJCdXhvcm8gdmlsb3lhdCBrbydwIHRhcm1vcWxpIHRpYmJpeW90IG1hcmthemkiLCJwb3NpdGlvbnMiOlsiY29tbWlzc2lvbl9",
    "Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczovL3pvcmRvYy51eiIsImlhdCI6MTc5MDc2MjE1NSwiZXhwIjoxODIyMjk4MTU1LCJuYmYiOjE3OTA3NjIxNTUsImp0aSI6ImZ3U2pyTHJ0cTVodHdOQVciLCJzdWIiOiI0MTU3MDk2MSIsInBydiI6IjkzOWY1N2JjYzViMjViZjhlNWI0NDIzYWJjN2M3MmI0Y2ZhOWM5NmEiLCJuYW1lIjoiSEFaUkFUT1YgWFVSU0hJRCBVTFVH4oCYQkVLIE_igJhH4oCYTEkiLCJlbWFpbCI6bnVsbCwicm9sZSI6ImRpcmVjdG9yIn0.P6W5NPBDUpA6nL8fE1qqiizwM41SvM40EAcyYoddtSk",
}


# =========================================================
# DATABASE
# =========================================================

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monitoring",
    "user": "postgres",
    "password": "1",
}


# =========================================================
# QAYSI ORALIQ UCHUN OLISH
# =========================================================

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


def appointment_day(appointment):
    start_at = appointment.get("start_at") or ""
    return start_at[:10]


def get_patients(dmed_id):
    """Shu shifokorning berilgan oraliqdagi bemorlarini kun bo'yicha qaytaradi."""

    page = 1
    by_date = defaultdict(list)

    while True:
        params = {
            "statuses[0]": "provided",
            "doctors[0]": dmed_id,
            "unplanned": 0,
            "start_at": START_DATE,
            "end_at": END_DATE,
            "page": page,
            "per_page": PER_PAGE,
        }

        response = requests.get(
            URL,
            headers=HEADERS,
            params=params,
            timeout=30,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"status {response.status_code}: {response.text[:300]}"
            )

        result = response.json()
        data = result.get("data") or []

        for appointment in data:
            doctor = appointment.get("doctor") or {}
            if str(doctor.get("id") or "") != str(dmed_id):
                continue

            day = appointment_day(appointment)
            if not day or day < START_DATE or day > END_DATE:
                continue

            patient = appointment.get("patient") or {}
            by_date[day].append({
                "kasal nomi": patient_name(patient),
                "uuid": patient.get("uuid") or "",
            })

        meta = result.get("meta") or {}
        if not meta.get("has_more_pages", False):
            break

        page += 1

    return by_date


def save_day(cursor, doctor_id, day, patients):
    """Shu sana uchun yozuv bo'lmasa, yangi qator qo'shadi. Eskisini o'zgartirmaydi."""

    cursor.execute(
        """
        SELECT id
        FROM month_monitor_monthmonitor
        WHERE doctor_id = %s AND appointment_date = %s
        """,
        (doctor_id, day),
    )
    row = cursor.fetchone()
    if row or not patients:
        return False

    cursor.execute(
        """
        INSERT INTO month_monitor_monthmonitor (
            doctor_id,
            appointment_date,
            patient_count
        )
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (doctor_id, day, len(patients)),
    )
    monitor_id = cursor.fetchone()[0]

    for patient in patients:
        cursor.execute(
            """
            INSERT INTO month_patient (
                month_monitor_id,
                patient,
                uuid,
                reception_date
            )
            VALUES (%s, %s, %s, %s)
            """,
            (
                monitor_id,
                patient["kasal nomi"],
                patient["uuid"],
                day,
            ),
        )

    return True


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


def existing_days(cursor, doctor_id):
    cursor.execute(
        """
        SELECT m.id, m.appointment_date, COUNT(p.id)
        FROM month_monitor_monthmonitor m
        LEFT JOIN month_patient p ON p.month_monitor_id = m.id
        WHERE m.doctor_id = %s
          AND m.appointment_date BETWEEN %s AND %s
        GROUP BY m.id, m.appointment_date
        """,
        (doctor_id, START_DATE, END_DATE),
    )
    filled = set()
    for monitor_id, appointment_date, patient_count in cursor.fetchall():
        day = appointment_date.isoformat()
        if patient_count:
            filled.add(day)
            continue
        cursor.execute(
            "DELETE FROM month_monitor_monthmonitor WHERE id = %s",
            (monitor_id,),
        )
    return filled


def save_polyclinic_patients():
    doctors = polyclinic_doctors()
    results = []

    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    for doctor_id, full_name, dmed_id in doctors:
        filled = existing_days(cursor, doctor_id)
        by_date = get_patients(dmed_id)

        saved_days = 0
        saved_patients = 0
        for day in sorted(by_date):
            patients = by_date[day]
            if day in filled or not patients:
                continue
            if save_day(cursor, doctor_id, day, patients):
                saved_days += 1
                saved_patients += len(patients)

        if saved_days:
            results.append({
                "doctor": full_name,
                "dmed_id": dmed_id,
                "dan": START_DATE,
                "gacha": END_DATE,
                "kunlar": saved_days,
                "qabullar": saved_patients,
            })
        elif not by_date:
            results.append({
                "doctor": full_name,
                "dmed_id": dmed_id,
                "dan": START_DATE,
                "gacha": END_DATE,
                "holat": "qabul yo'q, saqlanmadi",
            })
        else:
            results.append({
                "doctor": full_name,
                "dmed_id": dmed_id,
                "dan": START_DATE,
                "gacha": END_DATE,
                "holat": "eski qabul qoldirildi",
            })

        conn.commit()

    cursor.close()
    conn.close()
    return results


def main():
    print(f"Sana: {START_DATE} — {END_DATE}")
    results = save_polyclinic_patients()

    print(
        json.dumps(
            results,
            ensure_ascii=False,
            indent=4,
        )
    )
    saved = sum(item.get("qabullar", 0) for item in results)
    print(f"DB'ga saqlandi: {saved} ta qabul")


if __name__ == "__main__":
    main()
