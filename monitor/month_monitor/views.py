import calendar
from datetime import date, datetime

from django.db.models import Prefetch, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from monitor.models import (
    Doctors,
    Monitoring,
    Patients,
    PatientCurrentView,
    PattientCurrentDiagnosis,
)
from monitor.month_monitor.serializers import (
    BranchMonitoringSerializer,
    MonthMonitoringSerializer,
    StationaryDoctorSerializer,
)
from monitor.ambulator.serializers import patient_passport
from monitor.pagination import PaginationList

COUNT_FIELDS = (
    "appointment_count",
    "current_view_count",
    "examination_count",
    "diagnosis_count",
    "analysis_count",
    "diagnostika_count",
)

BRANCH_FIELDS = (
    "appointment_count",
    "rezident_count",
    "non_rezident_count",
    "simple_count",
    "examination_count",
    "diagnosis_count",
    "analysis_count",
    "diagnostika_count",
)


def selected_period(request):
    raw_start = (request.query_params.get("start_date") or "").strip()
    raw_end = (request.query_params.get("end_date") or "").strip()
    if not raw_start and not raw_end:
        today = date.today()
        start = date(today.year, today.month, 1)
        end = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
        return start, end
    if not raw_start or not raw_end:
        return Response(
            {"date": "start_date va end_date birga berilishi kerak"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        start = datetime.strptime(raw_start, "%Y-%m-%d").date()
        end = datetime.strptime(raw_end, "%Y-%m-%d").date()
    except ValueError:
        return Response({"date": "Sana YYYY-MM-DD formatida bo‘lishi kerak"}, status=status.HTTP_400_BAD_REQUEST)
    if start > end:
        return Response({"date": "start_date end_date dan katta bo‘lmasligi kerak"}, status=status.HTTP_400_BAD_REQUEST)
    return start, end


class MonthMonitoringListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = PaginationList

    @swagger_auto_schema(
        tags=["Monitor / Month"],
        responses={200: MonthMonitoringSerializer(many=True)},
        manual_parameters=[
            openapi.Parameter("start_date", openapi.IN_QUERY, description="Boshlanish (YYYY-MM-DD). Bo'sh bo'lsa oyning 1-kuni", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("end_date", openapi.IN_QUERY, description="Tugash (YYYY-MM-DD). Bo'sh bo'lsa oyning oxiri", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("full_name", openapi.IN_QUERY, description="Shifokor F.I.Sh.", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("page", openapi.IN_QUERY, description="Номер страницы", type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter("limit", openapi.IN_QUERY, description="Количество элементов на странице", type=openapi.TYPE_INTEGER, required=False),
        ],
    )
    def get(self, request):
        period = selected_period(request)
        if isinstance(period, Response):
            return period
        start, end = period
        full_name = (request.query_params.get("full_name") or "").strip()

        rows = Monitoring.objects.filter(
            date__range=(start, end),
            doctor__polyclinic=True,
        )
        if full_name:
            rows = rows.filter(doctor__full_name__icontains=full_name)
        rows = (
            rows.values("doctor_id", "doctor__full_name")
            .annotate(**{field: Coalesce(Sum(field), 0) for field in COUNT_FIELDS})
            .order_by("doctor__full_name")
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(rows, request)
        data = [
            {
                "id": row["doctor_id"],
                "doctor": {"id": row["doctor_id"], "full_name": row["doctor__full_name"] or ""},
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                **{field: row[field] for field in COUNT_FIELDS},
            }
            for row in page
        ]
        return Response(MonthMonitoringSerializer(data, many=True).data, status=status.HTTP_200_OK)


class MonthMonitoringDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Monitor / Month"],
        manual_parameters=[
            openapi.Parameter("start_date", openapi.IN_QUERY, description="Boshlanish (YYYY-MM-DD). Ro'yxatdagi oraliq", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("end_date", openapi.IN_QUERY, description="Tugash (YYYY-MM-DD). Ro'yxatdagi oraliq", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("patient", openapi.IN_QUERY, description="Kasal nomi", type=openapi.TYPE_STRING, required=False),
        ],
    )
    def get(self, request, doctor_id):
        period = selected_period(request)
        if isinstance(period, Response):
            return period
        start, end = period
        doctor = get_object_or_404(Doctors, id=doctor_id, polyclinic=True)
        patient_name = (request.query_params.get("patient") or "").strip()

        patients = Patients.objects.filter(
            reception__doctor=doctor,
            reception_date__range=(start, end),
        )
        if patient_name:
            patients = patients.filter(patient__icontains=patient_name)
        patients = patients.prefetch_related(
            Prefetch(
                "patient_current_view",
                queryset=PatientCurrentView.objects.filter(date__range=(start, end)),
            ),
            Prefetch(
                "pattientcurrentdiagnosis_set",
                queryset=PattientCurrentDiagnosis.objects.filter(
                    date__range=(start, end),
                ).prefetch_related("currentviewdiagnosis_set", "currentviewlaboratory_set"),
            ),
        ).order_by("-reception_date", "-id")

        return Response({
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "doctor": {"id": doctor.id, "full_name": doctor.full_name or ""},
            "patients": [self._patient(patient) for patient in patients],
        }, status=status.HTTP_200_OK)

    def _patient(self, patient):
        views = [
            item for item in patient.patient_current_view.all()
            if item.date == patient.reception_date and item.mkb_10_name
        ]
        diagnosis = next(
            (item for item in patient.pattientcurrentdiagnosis_set.all() if item.date == patient.reception_date),
            None,
        )
        diagnostika = {}
        tahlil = {}
        if diagnosis:
            self._collect(diagnostika, diagnosis.currentviewdiagnosis_set.all(), "diagnosis")
            self._collect(tahlil, diagnosis.currentviewlaboratory_set.all(), "laboratory")
        return {
            "id": patient.id,
            "full_name": patient.patient or "",
            "date": patient.reception_date.isoformat() if patient.reception_date else "",
            **patient_passport(patient),
            "korik": ", ".join(item.mkb_10_name for item in views),
            "tashxis": diagnosis.mkb_10_name if diagnosis and diagnosis.mkb_10_name else "",
            "tahlil": self._items(tahlil),
            "diagnostika": self._items(diagnostika),
        }

    def _collect(self, found, rows, field_name):
        for row in rows:
            name = getattr(row, field_name) or ""
            found[name] = found.get(name, False) or bool(row.is_exists)

    def _items(self, found):
        return [
            {"name": name, "status": "bor" if exists else "yo'q"}
            for name, exists in found.items()
        ]



class StasionaryBranchMonitoringListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Monitor / Month"],
        responses={200: BranchMonitoringSerializer(many=True)},
        manual_parameters=[
            openapi.Parameter("start_date", openapi.IN_QUERY, description="Boshlanish (YYYY-MM-DD). Bo'sh bo'lsa oyning 1-kuni", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("end_date", openapi.IN_QUERY, description="Tugash (YYYY-MM-DD). Bo'sh bo'lsa oyning oxiri", type=openapi.TYPE_STRING, required=False),
        ],
    )
    def get(self, request):
        period = selected_period(request)
        if isinstance(period, Response):
            return period
        start, end = period

        rows = (
            Monitoring.objects.filter(
                is_stasionary=True,
                date__range=(start, end),
                branch__isnull=False,
            )
            .values("branch__name")
            .annotate(**{field: Coalesce(Sum(field), 0) for field in BRANCH_FIELDS})
            .order_by("branch__name")
        )
        data = [
            {
                "branch": row["branch__name"] or "",
                **{field: row[field] for field in BRANCH_FIELDS},
            }
            for row in rows
        ]
        return Response(BranchMonitoringSerializer(data, many=True).data, status=status.HTTP_200_OK)


class StasionaryDoctorMonitoringListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = PaginationList

    @swagger_auto_schema(
        tags=["Monitor / Month"],
        responses={200: StationaryDoctorSerializer(many=True)},
        manual_parameters=[
            openapi.Parameter("start_date", openapi.IN_QUERY, description="Boshlanish (YYYY-MM-DD). Bo'sh bo'lsa oyning 1-kuni", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("end_date", openapi.IN_QUERY, description="Tugash (YYYY-MM-DD). Bo'sh bo'lsa oyning oxiri", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("branch", openapi.IN_QUERY, description="Bo'lim nomi yoki id. Bo'sh bo'lsa hammasi", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("page", openapi.IN_QUERY, description="Sahifa raqami", type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter("limit", openapi.IN_QUERY, description="Sahifadagi soni", type=openapi.TYPE_INTEGER, required=False),
        ],
    )
    def get(self, request):
        period = selected_period(request)
        if isinstance(period, Response):
            return period
        start, end = period
        branch = (request.query_params.get("branch") or "").strip()

        rows = Monitoring.objects.filter(
            is_stasionary=True,
            date__range=(start, end),
            doctor__isnull=False,
            branch__isnull=False,
        )
        if branch.isdigit():
            rows = rows.filter(branch_id=int(branch))
        elif branch:
            rows = rows.filter(branch__name__iexact=branch)
        rows = (
            rows.values("doctor_id", "doctor__full_name", "branch__name")
            .annotate(**{field: Coalesce(Sum(field), 0) for field in BRANCH_FIELDS})
            .order_by("branch__name", "doctor__full_name")
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(rows, request)
        data = [
            {
                "id": row["doctor_id"],
                "doctor": row["doctor__full_name"] or "",
                "branch": row["branch__name"] or "",
                **{field: row[field] for field in BRANCH_FIELDS},
            }
            for row in page
        ]
        return Response(StationaryDoctorSerializer(data, many=True).data, status=status.HTTP_200_OK)


class StasionaryDoctorPatientsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Monitor / Month"],
        manual_parameters=[
            openapi.Parameter("start_date", openapi.IN_QUERY, description="Boshlanish (YYYY-MM-DD). Bo'sh bo'lsa oyning 1-kuni", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("end_date", openapi.IN_QUERY, description="Tugash (YYYY-MM-DD). Bo'sh bo'lsa oyning oxiri", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("patient", openapi.IN_QUERY, description="Kasal nomi", type=openapi.TYPE_STRING, required=False),
        ],
    )
    def get(self, request, doctor_id):
        period = selected_period(request)
        if isinstance(period, Response):
            return period
        start, end = period
        doctor = get_object_or_404(Doctors, id=doctor_id)
        patient_name = (request.query_params.get("patient") or "").strip()

        patients = Patients.objects.filter(
            reception__doctor=doctor,
            is_stasionary=True,
        ).filter(
            Q(start_date__isnull=True) | Q(start_date__lte=end),
            Q(end_date__isnull=True) | Q(end_date__gte=start),
        )
        if patient_name:
            patients = patients.filter(patient__icontains=patient_name)
        patients = patients.prefetch_related(
            Prefetch(
                "patient_current_view",
                queryset=PatientCurrentView.objects.select_related("mkb_10"),
            ),
            Prefetch(
                "pattientcurrentdiagnosis_set",
                queryset=PattientCurrentDiagnosis.objects.select_related("mkb_10").prefetch_related(
                    "currentviewdiagnosis_set",
                    "currentviewlaboratory_set",
                ),
            ),
        ).order_by("-start_date", "-id")

        return Response({
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "doctor": {"id": doctor.id, "full_name": doctor.full_name or ""},
            "branch": doctor.branch.name if doctor.branch_id and doctor.branch else "",
            "patients": [self._patient(patient) for patient in patients],
        }, status=status.HTTP_200_OK)

    def _with_code(self, item):
        name = (item.mkb_10_name or "").strip()
        code = (item.mkb_10.name or "").strip() if item.mkb_10_id and item.mkb_10 else ""
        if code and not name.lower().startswith(code.lower()):
            return f"{code} {name}".strip()
        return name or code

    def _patient(self, patient):
        diagnoses = [self._with_code(item) for item in patient.pattientcurrentdiagnosis_set.all()]
        diagnoses = [name for name in diagnoses if name]
        tahlil = {}
        diagnostika = {}
        for diagnosis in patient.pattientcurrentdiagnosis_set.all():
            self._collect(diagnostika, diagnosis.currentviewdiagnosis_set.all(), "diagnosis")
            self._collect(tahlil, diagnosis.currentviewlaboratory_set.all(), "laboratory")
        return {
            "id": patient.id,
            "full_name": patient.patient or "",
            "start_date": patient.start_date.isoformat() if patient.start_date else "",
            "end_date": patient.end_date.isoformat() if patient.end_date else "",
            "tur": patient.price_type or "",
            **patient_passport(patient),
            "korik": [
                {
                    "doctor": item.examiner_name or "",
                    "date": item.date.isoformat() if item.date else "",
                    "tashxis": self._with_code(item),
                }
                for item in patient.patient_current_view.all()
            ],
            "tashxis": ", ".join(diagnoses),
            "tahlil": self._items(tahlil),
            "diagnostika": self._items(diagnostika),
        }

    def _collect(self, found, rows, field_name):
        for row in rows:
            name = getattr(row, field_name) or ""
            found[name] = found.get(name, False) or bool(row.is_exists)

    def _items(self, found):
        return [
            {"name": name, "status": "bor" if exists else "yo'q"}
            for name, exists in found.items()
        ]