from datetime import datetime

from django.db.models import Count, IntegerField, OuterRef, Prefetch, Subquery, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from monitor.models import Doctors
from monitor.pagination import PaginationList
from month_monitor.models import (
    MonthPatient,
    PatienMusterView,
    PatientDiagnosis,
    PatientExaminationView,
    PatientLaboratory,
)

BRANCHES = (
    "Отделение травматологии",
    "Отделение неврологии",
)


def period_dates(request):
    start_raw = request.query_params.get("start_date") or "2026-09-01"
    end_raw = request.query_params.get("end_date") or "2026-09-30"
    return (
        datetime.strptime(start_raw, "%Y-%m-%d").date(),
        datetime.strptime(end_raw, "%Y-%m-%d").date(),
    )


def doctor_count(queryset, group):
    total = queryset.order_by().values(group).annotate(total=Count("id")).values("total")
    return Coalesce(Subquery(total[:1], output_field=IntegerField()), Value(0))


class ExaminationSummaryAPIView(APIView):
    def get(self, request):
        try:
            start, end = period_dates(request)
        except ValueError:
            return Response(
                {"detail": "start_date va end_date YYYY-MM-DD bo'lsin"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        period = {"date__range": (start, end)}
        doctor_ids = MonthPatient.objects.filter(
            reception_date__range=(start, end),
            month_monitor__doctor__isnull=False,
        ).values("month_monitor__doctor_id")
        rows = (
            Doctors.objects.filter(id__in=doctor_ids, polyclinic=True)
            .annotate(
                receptions=doctor_count(
                    MonthPatient.objects.filter(
                        month_monitor__doctor=OuterRef("pk"),
                        reception_date__range=(start, end),
                    ),
                    "month_monitor__doctor",
                ),
                diagnoses=doctor_count(
                    PatientExaminationView.objects.filter(doctor=OuterRef("pk"), **period)
                    .exclude(mkb_10_name__isnull=True)
                    .exclude(mkb_10_name=""),
                    "doctor",
                ),
                analyses=doctor_count(
                    PatientLaboratory.objects.filter(
                        is_exists=True,
                        patient_current_view__doctor=OuterRef("pk"),
                        patient_current_view__date__range=(start, end),
                    ),
                    "patient_current_view__doctor",
                ),
                diagnostics=doctor_count(
                    PatientDiagnosis.objects.filter(
                        is_exists=True,
                        patient_diagnosis__doctor=OuterRef("pk"),
                        patient_diagnosis__date__range=(start, end),
                    ),
                    "patient_diagnosis__doctor",
                ),
            )
            .values("id", "full_name", "receptions", "diagnoses", "analyses", "diagnostics")
            .order_by("full_name")
        )
        return Response(
            [
                {
                    "id": row["id"],
                    "doctor": row["full_name"] or "",
                    "receptions": row["receptions"],
                    "diagnoses": row["diagnoses"],
                    "analyses": row["analyses"],
                    "diagnostics": row["diagnostics"],
                }
                for row in rows
            ],
            status=status.HTTP_200_OK,
        )


class BranchSummaryAPIView(APIView):
    def get(self, request):
        try:
            start, end = period_dates(request)
        except ValueError:
            return Response(
                {"detail": "start_date va end_date YYYY-MM-DD bo'lsin"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        period = {"date__range": (start, end)}
        doctor_ids = MonthPatient.objects.filter(
            is_branch=True,
            branch__in=BRANCHES,
            reception_date__range=(start, end),
            month_monitor__doctor__isnull=False,
        ).values("month_monitor__doctor_id")
        branch_name = (
            MonthPatient.objects.filter(
                is_branch=True,
                branch__in=BRANCHES,
                month_monitor__doctor=OuterRef("pk"),
                reception_date__range=(start, end),
            )
            .order_by("branch")
            .values("branch")[:1]
        )
        rows = (
            Doctors.objects.filter(id__in=doctor_ids)
            .annotate(
                branch_name=Subquery(branch_name),
                receptions=doctor_count(
                    MonthPatient.objects.filter(
                        is_branch=True,
                        branch__in=BRANCHES,
                        month_monitor__doctor=OuterRef("pk"),
                        reception_date__range=(start, end),
                    ),
                    "month_monitor__doctor",
                ),
                diagnoses=doctor_count(
                    PatientExaminationView.objects.filter(
                        patient__is_branch=True,
                        patient__branch__in=BRANCHES,
                        doctor=OuterRef("pk"),
                        **period,
                    )
                    .exclude(mkb_10_name__isnull=True)
                    .exclude(mkb_10_name=""),
                    "doctor",
                ),
                analyses=doctor_count(
                    PatientLaboratory.objects.filter(
                        is_exists=True,
                        patient_current_view__patient__is_branch=True,
                        patient_current_view__patient__branch__in=BRANCHES,
                        patient_current_view__doctor=OuterRef("pk"),
                        patient_current_view__date__range=(start, end),
                    ),
                    "patient_current_view__doctor",
                ),
                diagnostics=doctor_count(
                    PatientDiagnosis.objects.filter(
                        is_exists=True,
                        patient_diagnosis__patient__is_branch=True,
                        patient_diagnosis__patient__branch__in=BRANCHES,
                        patient_diagnosis__doctor=OuterRef("pk"),
                        patient_diagnosis__date__range=(start, end),
                    ),
                    "patient_diagnosis__doctor",
                ),
            )
            .values("id", "full_name", "branch_name", "receptions", "diagnoses", "analyses", "diagnostics")
            .order_by("full_name")
        )
        return Response(
            [
                {
                    "id": row["id"],
                    "doctor": row["full_name"] or "",
                    "branch": row["branch_name"] or "",
                    "receptions": row["receptions"],
                    "diagnoses": row["diagnoses"],
                    "analyses": row["analyses"],
                    "diagnostics": row["diagnostics"],
                }
                for row in rows
            ],
            status=status.HTTP_200_OK,
        )


def exam_status(rows, name_attr):
    status_by_name = {}
    for row in rows:
        name = (getattr(row, name_attr) or "").strip()
        if not name or not row.is_exists:
            continue
        status_by_name[name] = status_by_name.get(name, False) or bool(row.is_exists)
    return [
        {"name": name, "status": "bor" if exists else "yo'q"}
        for name, exists in status_by_name.items()
    ]


def patient_card(patient, number):
    titles = []
    seen_titles = set()
    laboratories = []
    diagnostics = []
    for exam in patient.patientexaminationview_set.all():
        title = (exam.mkb_10_name or "").strip()
        if title and title not in seen_titles:
            seen_titles.add(title)
            titles.append(title)
        laboratories.extend(exam.patientlaboratory_set.all())
        diagnostics.extend(exam.patientdiagnosis_set.all())
    return {
        "number": number,
        "patient": patient.patient or "",
        "date": patient.reception_date.isoformat() if patient.reception_date else "",
        "diagnosis": ", ".join(titles),
        "analysis": exam_status(laboratories, "laboratory"),
        "diagnostics": exam_status(diagnostics, "diagnosis"),
        "prescription": 0,
    }


class DoctorPatientsAPIView(APIView):
    pagination_class = PaginationList

    def get(self, request, doctor_id):
        try:
            start, end = period_dates(request)
        except ValueError:
            return Response(
                {"detail": "start_date va end_date YYYY-MM-DD bo'lsin"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        doctor = get_object_or_404(Doctors, id=doctor_id)
        patients = (
            MonthPatient.objects.filter(
                month_monitor__doctor=doctor,
                reception_date__range=(start, end),
            )
            .prefetch_related(
                Prefetch(
                    "patientexaminationview_set",
                    queryset=PatientExaminationView.objects.filter(date__range=(start, end)).prefetch_related(
                        Prefetch(
                            "patientlaboratory_set",
                            queryset=PatientLaboratory.objects.filter(is_exists=True).order_by("id"),
                        ),
                        Prefetch(
                            "patientdiagnosis_set",
                            queryset=PatientDiagnosis.objects.filter(is_exists=True).order_by("id"),
                        ),
                    ).order_by("-id"),
                )
            )
            .order_by("-reception_date")
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(patients, request, view=self)
        offset = (paginator.page.number - 1) * paginator.get_page_size(request)
        return paginator.get_paginated_response([
            patient_card(patient, offset + index)
            for index, patient in enumerate(page, start=1)
        ])


def present(value):
    text = (value or "").strip() if isinstance(value, str) else value
    return text or None


def branch_visit(row):
    visit = {}
    doctor_name = present(row.doctor_full_name)
    title = present(row.mkb_10_name)
    if doctor_name:
        visit["doctor_full_name"] = doctor_name
    if row.date:
        visit["date"] = row.date.isoformat()
    if title:
        visit["mkb_10_name"] = title
    return visit


def branch_patient_card(patient, number):
    titles = []
    seen_titles = set()
    laboratories = []
    diagnostics = []
    visits = []
    for exam in patient.patientexaminationview_set.all():
        title = present(exam.mkb_10_name)
        if title and title not in seen_titles:
            seen_titles.add(title)
            titles.append(title)
        laboratories.extend(exam.patientlaboratory_set.all())
        diagnostics.extend(exam.patientdiagnosis_set.all())
        for row in exam.patienmusterview_set.all():
            visit = branch_visit(row)
            if visit:
                visits.append(visit)
    return {
        "number": number,
        "patient": patient.patient or "",
        "start_date": patient.start_date.isoformat() if patient.start_date else "",
        "end_date": patient.end_date.isoformat() if patient.end_date else "",
        "diagnosis": ", ".join(titles),
        "visits": visits,
        "analysis": exam_status(laboratories, "laboratory"),
        "diagnostics": exam_status(diagnostics, "diagnosis"),
    }


class BranchPatientsAPIView(APIView):
    pagination_class = PaginationList

    def get(self, request, doctor_id):
        try:
            start, end = period_dates(request)
        except ValueError:
            return Response(
                {"detail": "start_date va end_date YYYY-MM-DD bo'lsin"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        doctor = get_object_or_404(Doctors, id=doctor_id)
        patients = (
            MonthPatient.objects.filter(
                is_branch=True,
                branch__in=BRANCHES,
                month_monitor__doctor=doctor,
                reception_date__range=(start, end),
            )
            .prefetch_related(
                Prefetch(
                    "patientexaminationview_set",
                    queryset=PatientExaminationView.objects.prefetch_related(
                        Prefetch(
                            "patientlaboratory_set",
                            queryset=PatientLaboratory.objects.filter(is_exists=True).order_by("id"),
                        ),
                        Prefetch(
                            "patientdiagnosis_set",
                            queryset=PatientDiagnosis.objects.filter(is_exists=True).order_by("id"),
                        ),
                        Prefetch(
                            "patienmusterview_set",
                            queryset=PatienMusterView.objects.order_by("date", "id"),
                        ),
                    ).order_by("-id"),
                )
            )
            .order_by("-reception_date")
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(patients, request, view=self)
        offset = (paginator.page.number - 1) * paginator.get_page_size(request)
        return paginator.get_paginated_response([
            branch_patient_card(patient, offset + index)
            for index, patient in enumerate(page, start=1)
        ])
