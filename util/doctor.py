import requests
import json

url = "https://zordoc.uz/api/mis/users"

headers = {
    "Device-Id": "4575853d-d610-4aea-ae71-8bbc3daf0e1b",
    "access_token": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczovL3pvcmRvYy51eiIsImlhdCI6MTc5MDc2MjE1NSwiZXhwIjoxODIyMjk4MTU1LCJuYmYiOjE3OTA3NjIxNTUsImp0aSI6ImZ3U2pyTHJ0cTVodHdOQVciLCJzdWIiOiI0MTU3MDk2MSIsInBydiI6IjkzOWY1N2JjYzViMjViZjhlNWI0NDIzYWJjN2M3MmI0Y2ZhOWM5NmEiLCJuYW1lIjoiSEFaUkFUT1YgWFVSU0hJRCBVTFVH4oCYQkVLIE_igJhH4oCYTEkiLCJlbWFpbCI6bnVsbCwicm9sZSI6ImRpcmVjdG9yIn0.P6W5NPBDUpA6nL8fE1qqiizwM41SvM40EAcyYoddtSk",
    "service_access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzUxMiJ9.eyJpYXQiOjE3OTA3NjIxNTUuMzI2MDEsImlzcyI6Imh0dHBzOi8vem9yZG9jLnV6IiwiZXhwIjoxNzkwODQ4NTU1LjMyNjAxLCJwaW5mbCI6IjMxOTAxOTc1MjgwMDY5IiwibmFtZSI6IlhVUlNISUQiLCJ1dWlkIjoiZTBhMjczNTktYjZlZS00ZDEyLWEyMmEtNjRjN2NiYjhkOTkxIiwic3VybmFtZSI6IkhBWlJBVE9WIiwicGF0cm9ueW1pYyI6IlVMVUfigJhCRUsgT-KAmEfigJhMSSIsInJvbGVzIjpbImRpcmVjdG9yIl0sInNwZWNpYWx0aWVzIjpbXSwiY2xpbmljX3V1aWQiOiJiYzAyMmEyYi0wMDQwLTRlYmQtYjYyYy0zMWQxZTZmYjA0MzkiLCJjbGluaWNfdGl0bGUiOiJCdXhvcm8gdmlsb3lhdCBrbydwIHRhcm1vcWxpIHRpYmJpeW90IG1hcmthemkiLCJwb3NpdGlvbnMiOlsiY29tbWlzc2lvbl9tZW1iZXJfcHJlZmVycmVudGluYWxfcmVmZXJyYWwiXX0.SPaLldtYLr4XEeblJckN8L_A0dShCkmOzRvrkvtHz_8OAGZJJlS9pPLvvUVIiDrxr2HkhtopuMFT0NfIt_9z43gAkVUUFtje_ReXCkClb85WKArBBy_L6wtpRCFYD_rWpBWDs0YYCSx-JdHKDkOS82OC",
    "Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczovL3pvcmRvYy51eiIsImlhdCI6MTc5MDc2MjE1NSwiZXhwIjoxODIyMjk4MTU1LCJuYmYiOjE3OTA3NjIxNTUsImp0aSI6ImZ3U2pyTHJ0cTVodHdOQVciLCJzdWIiOiI0MTU3MDk2MSIsInBydiI6IjkzOWY1N2JjYzViMjViZjhlNWI0NDIzYWJjN2M3MmI0Y2ZhOWM5NmEiLCJuYW1lIjoiSEFaUkFUT1YgWFVSU0hJRCBVTFVH4oCYQkVLIE_igJhH4oCYTEkiLCJlbWFpbCI6bnVsbCwicm9sZSI6ImRpcmVjdG9yIn0.P6W5NPBDUpA6nL8fE1qqiizwM41SvM40EAcyYoddtSk",
}

all_doctors = []

page = 1
per_page = 48

while True:

    params = {
        "per_page": per_page,
        "page": page,
        "query_field": "name",
        "query_type": "ILIKE",
        "role": "doctor",
        "status": "active",
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30
        )
    except requests.RequestException as e:
        print(f"Request xatoligi: {e}")
        break

    print(f"Page {page} | Status: {response.status_code}")

    if response.status_code != 200:
        print("API xatoligi:")
        print(response.text)
        break

    try:
        result = response.json()
    except ValueError:
        print("Response JSON formatida emas:")
        print(response.text)
        break

    data = result.get("data", [])

    # Ma'lumot tugagan bo'lsa
    if not data:
        print("Boshqa doctorlar topilmadi.")
        break

    # Doctorlarni olish
    for item in data:

        doctor = item.get("doctor") or {}

        # Bir nechta specialty bo'lsa:
        # "Кардиолог, Терапевт"
        specialties = ", ".join(
            specialty.get("title")
            for specialty in doctor.get("specialties", [])
            if specialty.get("title")
        )

        all_doctors.append({
            "dmed_id": doctor.get("id"),
            "full_name": item.get("name"),
            "specialization": specialties,
        })

    print(
        f"Page {page}: "
        f"{len(data)} ta doctor olindi | "
        f"Jami: {len(all_doctors)}"
    )

    # API pagination ma'lumotini tekshirish
    meta = result.get("meta", {})
    last_page = meta.get("last_page")

    # Agar API oxirgi page'ni bergan bo'lsa
    if last_page and page >= last_page:
        print(f"Oxirgi page: {page}")
        break

    # Agar 48 tadan kam kelgan bo'lsa,
    # bu odatda oxirgi page hisoblanadi
    if len(data) < per_page:
        print("Oxirgi page aniqlandi.")
        break

    # Keyingi page
    page += 1


# ==========================================
# JSON faylga saqlash
# ==========================================

output_file = "doctors.json"

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(
        all_doctors,
        f,
        ensure_ascii=False,
        indent=4
    )

print("\n================================")
print(f"Jami doctorlar: {len(all_doctors)}")
print(f"JSON fayl saqlandi: {output_file}")
print("================================")