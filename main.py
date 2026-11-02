import json
import re
from datetime import datetime

import psycopg2
import requests


URL = "https://zordoc.uz/api/mis/v2/appointments"
BASE_URL = "https://zordoc.uz"

HEADERS = {
    "Device-Id": "4575853d-d610-4aea-ae71-8bbc3daf0e1b",
    "lang": "uz",
    "access_token": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczovL3pvcmRvYy51eiIsImlhdCI6MTc5MDc2MjE1NSwiZXhwIjoxODIyMjk4MTU1LCJuYmYiOjE3OTA3NjIxNTUsImp0aSI6ImZ3U2pyTHJ0cTVodHdOQVciLCJzdWIiOiI0MTU3MDk2MSIsInBydiI6IjkzOWY1N2JjYzViMjViZjhlNWI0NDIzYWJjN2M3MmI0Y2ZhOWM5NmEiLCJuYW1lIjoiSEFaUkFUT1YgWFVSU0hJRCBVTFVH4oCYQkVLIE_igJhH4oCYTEkiLCJlbWFpbCI6bnVsbCwicm9sZSI6ImRpcmVjdG9yIn0.P6W5NPBDUpA6nL8fE1qqiizwM41SvM40EAcyYoddtSk",
    "service_access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzUxMiJ9.eyJpYXQiOjE3OTA3NjIxNTUuMzI2MDEsImlzcyI6Imh0dHBzOi8vem9yZG9jLnV6IiwiZXhwIjoxNzkwODQ4NTU1LjMyNjAxLCJwaW5mbCI6IjMxOTAxOTc1MjgwMDY5IiwibmFtZSI6IlhVUlNISUQiLCJ1dWlkIjoiZTBhMjczNTktYjZlZS00ZDEyLWEyMmEtNjRjN2NiYjhkOTkxIiwic3VybmFtZSI6IkhBWlJBVE9WIiwicGF0cm9ueW1pYyI6IlVMVUfigJhCRUsgT-KAmEfigJhMSSIsInJvbGVzIjpbImRpcmVjdG9yIl0sInNwZWNpYWx0aWVzIjpbXSwiY2xpbmljX3V1aWQiOiJiYzAyMmEyYi0wMDQwLTRlYmQtYjYyYy0zMWQxZTZmYjA0MzkiLCJjbGluaWNfdGl0bGUiOiJCdXhvcm8gdmlsb3lhdCBrbydwIHRhcm1vcWxpIHRpYmJpeW90IG1hcmthemkiLCJwb3NpdGlvbnMiOlsiY29tbWlzc2lvbl9",
    "Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczovL3pvcmRvYy51eiIsImlhdCI6MTc5MDc2MjE1NSwiZXhwIjoxODIyMjk4MTU1LCJuYmYiOjE3OTA3NjIxNTUsImp0aSI6ImZ3U2pyTHJ0cTVodHdOQVciLCJzdWIiOiI0MTU3MDk2MSIsInBydiI6IjkzOWY1N2JjYzViMjViZjhlNWI0NDIzYWJjN2M3MmI0Y2ZhOWM5NmEiLCJuYW1lIjoiSEFaUkFUT1YgWFVSU0hJRCBVTFVH4oCYQkVLIE_igJhH4oCYTEkiLCJlbWFpbCI6bnVsbCwicm9sZSI6ImRpcmVjdG9yIn0.P6W5NPBDUpA6nL8fE1qqiizwM41SvM40EAcyYoddtSk",
}

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monitoring2",
    "user": "postgres",
    "password": "1",
}

STAT_DATE = "2026-10-30"
DATE = STAT_DATE
PER_PAGE = 100
CLINIC_ID = "3470"


def patient_name(patient):
    parts = [
        patient.get("name") or "",
        patient.get("surname") or "",
        patient.get("patronymic") or "",
    ]
    return " ".join(part.strip() for part in parts if part.strip())


def get_patients(dmed_id):
    page = 1
    patients = []

    while True:
        response = requests.get(
            URL,
            headers=HEADERS,
            params={
                "statuses[0]": "provided",
                "doctors[0]": dmed_id,
                "unplanned": 0,
                "start_at": STAT_DATE,
                "end_at": STAT_DATE,
                "page": page,
                "per_page": PER_PAGE,
            },
            timeout=30,
        )
        if response.status_code != 200:
            raise RuntimeError(f"status {response.status_code}: {response.text[:300]}")

        result = response.json()
        for appointment in result.get("data") or []:
            doctor = appointment.get("doctor") or {}
            if str(doctor.get("id") or "") != str(dmed_id):
                continue
            patient = appointment.get("patient") or {}
            patients.append({
                "kasal nomi": patient_name(patient),
                "uuid": patient.get("uuid") or "",
            })

        if not (result.get("meta") or {}).get("has_more_pages", False):
            break
        page += 1

    return patients


def save_reception(cursor, doctor_id, patients):
    cursor.execute(
        """
        SELECT id
        FROM patient_receptions
        WHERE doctor_id = %s AND reception_date = %s
        """,
        (doctor_id, STAT_DATE),
    )
    row = cursor.fetchone()
    if row or not patients:
        return (row[0] if row else None), False

    cursor.execute(
        """
        INSERT INTO patient_receptions (
            doctor_id,
            reception_count,
            reception_date
        )
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (doctor_id, len(patients), STAT_DATE),
    )
    reception_id = cursor.fetchone()[0]
    for patient in patients:
        cursor.execute(
            """
            INSERT INTO patients (
                reception_id,
                patient,
                uuid,
                reception_date,
                is_stasionary,
                region,
                city,
                neighborhood,
                polyclinic,
                phone,
                birth_date,
                passport_series,
                inn
            )
            VALUES (%s, %s, %s, %s, FALSE, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                reception_id,
                patient["kasal nomi"],
                patient["uuid"],
                STAT_DATE,
                *card_values(patient_card(patient.get("uuid"))),
            ),
        )
    return reception_id, True


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


def save_polyclinic_patients():
    doctors = polyclinic_doctors()
    results = []
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    for doctor_id, full_name, dmed_id in doctors:
        cursor.execute(
            """
            SELECT id
            FROM patient_receptions
            WHERE doctor_id = %s AND reception_date = %s
            """,
            (doctor_id, STAT_DATE),
        )
        existing = cursor.fetchone()
        if existing:
            cursor.execute(
                "SELECT COUNT(*) FROM patients WHERE reception_id = %s",
                (existing[0],),
            )
            if cursor.fetchone()[0] > 0:
                results.append({
                    "doctor": full_name,
                    "dmed_id": dmed_id,
                    "sana": STAT_DATE,
                    "holat": "eski qabul qoldirildi",
                })
                continue
            cursor.execute(
                "DELETE FROM patient_receptions WHERE id = %s",
                (existing[0],),
            )

        patients = get_patients(dmed_id)
        if not patients:
            results.append({
                "doctor": full_name,
                "dmed_id": dmed_id,
                "sana": STAT_DATE,
                "holat": "qabul yo'q, saqlanmadi",
            })
            continue

        save_reception(cursor, doctor_id, patients)
        results.append({
            "doctor": full_name,
            "dmed_id": dmed_id,
            "sana": STAT_DATE,
            "qabullar": len(patients),
            "kasal_dmed_id": patients,
        })

    conn.commit()
    cursor.close()
    conn.close()
    return results


def g2g_date(day):
    return datetime.strptime(str(day)[:10], "%Y-%m-%d").strftime("%d.%m.%y")


def parse_birthdate(value):
    text = str(value or "").strip()
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:10], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def nested_title(item):
    if isinstance(item, dict):
        return (item.get("title") or item.get("title_uz") or "").strip()
    return ""


def empty_patient_card():
    return {
        "region": "",
        "city": "",
        "neighborhood": "",
        "polyclinic": "",
        "phone": "",
        "birth_date": None,
        "passport_series": "",
        "inn": "",
    }


_PATIENT_CARDS = {}


def patient_card(uuid):
    uuid = (uuid or "").strip()
    if not uuid:
        return empty_patient_card()
    cached = _PATIENT_CARDS.get(uuid)
    if cached is not None:
        return cached
    card = empty_patient_card()
    try:
        response = requests.get(
            f"{BASE_URL}/api/mis/g2g/patients/{uuid}",
            headers=HEADERS,
            timeout=30,
        )
        if response.status_code == 200:
            payload = response.json()
            data = payload.get("data") if isinstance(payload, dict) else payload
            if isinstance(data, dict):
                serial = (data.get("passport_serial") or "").strip()
                number = (data.get("passport_number") or "").strip()
                card = {
                    "region": nested_title(data.get("city")),
                    "city": nested_title(data.get("district")),
                    "neighborhood": (data.get("place_residence") or "").strip(),
                    "polyclinic": nested_title(data.get("active_attached_clinic")),
                    "phone": (data.get("phone") or "").strip(),
                    "birth_date": parse_birthdate(data.get("birthdate")),
                    "passport_series": f"{serial} {number}".strip(),
                    "inn": str(data.get("pinfl") or data.get("inn") or "").strip(),
                }
    except requests.RequestException:
        pass
    _PATIENT_CARDS[uuid] = card
    return card


def card_values(card):
    return (
        (card.get("region") or "")[:255] or None,
        (card.get("city") or "")[:255] or None,
        (card.get("neighborhood") or "")[:255] or None,
        (card.get("polyclinic") or "")[:255] or None,
        (card.get("phone") or "")[:255] or None,
        card.get("birth_date"),
        (card.get("passport_series") or "")[:255] or None,
        (card.get("inn") or "")[:255] or None,
    )


def save_patient_card(cursor, patient_id, card):
    cursor.execute(
        """
        UPDATE patients
        SET region = %s,
            city = %s,
            neighborhood = %s,
            polyclinic = %s,
            phone = %s,
            birth_date = %s,
            passport_series = %s,
            inn = %s
        WHERE id = %s
        """,
        (*card_values(card), patient_id),
    )


def saved_patients():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT doctors.full_name, doctors.dmed_id, patients.patient, patients.uuid, patients.reception_date
        FROM patients
        JOIN patient_receptions ON patient_receptions.id = patients.reception_id
        JOIN doctors ON doctors.id = patient_receptions.doctor_id
        WHERE patients.reception_date = %s
          AND doctors.dmed_id IS NOT NULL
          AND doctors.dmed_id <> ''
        ORDER BY doctors.id, patients.id
        """,
        (DATE,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def appointments(patient_uuid, day, end=None):
    page = 1
    items = []
    start = g2g_date(day)
    finish = g2g_date(end or day)

    while True:
        response = requests.get(
            f"{BASE_URL}/api/mis/g2g/patients/{patient_uuid}/appointments",
            headers=HEADERS,
            params={
                "page": page,
                "per_page": PER_PAGE,
                "start_at": start,
                "end_at": finish,
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


def diagnoses(patient_uuid, day, end=None):
    page = 1
    items = []
    start = str(day)[:10]
    finish = str(end or day)[:10]

    while True:
        response = requests.get(
            f"{BASE_URL}/api/mis/v2/patients/{patient_uuid}/appointments/disease-related",
            headers=HEADERS,
            params={
                "page": page,
                "per_page": PER_PAGE,
                "start_at": start,
                "end_at": finish,
            },
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        data = result.get("data") or {}
        appointments = data.get("appointments") if isinstance(data, dict) else []
        items.extend(appointments or [])

        if not (result.get("meta") or {}).get("has_more_pages", False):
            break

        page += 1

    return items


def same_day(value, day, end=None):
    text = str(value or "").strip()
    target = str(day)[:10]
    finish = str(end or day)[:10]
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"):
        try:
            found = datetime.strptime(text[:10], fmt).strftime("%Y-%m-%d")
            return target <= found <= finish
        except ValueError:
            continue
    return False


def analyses(patient_uuid, day, end=None):
    page = 1
    items = []
    start = g2g_date(day)
    finish = g2g_date(end or day)

    while True:
        response = requests.get(
            f"{BASE_URL}/api/mis/g2g/patients/{patient_uuid}/analyses",
            headers=HEADERS,
            params={
                "page": page,
                "per_page": PER_PAGE,
                "start_at": start,
                "end_at": finish,
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


def diagnostic_appointments(patient_uuid, day, end=None):
    page = 1
    items = []
    start = g2g_date(day)
    finish = g2g_date(end or day)

    while True:
        response = requests.get(
            f"{BASE_URL}/api/mis/g2g/patients/{patient_uuid}/appointments",
            headers=HEADERS,
            params={
                "page": page,
                "per_page": PER_PAGE,
                "start_at": start,
                "end_at": finish,
                "is_diagnostic": 1,
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


def service_titles(items, day, end=None):
    found = []
    seen = set()

    for item in items:
        clinic = ((item.get("doctor") or {}).get("clinic") or {}).get("id")
        if str(clinic or "") != str(CLINIC_ID):
            continue
        if not same_day(item.get("date"), day, end):
            continue

        for service in item.get("group_services") or []:
            title = (service.get("title") or "").strip()
            if not title or title in seen:
                continue
            seen.add(title)
            found.append({"title": title})

    return found


def diagnostic_rows(items, day, end=None):
    found = []
    seen = set()

    for item in items:
        doctor = item.get("doctor") or {}
        clinic = (doctor.get("clinic") or {}).get("id")
        if str(clinic or "") != str(CLINIC_ID):
            continue
        if not same_day(item.get("date"), day, end):
            continue

        specialties = []
        for specialty in doctor.get("specialties") or []:
            name = (specialty.get("title") or "").strip()
            if name and name not in specialties:
                specialties.append(name)

        titles = []
        for service in item.get("group_services") or []:
            title = (service.get("title") or "").strip()
            if title and title not in titles:
                titles.append(title)
        if not titles and specialties:
            titles = [""]
        if not titles:
            continue

        for title in titles:
            key = (title, tuple(specialties))
            if key in seen:
                continue
            seen.add(key)
            found.append({
                "title": title,
                "specialties": specialties,
            })

    return found


def exam_catalog():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT classification.name, laboratory_examination.name
        FROM laboratory_examination
        JOIN classification ON classification.id = laboratory_examination.classification_id
        WHERE classification.name IS NOT NULL
          AND classification.name <> ''
          AND laboratory_examination.name IS NOT NULL
          AND laboratory_examination.name <> ''
        ORDER BY laboratory_examination.id
        """
    )
    laboratories = {}
    for code, name in cursor.fetchall():
        bucket = laboratories.setdefault(code, [])
        if name not in bucket:
            bucket.append(name)

    cursor.execute(
        """
        SELECT classification.name, diagnostic_examination.name
        FROM diagnostic_examination
        JOIN classification ON classification.id = diagnostic_examination.classification_id
        WHERE classification.name IS NOT NULL
          AND classification.name <> ''
          AND diagnostic_examination.name IS NOT NULL
          AND diagnostic_examination.name <> ''
        ORDER BY diagnostic_examination.id
        """
    )
    diagnostics = {}
    for code, name in cursor.fetchall():
        bucket = diagnostics.setdefault(code, [])
        if name not in bucket:
            bucket.append(name)

    cursor.close()
    conn.close()
    return diagnostics, laboratories


def required_names(codes, catalog):
    names = []
    seen = set()
    for code in codes:
        for name in catalog.get(code, []):
            if name in seen:
                continue
            seen.add(name)
            names.append(name)
    return names


NAME_ALIASES = {
    "alat": "alt",
    "asat": "ast",
    "koagullogramma": "koagulogramma",
    "aptt": "achtv",
    "protrombin": "pti",
}


def normalize_name(value):
    text = str(value or "").lower()
    text = text.replace("ʻ", "'").replace("’", "'").replace("`", "'").replace("‘", "'")
    text = text.replace("'", "")
    text = text.replace("rezus faktor", "rh omil")
    text = re.sub(r"[^0-9a-zа-яёўқғҳ]+", " ", text)
    words = []
    for word in text.split():
        word = NAME_ALIASES.get(word, word)
        if word.startswith("fibrinogen"):
            word = "fibrinogen"
        words.append(word)
    return words


BIOCHEMISTRY = (
    "umumiy bilirubin",
    "bevosita bilirubin",
    "alt",
    "ast",
    "mochevina",
    "glyukoza",
    "kreatinin",
    "umumiy oqsil",
)

KOAGULOGRAM = (
    "achtv",
    "pti",
    "fibrinogen",
)


def tokens_found(need, found_titles):
    if not need:
        return False
    need_text = " ".join(need)

    for title in found_titles:
        have = normalize_name(title)
        if not have:
            continue
        if need_text in " ".join(have):
            return True
        pos = 0
        matched = True
        for word in need:
            while pos < len(have) and have[pos] != word:
                pos += 1
            if pos >= len(have):
                matched = False
                break
            pos += 1
        if matched:
            return True

    return False


def biochemistry_found(found_titles):
    found = sum(1 for name in BIOCHEMISTRY if tokens_found(normalize_name(name), found_titles))
    return found >= 4


def coagulogram_found(found_titles):
    if tokens_found(["koagulogramma"], found_titles):
        return True
    found = sum(1 for name in KOAGULOGRAM if tokens_found([name], found_titles))
    return found >= 2


def hepatitis_bc_found(found_titles):
    for title in found_titles:
        text = " ".join(normalize_name(title))
        if "gepatit b" in text or "hbsag" in text or "gepatit c" in text or "hcv" in text:
            return True
    return False


def name_found(required, found_titles):
    need = normalize_name(required)
    if not need:
        return False
    if "gepatit" in need and "v" in need and "s" in need:
        return hepatitis_bc_found(found_titles)
    if any(word in need for word in ("bioximyaviy", "bioximiya", "biokimyoviy")):
        return biochemistry_found(found_titles)
    if "koagulogramma" in need:
        return coagulogram_found(found_titles)
    return tokens_found(need, found_titles)


def with_status(required, found_titles):
    return [
        {"title": name, "holati": "bor" if name_found(name, found_titles) else "yo'q"}
        for name in required
    ]


def classification_catalog():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT name, title FROM classification
        WHERE name IS NOT NULL AND name <> ''
        """
    )
    catalog = {name: title or "" for name, title in cursor.fetchall()}
    cursor.close()
    conn.close()
    return catalog


def with_code(code, title):
    title = (title or "").strip()
    if not code:
        return title
    if title.lower().startswith(code.lower()):
        return title
    return f"{code} {title}".strip()


def catalog_diagnosis(items, catalog):
    rows = []
    for item in items:
        code = (item.get("code") or "").strip()
        if code in catalog:
            rows.append({
                "holati": "bor",
                "code": code,
                "title": with_code(code, catalog[code] or item.get("title") or ""),
            })
        else:
            rows.append({
                "holati": "yo'q",
                "code": code,
                "title": with_code(code, item.get("title") or ""),
            })
    return rows


def classification_id(cursor, code):
    code = (code or "").strip()
    if not code:
        return None
    cursor.execute("SELECT id FROM classification WHERE name = %s", (code,))
    row = cursor.fetchone()
    return row[0] if row else None


def patient_pk(cursor, doctor_id, patient_uuid, reception_date):
    cursor.execute(
        """
        SELECT patients.id
        FROM patients
        JOIN patient_receptions ON patient_receptions.id = patients.reception_id
        WHERE patients.uuid = %s
          AND patient_receptions.doctor_id = %s
          AND patients.reception_date = %s
        ORDER BY patients.id
        LIMIT 1
        """,
        (patient_uuid, doctor_id, reception_date),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def filled_rows(items):
    return [
        item for item in items or []
        if (item.get("code") or "").strip() or (item.get("title") or "").strip()
    ]


def exists_count(cursor, table, doctor_id, day):
    cursor.execute(
        f"""
        SELECT COUNT(*)
        FROM {table} item
        JOIN pattient_current_diagnosis diagnosis
          ON diagnosis.id = item.patient_current_view_id
        WHERE diagnosis.doctor_id = %s
          AND diagnosis.date = %s
          AND item.is_exists IS TRUE
        """,
        (doctor_id, day),
    )
    return cursor.fetchone()[0]


def save_monitoring(cursor, doctor_id, day, patients):
    examination_count = 0
    diagnosis_count = 0

    for patient in patients:
        examination_count += len(filled_rows(patient.get("korik")))
        diagnosis_count += len(filled_rows(patient.get("tashxis")))

    analysis_count = exists_count(cursor, "current_view_laboratory", doctor_id, day)
    diagnostika_count = exists_count(cursor, "current_view_diagnosis", doctor_id, day)
    counts = (
        len(patients),
        examination_count,
        diagnosis_count,
        analysis_count,
        diagnostika_count,
    )
    cursor.execute(
        "SELECT id FROM monitoring WHERE doctor_id = %s AND date = %s",
        (doctor_id, day),
    )
    existing = cursor.fetchone()
    if existing:
        cursor.execute(
            """
            UPDATE monitoring
            SET appointment_count = %s,
                examination_count = %s,
                diagnosis_count = %s,
                analysis_count = %s,
                diagnostika_count = %s
            WHERE id = %s
            """,
            (*counts, existing[0]),
        )
        return

    cursor.execute(
        """
        INSERT INTO monitoring (
            doctor_id, date, appointment_count, current_view_count,
            examination_count, diagnosis_count, analysis_count, diagnostika_count
        ) VALUES (%s, %s, %s, 0, %s, %s, %s, %s)
        """,
        (doctor_id, day, *counts),
    )


def save_checks(results):
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    saved = 0

    for doctor in results:
        cursor.execute("SELECT id FROM doctors WHERE dmed_id = %s", (str(doctor["dmed_id"]),))
        doctor_row = cursor.fetchone()
        if not doctor_row:
            continue
        doctor_id = doctor_row[0]
        day = doctor["sana"]

        for patient in doctor["kasal_dmed_id"]:
            diseases = [
                item for item in patient.get("tashxis") or []
                if (item.get("code") or "").strip() or (item.get("title") or "").strip()
            ]
            visits = [
                item for item in patient.get("korik") or []
                if (item.get("code") or "").strip()
                or (item.get("title") or "").strip()
                or (item.get("doctor") or "").strip()
            ]
            current_patient_id = patient_pk(cursor, doctor_id, patient.get("uuid") or "", day)
            if not current_patient_id:
                continue
            save_patient_card(cursor, current_patient_id, patient)
            if not diseases and not visits:
                continue

            cursor.execute(
                """
                SELECT id FROM pattient_current_diagnosis
                WHERE doctor_id = %s AND patient_id = %s AND date = %s
                """,
                (doctor_id, current_patient_id, day),
            )
            old_ids = [row[0] for row in cursor.fetchall()]
            if old_ids:
                cursor.execute(
                    "DELETE FROM current_view_diagnosis WHERE patient_current_view_id = ANY(%s)",
                    (old_ids,),
                )
                cursor.execute(
                    "DELETE FROM current_view_laboratory WHERE patient_current_view_id = ANY(%s)",
                    (old_ids,),
                )
                cursor.execute(
                    "DELETE FROM pattient_current_diagnosis WHERE id = ANY(%s)",
                    (old_ids,),
                )

            cursor.execute(
                """
                SELECT id FROM patient_current_view
                WHERE doctor_id = %s AND patient_id = %s AND date = %s
                """,
                (doctor_id, current_patient_id, day),
            )
            old_views = [row[0] for row in cursor.fetchall()]
            if old_views:
                cursor.execute(
                    "DELETE FROM patient_current_view WHERE id = ANY(%s)",
                    (old_views,),
                )
            for visit in visits:
                branch_id = specialist_branch_id(cursor, visit)
                cursor.execute(
                    """
                    INSERT INTO patient_current_view
                        (doctor_id, patient_id, branch_id, date, examiner_name, mkb_10_id, mkb_10_name)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        doctor_id,
                        current_patient_id,
                        branch_id,
                        visit.get("date") or day,
                        (visit.get("doctor") or "")[:255],
                        classification_id(cursor, visit.get("code")),
                        (visit.get("title") or "")[:255],
                    ),
                )
                if branch_id:
                    cursor.execute(
                        """
                        UPDATE patients
                        SET branch_id = COALESCE(branch_id, %s)
                        WHERE id = %s
                        """,
                        (branch_id, current_patient_id),
                    )

            for disease in diseases:
                cursor.execute(
                    """
                    INSERT INTO pattient_current_diagnosis
                        (doctor_id, patient_id, date, mkb_10_id, mkb_10_name)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        doctor_id,
                        current_patient_id,
                        day,
                        classification_id(cursor, disease.get("code")),
                        (disease.get("title") or "")[:255],
                    ),
                )
                diagnosis_id = cursor.fetchone()[0]
                for item in patient.get("diagnostika") or []:
                    cursor.execute(
                        """
                        INSERT INTO current_view_diagnosis
                            (patient_current_view_id, diagnosis, is_exists)
                        VALUES (%s, %s, %s)
                        """,
                        (diagnosis_id, (item.get("title") or "")[:255], item.get("holati") == "bor"),
                    )
                for item in patient.get("tahlil") or []:
                    cursor.execute(
                        """
                        INSERT INTO current_view_laboratory
                            (patient_current_view_id, laboratory, is_exists)
                        VALUES (%s, %s, %s)
                        """,
                        (diagnosis_id, (item.get("title") or "")[:255], item.get("holati") == "bor"),
                    )
            saved += 1

        save_monitoring(cursor, doctor_id, day, doctor["kasal_dmed_id"])

    conn.commit()
    cursor.close()
    conn.close()
    return saved


def disease_codes(items, dmed_id):
    found = []
    seen = set()

    for item in items:
        doctor = item.get("doctor") or {}
        clinic = doctor.get("clinic") or {}
        if str(doctor.get("id") or "") != str(dmed_id):
            continue
        if str(clinic.get("id") or "") != str(CLINIC_ID):
            continue

        for disease in item.get("disease_codes") or []:
            code = (disease.get("code") or "").strip()
            title = (disease.get("title") or "").strip()
            key = (code, title)
            if key in seen or not (code or title):
                continue
            seen.add(key)
            found.append({
                "code": code,
                "title": title,
            })

    return found


def visit_day(value):
    text = str(value or "").strip()
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:10], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def examinations(items, day, catalog, end=None):
    found = []
    seen = set()
    for item in items:
        doctor = item.get("doctor") or {}
        clinic = (doctor.get("clinic") or {}).get("id")
        if str(clinic or "") != str(CLINIC_ID):
            continue
        if not same_day(item.get("date"), day, end):
            continue
        name = (doctor.get("name") or "").strip()
        specialties = [
            spec for spec in (doctor.get("specialties") or [])
            if (spec.get("type") or "") == "narrow_specialist"
        ]
        visit = visit_day(item.get("date"))
        diseases = [
            disease for disease in (item.get("disease_codes") or [])
            if (disease.get("code") or "").strip() or (disease.get("title") or "").strip()
        ] or [{}]
        for disease in diseases:
            code = (disease.get("code") or "").strip()
            raw = (disease.get("title") or "").strip()
            title = ""
            if code or raw:
                title = catalog_diagnosis([{"code": code, "title": raw}], catalog)[0]["title"]
            if not name and not title:
                continue
            key = (name, visit, code, title, str(doctor.get("id") or ""))
            if key in seen:
                continue
            seen.add(key)
            found.append({
                "doctor": name,
                "doctor_id": doctor.get("id"),
                "specialties": specialties,
                "code": code,
                "title": title,
                "date": visit,
            })
    return found


def specialist_branch_id(cursor, visit):
    specialties = [
        spec for spec in (visit.get("specialties") or [])
        if (spec.get("type") or "") == "narrow_specialist"
    ]
    if not specialties:
        return None
    dmed_id = str(visit.get("doctor_id") or "")
    if not dmed_id:
        return None
    cursor.execute(
        "SELECT id, branch_id FROM doctors WHERE dmed_id = %s",
        (dmed_id,),
    )
    doctor = cursor.fetchone()
    if not doctor:
        return None
    if doctor[1]:
        return doctor[1]
    for spec in specialties:
        title = (spec.get("title") or "").strip()
        if len(title) < 5:
            continue
        cursor.execute(
            """
            SELECT id FROM branches
            WHERE name ILIKE %s
            LIMIT 1
            """,
            (f"%{title}%",),
        )
        branch = cursor.fetchone()
        if branch:
            return branch[0]
        cursor.execute(
            """
            SELECT branch_id FROM doctors
            WHERE branch_id IS NOT NULL
              AND specialization ILIKE %s
            LIMIT 1
            """,
            (f"%{title}%",),
        )
        branch = cursor.fetchone()
        if branch and branch[0]:
            return branch[0]
    return None


def main():
    print(f"Sana: {STAT_DATE}")
    receptions = save_polyclinic_patients()
    print(json.dumps(receptions, ensure_ascii=False, indent=4))
    print(f"Qabullar saqlandi: {sum(1 for item in receptions if 'qabullar' in item)} ta shifokor")

    diagnostics, laboratories = exam_catalog()
    catalog = classification_catalog()
    grouped = {}

    for full_name, dmed_id, patient_name, patient_uuid, reception_date in saved_patients():
        day = str(reception_date)[:10]
        bucket = grouped.setdefault(str(dmed_id), {
            "doctor": full_name,
            "dmed_id": str(dmed_id),
            "sana": day,
            "kasal_dmed_id": [],
        })
        codes = []
        korik = []
        tashxis = []
        tahlil = []
        diagnostika = []
        mkb_codes = []
        if patient_uuid:
            visits = appointments(patient_uuid, day)
            codes = disease_codes(visits, dmed_id)
            korik = examinations(visits, day, catalog)
            tashxis = disease_codes(diagnoses(patient_uuid, day), dmed_id)
            tashxis_codes = [item.get("code") or "" for item in tashxis if item.get("code")]
            korik_codes = [item.get("code") or "" for item in codes if item.get("code")]
            mkb_codes = tashxis_codes or korik_codes
            if any(code in catalog for code in mkb_codes):
                tahlil = service_titles(analyses(patient_uuid, day), day)
                diagnostika = diagnostic_rows(diagnostic_appointments(patient_uuid, day), day)
        diagnostika_titles = []
        for item in diagnostika:
            if item.get("title"):
                diagnostika_titles.append(item["title"])
            diagnostika_titles.extend(item.get("specialties") or [])
        bucket["kasal_dmed_id"].append({
            "kasal nomi": patient_name or "",
            "uuid": patient_uuid or "",
            **(patient_card(patient_uuid) if patient_uuid else empty_patient_card()),
            "korik": korik,
            "tashxis": catalog_diagnosis(tashxis, catalog),
            "tahlil": with_status(
                required_names(mkb_codes, laboratories),
                [item.get("title") or "" for item in tahlil],
            ),
            "diagnostika": with_status(
                required_names(mkb_codes, diagnostics),
                diagnostika_titles,
            ),
        })

    results = []
    for item in grouped.values():
        results.append({
            "doctor": item["doctor"],
            "dmed_id": item["dmed_id"],
            "sana": item["sana"],
            "qabullar": len(item["kasal_dmed_id"]),
            "kasal_dmed_id": item["kasal_dmed_id"],
        })

    print(json.dumps(results, ensure_ascii=False, indent=4))
    print(f"Saqlandi: {save_checks(results)}")


if __name__ == "__main__":
    main()
