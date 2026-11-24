import psycopg2
import requests

from main import BASE_URL, DB_CONFIG, HEADERS, PER_PAGE


URL = f"{BASE_URL}/api/prescriptions/v1/prescriptions"
START_DATE = "2026-11-01"
END_DATE = "2026-11-17"

STATUS_UZ = {
    "approve": "Tasdiqlangan",
    "issued": "Berilgan",
    "partially_issued": "Qisman berilgan",
    "canceled": "Bekor qilingan",
}


def retsep_name(item):
    appointment = item.get("drug_appointment") or {}
    inn = appointment.get("inn") or {}
    title = (inn.get("title") or inn.get("title_uz") or "").strip()
    if title:
        return title[:255]
    medications = appointment.get("medication") or []
    if medications:
        title = (medications[0].get("title") or "").strip()
        if title:
            return title[:255]
    return (item.get("number") or "")[:255]


def retsep_date(item):
    appointment = item.get("drug_appointment") or {}
    return str(item.get("created_at") or appointment.get("start_date") or "")[:10] or None


def status_uz(item):
    raw = (item.get("status") or "").strip().lower()
    if not raw:
        return None
    return STATUS_UZ.get(raw, raw)[:255]


def doctor_id_from(item):
    appointment = item.get("drug_appointment") or {}
    doctor = appointment.get("doctor") or {}
    value = doctor.get("id") or appointment.get("doctor_id")
    return str(value) if value not in (None, "") else ""


def fetch_prescriptions():
    page = 1
    items = []

    while True:
        response = requests.get(
            URL,
            headers=HEADERS,
            params={
                "page": page,
                "per_page": PER_PAGE,
                "type": "simple",
                "start_at": START_DATE,
                "end_at": END_DATE,
            },
            timeout=30,
        )
        if response.status_code != 200:
            raise RuntimeError(f"status {response.status_code}: {response.text[:300]}")

        result = response.json()
        items.extend(result.get("data") or [])
        if not (result.get("meta") or {}).get("has_more_pages", False):
            break
        page += 1

    return items


def save_prescriptions(items):
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM retsep_monitoring WHERE date BETWEEN %s AND %s",
        (START_DATE, END_DATE),
    )

    saved = 0
    for item in items:
        day = retsep_date(item)
        if not day:
            continue
        cursor.execute(
            "SELECT id, branch_id FROM doctors WHERE dmed_id = %s",
            (doctor_id_from(item),),
        )
        row = cursor.fetchone()
        doctor_pk = row[0] if row else None
        branch_pk = row[1] if row else None
        cursor.execute(
            """
            INSERT INTO retsep_monitoring (doctor_id, branch_id, retsep_name, status, date)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                doctor_pk,
                branch_pk,
                retsep_name(item),
                status_uz(item),
                day,
            ),
        )
        saved += 1

    conn.commit()
    cursor.close()
    conn.close()
    return saved


def main():
    items = fetch_prescriptions()
    saved = save_prescriptions(items)
    print(f"Retseptlar: {len(items)}, saqlandi: {saved}")


if __name__ == "__main__":
    main()
