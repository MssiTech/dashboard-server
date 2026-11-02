from pathlib import Path

import psycopg2
from openpyxl import Workbook

from get_patient import DB_CONFIG

EXCEL_FILE = Path(__file__).resolve().parent / "monitor.xlsx"


def monitors():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT doctors.full_name, COUNT(month_patient.id)
        FROM month_monitor_monthmonitor
        JOIN doctors ON doctors.id = month_monitor_monthmonitor.doctor_id
        LEFT JOIN month_patient
          ON month_patient.month_monitor_id = month_monitor_monthmonitor.id
        GROUP BY doctors.id, doctors.full_name
        ORDER BY doctors.full_name
        """
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [
        {
            "mutaxasis": full_name or "",
            "umumiy_qabullar": count,
        }
        for full_name, count in rows
    ]


def write_excel(rows):
    book = Workbook()
    sheet = book.active
    sheet.title = "Monitor"
    sheet.append(["Mutaxasis", "Umumiy qabullar"])
    for row in rows:
        sheet.append([row["mutaxasis"], row["umumiy_qabullar"]])
    book.save(EXCEL_FILE)


def main():
    rows = monitors()
    write_excel(rows)
    print(f"{len(rows)} ta mutaxasis saqlandi: {EXCEL_FILE.name}")


if __name__ == "__main__":
    main()
