import json
import os
from pathlib import Path

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from monitor.models import Classification, DiagnsticExamination, LaboratoryExamination


JSON_FILE = Path(__file__).resolve().parent / "endikirinoloiya.json"

with JSON_FILE.open(encoding="utf-8") as f:
    diseases = json.load(f)

print(f"JSON'dan {len(diseases)} ta kasallik olindi")

Classification.objects.filter(name__contains=";").delete()

classification_count = 0
skipped_count = 0
laboratory_count = 0
diagnostic_count = 0


def mkb_codes(value):
    if isinstance(value, list):
        raw = value
    elif value:
        raw = [value]
    else:
        raw = []
    codes = []
    for item in raw:
        code = str(item).strip().rstrip(".")
        if code:
            codes.append(code)
    return codes


for item in diseases:
    title = (item.get("mkb_name") or item.get("title") or "").strip()
    codes = mkb_codes(item.get("mkb_code") or item.get("name"))
    if not title or not codes:
        skipped_count += 1
        continue

    laboratories = [
        str(service).strip()
        for service in (item.get("laboratory") or item.get("labaratory") or [])
        if str(service).strip()
    ]
    diagnostics = [
        str(service).strip()
        for service in (item.get("diagnostic") or item.get("diganostic") or [])
        if str(service).strip()
    ]

    for code in codes:
        if Classification.objects.filter(name=code).exists():
            skipped_count += 1
            continue

        classification = Classification.objects.create(title=title, name=code)
        classification_count += 1

        LaboratoryExamination.objects.bulk_create([
            LaboratoryExamination(classification=classification, name=service)
            for service in laboratories
        ])
        DiagnsticExamination.objects.bulk_create([
            DiagnsticExamination(classification=classification, name=service)
            for service in diagnostics
        ])
        laboratory_count += len(laboratories)
        diagnostic_count += len(diagnostics)

print()
print("==============================")
print(f"Classification: {classification_count}")
print(f"O'tkazib yuborildi: {skipped_count}")
print(f"Laboratory: {laboratory_count}")
print(f"Diagnostic: {diagnostic_count}")
print("==============================")
