import json
import psycopg2


# ==============================
# PostgreSQL sozlamalari
# ==============================

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monitoring",
    "user": "postgres",
    "password": "1",
}


# ==============================
# JSON fayl
# ==============================

JSON_FILE = "doctors.json"


# ==============================
# JSON o'qish
# ==============================

with open(JSON_FILE, "r", encoding="utf-8") as f:
    doctors = json.load(f)


print(f"JSON'dan {len(doctors)} ta doctor olindi")


# ==============================
# PostgreSQL'ga ulanish
# ==============================

conn = psycopg2.connect(**DB_CONFIG)

cursor = conn.cursor()


# ==============================
# Ma'lumotlarni DB'ga yozish
# ==============================

created_count = 0
updated_count = 0


for doctor in doctors:

    dmed_id = str(doctor.get("dmed_id"))
    full_name = doctor.get("full_name", "").strip()
    specialization = doctor.get("specialization", "").strip()

    if not dmed_id or not full_name:
        continue

    cursor.execute(
        """
        INSERT INTO doctors (
            dmed_id,
            full_name,
            specialization
        )
        VALUES (%s, %s, %s)

        ON CONFLICT (dmed_id)
        DO UPDATE SET
            full_name = EXCLUDED.full_name,
            specialization = EXCLUDED.specialization
        """,
        (
            dmed_id,
            full_name,
            specialization,
        )
    )

    if cursor.rowcount == 1:
        created_count += 1


# ==============================
# Saqlash
# ==============================

conn.commit()


cursor.close()
conn.close()


print()
print("==============================")
print(f"Jami JSON doctorlar: {len(doctors)}")
print(f"DB'ga ishlov berildi: {created_count}")
print("==============================")