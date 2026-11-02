import json

import psycopg2
import requests

from main import (
    DB_CONFIG,
    HEADERS,
    analyses,
    appointments,
    card_values,
    catalog_diagnosis,
    classification_catalog,
    classification_id,
    diagnoses,
    diagnostic_appointments,
    diagnostic_rows,
    disease_codes,
    empty_patient_card,
    exam_catalog,
    examinations,
    patient_card,
    required_names,
    service_titles,
    specialist_branch_id,
    with_status,
)


URL = "https://zordoc.uz/api/mis/v2/hospitalizations"
START_DATE = "2026-10-01"
END_DATE = "2026-10-31"
PER_PAGE = 100


def patient_name(patient):
    parts = [
        patient.get("name") or "",
        patient.get("surname") or "",
        patient.get("patronymic") or "",
    ]
    return " ".join(part.strip() for part in parts if part.strip())


def departments():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT name, dmed_id
        FROM branches
        WHERE dmed_id IS NOT NULL
          AND dmed_id <> ''
        ORDER BY name
        """
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def hospitalizations(department_id):
    page = 1
    found = []
    seen = set()

    while True:
        response = requests.get(
            URL,
            headers=HEADERS,
            params={
                "department_id": department_id,
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
            return found
        if response.status_code != 200:
            raise RuntimeError(f"status {response.status_code}: {response.text[:300]}")

        result = response.json()
        for item in result.get("data") or []:
            doctor = item.get("doctor") or {}
            patient = item.get("patient") or {}
            uuid = patient.get("uuid") or ""
            start = str(item.get("start_at") or "")[:10]
            end = str(item.get("end_at") or "")[:10]
            key = (uuid, start, end)
            if key in seen:
                continue
            seen.add(key)
            price = item.get("price_list") or {}
            diagnosis = item.get("diagnosis") or {}
            department = item.get("department") or {}
            found.append({
                "kasal nomi": patient_name(patient),
                "start_date": start or None,
                "end_date": end or None,
                "financing_type": item.get("financing_type") or "",
                "price_list": {
                    "id": price.get("id"),
                    "title": price.get("title") or "",
                },
                "diagnosis": {
                    "code": diagnosis.get("code") or "",
                    "title": diagnosis.get("title") or "",
                },
                "department": {
                    "id": department.get("id"),
                    "title": department.get("title") or "",
                },
                "patient": {
                    "id": patient.get("id"),
                    "uuid": uuid,
                    "name": patient.get("name") or "",
                    "surname": patient.get("surname") or "",
                    "patronymic": patient.get("patronymic") or "",
                },
                "doctor": {
                    "id": doctor.get("id"),
                    "name": doctor.get("name") or "",
                },
            })

        if not (result.get("meta") or {}).get("has_more_pages", False):
            break
        page += 1

    return found


def patient_details(patient, dmed_id, diagnostics, laboratories, catalog):
    empty = {
        **empty_patient_card(),
        "korik": [],
        "tashxis": [],
        "tahlil": [],
        "diagnostika": [],
    }
    uuid = (patient.get("patient") or {}).get("uuid") or ""
    start = patient.get("start_date")
    end = patient.get("end_date")
    if not uuid or not start or not end:
        return empty

    name = patient.get("kasal nomi") or uuid
    visits = fetch_list(appointments, uuid, start, end, name)
    codes = disease_codes(visits, dmed_id)
    tashxis = disease_codes(fetch_list(diagnoses, uuid, start, end, name), dmed_id)
    tashxis_codes = [item.get("code") or "" for item in tashxis if item.get("code")]
    korik_codes = [item.get("code") or "" for item in codes if item.get("code")]
    mkb_codes = tashxis_codes or korik_codes
    tahlil = []
    diagnostika = []
    if any(code in catalog for code in mkb_codes):
        tahlil = service_titles(fetch_list(analyses, uuid, start, end, name), start, end)
        diagnostika = diagnostic_rows(
            fetch_list(diagnostic_appointments, uuid, start, end, name),
            start,
            end,
        )

    diagnostika_titles = []
    for item in diagnostika:
        if item.get("title"):
            diagnostika_titles.append(item["title"])
        diagnostika_titles.extend(item.get("specialties") or [])

    return {
        **patient_card(uuid),
        "korik": examinations(visits, start, catalog, end),
        "tashxis": catalog_diagnosis(tashxis, catalog),
        "tahlil": with_status(
            required_names(mkb_codes, laboratories),
            [item.get("title") or "" for item in tahlil],
        ),
        "diagnostika": with_status(
            required_names(mkb_codes, diagnostics),
            diagnostika_titles,
        ),
    }


def fetch_list(loader, uuid, start, end, name):
    try:
        return loader(uuid, start, end)
    except requests.RequestException as exc:
        status = ""
        response = getattr(exc, "response", None)
        if response is not None:
            status = f" {response.status_code}"
        print(f"o'tkazildi: {name} / {loader.__name__}{status}", flush=True)
        return []


def filled_rows(items):
    return [
        item for item in items or []
        if (item.get("code") or "").strip() or (item.get("title") or "").strip()
    ]


PRICE_LABEL = {
    "rez": "rezident",
    "non": "no rezident",
    "simple": "oddiy",
}


def price_kind(patient):
    title = ((patient.get("price_list") or {}).get("title") or "").strip().lower()
    compact = title.replace(" ", "")
    if "norezident" in compact:
        return "non"
    if "rezident" in compact:
        return "rez"
    if "oddiy" in compact:
        return "simple"
    return ""


def price_label(patient):
    return PRICE_LABEL.get(price_kind(patient), "")


def delete_patient_rows(cursor, patient_id):
    cursor.execute(
        "SELECT id FROM pattient_current_diagnosis WHERE patient_id = %s",
        (patient_id,),
    )
    diagnosis_ids = [row[0] for row in cursor.fetchall()]
    if diagnosis_ids:
        cursor.execute(
            "DELETE FROM current_view_diagnosis WHERE patient_current_view_id = ANY(%s)",
            (diagnosis_ids,),
        )
        cursor.execute(
            "DELETE FROM current_view_laboratory WHERE patient_current_view_id = ANY(%s)",
            (diagnosis_ids,),
        )
        cursor.execute(
            "DELETE FROM pattient_current_diagnosis WHERE id = ANY(%s)",
            (diagnosis_ids,),
        )
    cursor.execute("DELETE FROM patient_current_view WHERE patient_id = %s", (patient_id,))
    cursor.execute("DELETE FROM patients WHERE id = %s", (patient_id,))


def clear_stationary(cursor, doctor_id, branch_id):
    cursor.execute(
        """
        SELECT patients.id, patients.reception_id
        FROM patients
        JOIN patient_receptions ON patient_receptions.id = patients.reception_id
        WHERE patient_receptions.doctor_id = %s
          AND patients.is_stasionary IS TRUE
          AND patients.branch_id IS NOT DISTINCT FROM %s
          AND (patients.start_date IS NULL OR patients.start_date <= %s)
          AND (patients.end_date IS NULL OR patients.end_date >= %s)
        """,
        (doctor_id, branch_id, END_DATE, START_DATE),
    )
    reception_ids = set()
    for patient_id, reception_id in cursor.fetchall():
        delete_patient_rows(cursor, patient_id)
        if reception_id:
            reception_ids.add(reception_id)
    for reception_id in reception_ids:
        cursor.execute(
            "SELECT COUNT(*) FROM patients WHERE reception_id = %s",
            (reception_id,),
        )
        if cursor.fetchone()[0] == 0:
            cursor.execute("DELETE FROM patient_receptions WHERE id = %s", (reception_id,))


def ensure_reception(cursor, doctor_id, day):
    cursor.execute(
        """
        SELECT id FROM patient_receptions
        WHERE doctor_id = %s AND reception_date = %s
        """,
        (doctor_id, day),
    )
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute(
        """
        INSERT INTO patient_receptions (doctor_id, reception_count, reception_date)
        VALUES (%s, 0, %s)
        RETURNING id
        """,
        (doctor_id, day),
    )
    return cursor.fetchone()[0]


def refresh_reception_count(cursor, reception_id):
    cursor.execute(
        """
        UPDATE patient_receptions
        SET reception_count = (SELECT COUNT(*) FROM patients WHERE reception_id = %s)
        WHERE id = %s
        """,
        (reception_id, reception_id),
    )


def insert_checks(cursor, doctor_id, patient_id, day, patient):
    visits = patient.get("korik") or []
    diseases = filled_rows(patient.get("tashxis"))
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
                patient_id,
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
                (branch_id, patient_id),
            )

    parents = diseases or (
        [{"code": "", "title": ""}] if patient.get("tahlil") or patient.get("diagnostika") else []
    )
    analysis_count = 0
    diagnostika_count = 0
    diagnosis_count = 0
    for disease in parents:
        if (disease.get("code") or "").strip() or (disease.get("title") or "").strip():
            diagnosis_count += 1
        cursor.execute(
            """
            INSERT INTO pattient_current_diagnosis
                (doctor_id, patient_id, date, mkb_10_id, mkb_10_name)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                doctor_id,
                patient_id,
                day,
                classification_id(cursor, disease.get("code")),
                (disease.get("title") or "")[:255],
            ),
        )
        diagnosis_id = cursor.fetchone()[0]
        for item in patient.get("diagnostika") or []:
            exists = item.get("holati") == "bor"
            cursor.execute(
                """
                INSERT INTO current_view_diagnosis
                    (patient_current_view_id, diagnosis, is_exists)
                VALUES (%s, %s, %s)
                """,
                (diagnosis_id, (item.get("title") or "")[:255], exists),
            )
            if exists:
                diagnostika_count += 1
        for item in patient.get("tahlil") or []:
            exists = item.get("holati") == "bor"
            cursor.execute(
                """
                INSERT INTO current_view_laboratory
                    (patient_current_view_id, laboratory, is_exists)
                VALUES (%s, %s, %s)
                """,
                (diagnosis_id, (item.get("title") or "")[:255], exists),
            )
            if exists:
                analysis_count += 1
    return len(visits), diagnosis_count, analysis_count, diagnostika_count


def save_monitoring(cursor, doctor_id, branch_id, patients, counts):
    if not patients:
        cursor.execute(
            """
            DELETE FROM monitoring
            WHERE doctor_id = %s
              AND date = %s
              AND is_stasionary IS TRUE
              AND branch_id IS NOT DISTINCT FROM %s
            """,
            (doctor_id, START_DATE, branch_id),
        )
        return

    simple_count = sum(1 for patient in patients if price_kind(patient) == "simple")
    rezident_count = sum(1 for patient in patients if price_kind(patient) == "rez")
    non_rezident_count = sum(1 for patient in patients if price_kind(patient) == "non")
    values = (
        len(patients),
        counts["examination"],
        counts["diagnosis"],
        counts["analysis"],
        counts["diagnostika"],
        rezident_count,
        non_rezident_count,
        simple_count,
        branch_id,
    )
    cursor.execute(
        """
        SELECT id FROM monitoring
        WHERE doctor_id = %s
          AND date = %s
          AND is_stasionary IS TRUE
          AND branch_id IS NOT DISTINCT FROM %s
        """,
        (doctor_id, START_DATE, branch_id),
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
                diagnostika_count = %s,
                rezident_count = %s,
                non_rezident_count = %s,
                simple_count = %s,
                branch_id = %s,
                current_view_count = 0,
                is_stasionary = TRUE
            WHERE id = %s
            """,
            (*values, existing[0]),
        )
        return

    cursor.execute(
        """
        INSERT INTO monitoring (
            doctor_id, branch_id, date, is_stasionary,
            appointment_count, current_view_count,
            examination_count, diagnosis_count, analysis_count, diagnostika_count,
            rezident_count, non_rezident_count, simple_count
        ) VALUES (%s, %s, %s, TRUE, %s, 0, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            doctor_id,
            branch_id,
            START_DATE,
            len(patients),
            counts["examination"],
            counts["diagnosis"],
            counts["analysis"],
            counts["diagnostika"],
            rezident_count,
            non_rezident_count,
            simple_count,
        ),
    )


def save_month(results):
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    saved = 0

    for doctor in results:
        cursor.execute(
            "SELECT id, polyclinic FROM doctors WHERE dmed_id = %s",
            (str(doctor["dmed_id"]),),
        )
        doctor_row = cursor.fetchone()
        if not doctor_row:
            continue
        doctor_id = doctor_row[0]
        cursor.execute(
            "SELECT id FROM branches WHERE dmed_id = %s",
            (str(doctor.get("department_id") or ""),),
        )
        branch_row = cursor.fetchone()
        branch_id = branch_row[0] if branch_row else None
        patients = doctor.get("kasal_dmed_id") or []

        clear_stationary(cursor, doctor_id, branch_id)
        counts = {"examination": 0, "diagnosis": 0, "analysis": 0, "diagnostika": 0}
        grouped = {}
        for patient in patients:
            day = patient.get("start_date") or START_DATE
            grouped.setdefault(day, []).append(patient)

        for day, group in grouped.items():
            reception_id = ensure_reception(cursor, doctor_id, day)
            for patient in group:
                cursor.execute(
                    """
                    INSERT INTO patients (
                        reception_id, patient, uuid, branch_id, is_stasionary,
                        price_type, start_date, end_date, reception_date,
                        region, city, neighborhood, polyclinic, phone,
                        birth_date, passport_series, inn
                    ) VALUES (%s, %s, %s, %s, TRUE, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        reception_id,
                        patient.get("kasal nomi") or "",
                        ((patient.get("patient") or {}).get("uuid") or ""),
                        branch_id,
                        price_label(patient),
                        patient.get("start_date"),
                        patient.get("end_date"),
                        day,
                        *card_values(patient),
                    ),
                )
                patient_id = cursor.fetchone()[0]
                examination, diagnosis, analysis, diagnostika = insert_checks(
                    cursor, doctor_id, patient_id, day, patient,
                )
                counts["examination"] += examination
                counts["diagnosis"] += diagnosis
                counts["analysis"] += analysis
                counts["diagnostika"] += diagnostika
                saved += 1
            refresh_reception_count(cursor, reception_id)

        save_monitoring(cursor, doctor_id, branch_id, patients, counts)

    conn.commit()
    cursor.close()
    conn.close()
    return saved


def main():
    print(f"Sana: {START_DATE} — {END_DATE}")
    diagnostics, laboratories = exam_catalog()
    catalog = classification_catalog()
    results = []
    output_file = "month.json"
    for branch_name, department_id in departments():
        patients = hospitalizations(department_id)
        print(f"{branch_name}: {len(patients)} bemor", flush=True)
        grouped = {}
        for patient in patients:
            dmed_id = str((patient.get("doctor") or {}).get("id") or "")
            if not dmed_id:
                continue
            bucket = grouped.setdefault((dmed_id, str(department_id)), {
                "doctor": (patient.get("doctor") or {}).get("name") or "",
                "dmed_id": dmed_id,
                "department_id": str(department_id),
                "branch": branch_name,
                "kasal_dmed_id": [],
            })
            patient.update(patient_details(patient, dmed_id, diagnostics, laboratories, catalog))
            bucket["kasal_dmed_id"].append(patient)
        branch_results = []
        for item in grouped.values():
            branch_results.append({
                **item,
                "qabullar": len(item["kasal_dmed_id"]),
            })
        saved = save_month(branch_results)
        results.extend(branch_results)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        print(f"{branch_name}: bazaga {saved}", flush=True)

    print(f"JSON saqlandi: {output_file}")
    print(f"Shifokor: {len(results)}, bemor: {sum(item['qabullar'] for item in results)}")


if __name__ == "__main__":
    main()
