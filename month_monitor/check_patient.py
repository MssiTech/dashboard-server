import json
from datetime import datetime

import requests
import psycopg2

from get_patient import DB_CONFIG, HEADERS, PER_PAGE


BASE_URL = "https://zordoc.uz"

# doctors jadvalidagi id yoki dmed_id, va Zordoc shifoxona id. Ikkalasini qo'lda yoziladi.
DOCTOR_ID = "231308"
CLINIC_ID = "3470"
START_DATE = "2026-09-01"
END_DATE = "2026-09-30"


def as_date(value):
    if hasattr(value, "isoformat"):
        value = value.isoformat()
    return str(value)[:10]


def g2g_date(day):
    return datetime.strptime(as_date(day), "%Y-%m-%d").strftime("%d.%m.%y")


def load_doctor():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, full_name, dmed_id
        FROM doctors
        WHERE CAST(id AS TEXT) = %s OR dmed_id = %s
        ORDER BY CASE WHEN CAST(id AS TEXT) = %s THEN 0 ELSE 1 END
        LIMIT 1
        """,
        (str(DOCTOR_ID), str(DOCTOR_ID), str(DOCTOR_ID)),
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row


def doctor_patients(doctor_id):
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT month_patient.id, month_patient.patient, month_patient.uuid,
               month_patient.reception_date, month_patient.start_date, month_patient.end_date
        FROM month_patient
        JOIN month_monitor_monthmonitor
          ON month_monitor_monthmonitor.id = month_patient.month_monitor_id
        WHERE month_monitor_monthmonitor.doctor_id = %s
          AND month_patient.reception_date BETWEEN %s AND %s
        ORDER BY month_patient.reception_date, month_patient.id
        """,
        (doctor_id, START_DATE, END_DATE),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def diagnoses(patient_uuid, start, end):
    page = 1
    items = []
    start = as_date(start)
    end = as_date(end)

    while True:
        response = requests.get(
            f"{BASE_URL}/api/mis/v2/patients/{patient_uuid}/appointments/disease-related",
            headers=HEADERS,
            params={
                "page": page,
                "per_page": PER_PAGE,
                "start_at": start,
                "end_at": end,
            },
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        data = result.get("data") or {}
        visits = data.get("appointments") if isinstance(data, dict) else []
        items.extend(visits or [])

        if not (result.get("meta") or {}).get("has_more_pages", False):
            break

        page += 1

    return items


def diagnostic_appointments(patient_uuid, clinic_id, start, end):
    page = 1
    items = []

    while True:
        response = requests.get(
            f"{BASE_URL}/api/mis/g2g/patients/{patient_uuid}/appointments",
            headers=HEADERS,
            params={
                "page": page,
                "per_page": PER_PAGE,
                "start_at": g2g_date(start),
                "end_at": g2g_date(end),
                "is_diagnostic": 1,
            },
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()

        for item in result.get("data") or []:
            items.append(item)

        if not (result.get("meta") or {}).get("has_more_pages", False):
            break

        page += 1

    return items


def appointments(patient_uuid, start, end):
    """Ko'riklar. Sana bemorning start_date va end_date oralig'i."""

    page = 1
    items = []

    while True:
        response = requests.get(
            f"{BASE_URL}/api/mis/g2g/patients/{patient_uuid}/appointments",
            headers=HEADERS,
            params={
                "page": page,
                "per_page": PER_PAGE,
                "start_at": g2g_date(start),
                "end_at": g2g_date(end),
            },
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        items.extend(result.get("data") or [])

        if not (result.get("meta") or {}).get("has_more_pages", False):
            break

        page += 1

    return items


def muster_date(value):
    value = str(value or "").strip()
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def muster_rows(items):
    found = []
    seen = set()

    for item in items:
        doctor = item.get("doctor") or {}
        doctor_name = (doctor.get("name") or "").strip()
        day = muster_date(item.get("date"))
        for disease in item.get("disease_codes") or []:
            code = (disease.get("code") or "").strip()
            title = (disease.get("title") or "").strip()
            if not (code or title):
                continue
            key = (doctor_name, day, code, title)
            if key in seen:
                continue
            seen.add(key)
            found.append({
                "doctor_full_name": doctor_name,
                "date": day,
                "code": code,
                "mkb_10_name": title,
            })

    return found


def analyses(patient_uuid, start, end):
    page = 1
    items = []

    while True:
        response = requests.get(
            f"{BASE_URL}/api/mis/g2g/patients/{patient_uuid}/analyses",
            headers=HEADERS,
            params={
                "page": page,
                "per_page": PER_PAGE,
                "start_at": g2g_date(start),
                "end_at": g2g_date(end),
            },
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()

        for item in result.get("data") or []:
            items.append(item)

        if not (result.get("meta") or {}).get("has_more_pages", False):
            break

        page += 1

    return items


def service_titles(item):
    titles = []
    for service in item.get("group_services") or []:
        title = (service.get("title") or "").strip()
        if title:
            titles.append(title)
    return titles


def analysis_names(items):
    found = []
    seen = set()
    for item in items:
        for title in service_titles(item):
            if title in seen:
                continue
            seen.add(title)
            found.append(title)
    return found


def diagnostic_names(items):
    found = []
    seen = set()

    def add(title):
        title = (title or "").strip()
        if not title or title in seen:
            return
        seen.add(title)
        found.append(title)

    for item in items:
        doctor = item.get("doctor") or {}
        for specialty in doctor.get("specialties") or []:
            add(specialty.get("title"))
    return found


def found_on_day(names):
    rows = []
    seen = set()
    for name in names:
        name = (name or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        rows.append({"nomi": name, "holati": "bor"})
    return rows


def disease_pairs(items):
    found = []
    seen = set()

    for item in items:
        for disease in item.get("disease_codes") or []:
            title = (disease.get("title") or "").strip()
            code = (disease.get("code") or "").strip()
            key = (title, code)
            if key in seen or not (title or code):
                continue
            seen.add(key)
            found.append(key)

    return found


def filled(block):
    return bool((block.get("nomi") or "").strip() or (block.get("code") or "").strip())


def classification_id(cursor, code):
    code = (code or "").strip()
    if not code:
        return None
    cursor.execute("SELECT id FROM classification WHERE name = %s", (code,))
    row = cursor.fetchone()
    return row[0] if row else None


def examination_id(cursor, doctor_id, month_patient_id, day, title):
    cursor.execute(
        """
        SELECT id FROM patient_examination
        WHERE doctor_id = %s AND patient_id = %s AND date = %s AND mkb_10_name = %s
        LIMIT 1
        """,
        (doctor_id, month_patient_id, day, title or ""),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def add_muster(cursor, view_id, items):
    for item in items:
        title = (item.get("mkb_10_name") or "").strip()
        doctor_name = (item.get("doctor_full_name") or "").strip()
        day = item.get("date")
        cursor.execute(
            """
            SELECT id FROM patient_muster
            WHERE patient_examination_id = %s
              AND date IS NOT DISTINCT FROM %s
              AND COALESCE(mkb_10_name, '') = %s
              AND COALESCE(doctor_full_name, '') = %s
            LIMIT 1
            """,
            (view_id, day, title, doctor_name),
        )
        if cursor.fetchone():
            continue
        cursor.execute(
            """
            INSERT INTO patient_muster
                (patient_examination_id, doctor_full_name, date, mkb_10_id, mkb_10_name)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                view_id,
                doctor_name,
                day,
                classification_id(cursor, item.get("code")),
                title,
            ),
        )


def add_children(cursor, view_id, diagnostics, laboratories):
    for item in diagnostics:
        name = (item.get("nomi") or "").strip()
        if not name:
            continue
        cursor.execute(
            """
            SELECT id FROM patient_diagnosis
            WHERE patient_diagnosis_id = %s AND diagnosis = %s
            LIMIT 1
            """,
            (view_id, name),
        )
        if cursor.fetchone():
            continue
        cursor.execute(
            """
            INSERT INTO patient_diagnosis
                (patient_diagnosis_id, diagnosis, is_exists)
            VALUES (%s, %s, %s)
            """,
            (view_id, name, item.get("holati") == "bor"),
        )
    for item in laboratories:
        name = (item.get("nomi") or "").strip()
        if not name:
            continue
        cursor.execute(
            """
            SELECT id FROM patient_laboratory
            WHERE patient_current_view_id = %s AND laboratory = %s
            LIMIT 1
            """,
            (view_id, name),
        )
        if cursor.fetchone():
            continue
        cursor.execute(
            """
            INSERT INTO patient_laboratory
                (patient_current_view_id, laboratory, is_exists)
            VALUES (%s, %s, %s)
            """,
            (view_id, name, item.get("holati") == "bor"),
        )


def insert_examination(cursor, doctor_id, month_patient_id, day, code, title):
    cursor.execute(
        """
        INSERT INTO patient_examination
            (doctor_id, patient_id, date, mkb_10_id, mkb_10_name)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            doctor_id,
            month_patient_id,
            day,
            classification_id(cursor, code),
            title or "",
        ),
    )
    return cursor.fetchone()[0]


def save_results(doctor_id, rows):
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    saved = 0
    attached = set()

    for row in rows:
        month_patient_id = row["month_patient_id"]
        day = row["reception_date"]
        key = (month_patient_id, day)
        title = row["tashxis"].get("nomi") or ""
        has_tashxis = filled(row["tashxis"])
        has_checks = bool(row["diagnostika"] or row["laboratoriya"])
        has_muster = bool(row["muster"])
        if not has_tashxis and not has_checks and not has_muster:
            continue

        view_id = examination_id(cursor, doctor_id, month_patient_id, day, title if has_tashxis else "")
        if has_tashxis and view_id is None:
            view_id = insert_examination(
                cursor,
                doctor_id,
                month_patient_id,
                day,
                (row["tashxis"].get("code") or "").strip(),
                title,
            )
            saved += 1
        elif not has_tashxis and view_id is None:
            view_id = insert_examination(cursor, doctor_id, month_patient_id, day, "", "")
            saved += 1

        if view_id and key not in attached:
            add_children(cursor, view_id, row["diagnostika"], row["laboratoriya"])
            add_muster(cursor, view_id, row["muster"])
            attached.add(key)

    conn.commit()
    cursor.close()
    conn.close()
    return saved


def check_doctor(doctor_id, full_name, dmed_id, clinic_id):
    rows = []

    for month_patient_id, patient_name, patient_uuid, reception_date, start_date, end_date in doctor_patients(doctor_id):
        if not patient_uuid or not start_date or not end_date:
            continue
        day = as_date(reception_date or start_date)
        diagnosis_visits = diagnoses(patient_uuid, start_date, end_date)
        analysis_visits = analyses(patient_uuid, start_date, end_date)
        diagnostic_visits = diagnostic_appointments(patient_uuid, clinic_id, start_date, end_date)
        muster = muster_rows(appointments(patient_uuid, start_date, end_date))
        tashxis_pairs = disease_pairs(diagnosis_visits) or [("", "")]
        diagnostika = found_on_day(diagnostic_names(diagnostic_visits))
        laboratoriya = found_on_day(analysis_names(analysis_visits))

        for tashxis_title, tashxis_code in tashxis_pairs:
            rows.append({
                "month_patient_id": month_patient_id,
                "kasal nomi": patient_name or "",
                "uuid": patient_uuid or "",
                "reception_date": day,
                "tashxis": {
                    "nomi": tashxis_title,
                    "code": tashxis_code,
                },
                "diagnostika": diagnostika,
                "laboratoriya": laboratoriya,
                "muster": muster,
            })

    saved = save_results(doctor_id, rows)
    return {
        "doctor": full_name,
        "dmed_id": dmed_id,
        "clinic_id": clinic_id,
        "dan": START_DATE,
        "gacha": END_DATE,
        "bemorlar": len({row["month_patient_id"] for row in rows}),
        "saqlangan": saved,
    }


def main():
    if not str(DOCTOR_ID).strip() or not str(CLINIC_ID).strip():
        print("DOCTOR_ID va CLINIC_ID ni check_patient.py boshiga yozing")
        return

    doctor = load_doctor()
    if not doctor or not doctor[2]:
        print(f"Shifokor topilmadi: {DOCTOR_ID}")
        return

    doctor_id, full_name, dmed_id = doctor
    print(f"Sana: {START_DATE} — {END_DATE}")
    print(f"Shifokor: {full_name} ({dmed_id})")
    print(f"Shifoxona: {CLINIC_ID}")

    result = check_doctor(doctor_id, full_name, dmed_id, CLINIC_ID)
    print(json.dumps(result, ensure_ascii=False, indent=4))
    print("DB'ga saqlandi")


if __name__ == "__main__":
    main()
