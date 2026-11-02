import calendar
from datetime import date, datetime

from django.db.models import Count, Prefetch, Q, Value
from django.shortcuts import get_object_or_404
from django.db.models.functions import Coalesce, NullIf, Trim
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from monitor.district_monitor.serializers import (
    DistrictMonitoringSerializer,
    DistrictPatientDetailSerializer,
    DistrictPatientSerializer,
    DistrictStatsSerializer,
)
from monitor.models import Patients, PatientCurrentView, PattientCurrentDiagnosis
from monitor.pagination import PaginationList


DATE_PARAMS = [
    openapi.Parameter(
        "start_date",
        openapi.IN_QUERY,
        description="Boshlanish (YYYY-MM-DD). Bo'sh bo'lsa oyning 1-kuni",
        type=openapi.TYPE_STRING,
        format=openapi.FORMAT_DATE,
        required=False,
    ),
    openapi.Parameter(
        "end_date",
        openapi.IN_QUERY,
        description="Tugash (YYYY-MM-DD). Bo'sh bo'lsa start_date yoki oyning oxiri",
        type=openapi.TYPE_STRING,
        format=openapi.FORMAT_DATE,
        required=False,
    ),
]


def parse_day(value):
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def query_dates(request):
    raw_start = (request.query_params.get("start_date") or "").strip()
    raw_end = (request.query_params.get("end_date") or "").strip()
    if not raw_start and not raw_end:
        today = date.today()
        return date(today.year, today.month, 1), date(
            today.year, today.month, calendar.monthrange(today.year, today.month)[1]
        )
    start = parse_day(raw_start)
    end = parse_day(raw_end)
    if raw_start and start is None:
        return Response({"date": "Sana YYYY-MM-DD formatida bo‘lishi kerak"}, status=status.HTTP_400_BAD_REQUEST)
    if raw_end and end is None:
        return Response({"date": "Sana YYYY-MM-DD formatida bo‘lishi kerak"}, status=status.HTTP_400_BAD_REQUEST)
    if start and not end:
        end = start
    if end and not start:
        start = end
    if start > end:
        return Response({"date": "start_date end_date dan katta bo‘lmasligi kerak"}, status=status.HTTP_400_BAD_REQUEST)
    return start, end


def polyclinic_patients(request):
    period = query_dates(request)
    if isinstance(period, Response):
        return period, None
    start, end = period
    region = (request.query_params.get("region") or "").strip()
    patients = Patients.objects.filter(
        is_stasionary=False,
        reception_date__range=(start, end),
    )
    if region:
        patients = patients.filter(region__icontains=region)
    return (start, end), patients


def district_patients(request):
    district = (request.query_params.get("district") or "").strip()
    if not district:
        return Response(
            {"district": "Tuman nomi kerak"},
            status=status.HTTP_400_BAD_REQUEST,
        ), None, None
    period, patients = polyclinic_patients(request)
    if isinstance(period, Response):
        return period, None, None
    start, end = period
    if district == "Noma'lum":
        patients = patients.filter(Q(city__isnull=True) | Q(city=""))
    else:
        patients = patients.filter(city__iexact=district)
    return (start, end, district), patients, None


class DistrictMonitoringListAPIView(APIView):
    # permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Monitor / District"],
        responses={200: DistrictMonitoringSerializer(many=True)},
        manual_parameters=DATE_PARAMS + [
            openapi.Parameter("region", openapi.IN_QUERY, description="Viloyat nomi", type=openapi.TYPE_STRING, required=False),
        ],
    )
    def get(self, request):
        period, patients = polyclinic_patients(request)
        if isinstance(period, Response):
            return period
        rows = (
            patients.annotate(
                district=Coalesce(NullIf(Trim("city"), Value("")), Value("Noma'lum"))
            )
            .values("district")
            .annotate(count=Count("id"))
            .order_by("-count", "district")
        )
        data = [
            {"district": row["district"] or "Noma'lum", "count": row["count"]}
            for row in rows
        ]
        return Response(
            DistrictMonitoringSerializer(data, many=True).data,
            status=status.HTTP_200_OK,
        )


class DistrictPatientsAPIView(APIView):
    # permission_classes = [IsAuthenticated]
    pagination_class = PaginationList

    @swagger_auto_schema(
        tags=["Monitor / District"],
        responses={200: DistrictPatientSerializer(many=True)},
        manual_parameters=[
            openapi.Parameter("district", openapi.IN_QUERY, description="Tuman nomi. Ro'yxatdagi district", type=openapi.TYPE_STRING, required=True),
            *DATE_PARAMS,
            openapi.Parameter("region", openapi.IN_QUERY, description="Viloyat nomi", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("page", openapi.IN_QUERY, description="Sahifa raqami", type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter("limit", openapi.IN_QUERY, description="Sahifadagi soni", type=openapi.TYPE_INTEGER, required=False),
        ],
    )
    def get(self, request):
        period, patients, _ = district_patients(request)
        if isinstance(period, Response):
            return period
        start, end, district = period
        patients = patients.select_related("branch", "reception__doctor").prefetch_related(
            Prefetch(
                "pattientcurrentdiagnosis_set",
                queryset=PattientCurrentDiagnosis.objects.exclude(mkb_10_name="").exclude(mkb_10_name__isnull=True),
            ),
        ).order_by(
            "-reception_date",
            "-id",
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(patients, request, view=self)
        if page is None:
            data = [self._patient(patient) for patient in patients]
            return Response({
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "district": district,
                "count": len(data),
                "results": DistrictPatientSerializer(data, many=True).data,
            }, status=status.HTTP_200_OK)
        data = [self._patient(patient) for patient in page]
        response = paginator.get_paginated_response(DistrictPatientSerializer(data, many=True).data)
        response.data = {
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "district": district,
            **response.data,
        }
        return response

    def _patient(self, patient):
        doctor = patient.reception.doctor if patient.reception_id and patient.reception else None
        names = [item.mkb_10_name for item in patient.pattientcurrentdiagnosis_set.all() if item.mkb_10_name]
        return {
            "id": patient.id,
            "full_name": patient.patient or "",
            "neighborhood": patient.neighborhood or "",
            "polyclinic": patient.polyclinic or "",
            "branch": patient.branch.name if patient.branch_id and patient.branch else "",
            "mkb_10_name": ", ".join(names),
            "reception_date": patient.reception_date.isoformat() if patient.reception_date else "",
            "doctor": doctor.full_name if doctor else "",
        }


class DistrictPatientDetailAPIView(APIView):
    # permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Monitor / District"],
        responses={200: DistrictPatientDetailSerializer()},
    )
    def get(self, request, patient_id):
        patient = get_object_or_404(
            Patients.objects.select_related("branch", "reception__doctor").prefetch_related(
                Prefetch(
                    "pattientcurrentdiagnosis_set",
                    queryset=PattientCurrentDiagnosis.objects.exclude(mkb_10_name="").exclude(mkb_10_name__isnull=True),
                ),
            ),
            id=patient_id,
            is_stasionary=False,
        )
        doctor = patient.reception.doctor if patient.reception_id and patient.reception else None
        names = [item.mkb_10_name for item in patient.pattientcurrentdiagnosis_set.all() if item.mkb_10_name]
        data = {
            "id": patient.id,
            "patient": patient.patient or "",
            "region": patient.region or "",
            "city": patient.city or "",
            "neighborhood": patient.neighborhood or "",
            "polyclinic": patient.polyclinic or "",
            "phone": patient.phone or "",
            "birth_date": patient.birth_date.isoformat() if patient.birth_date else "",
            "passport_series": patient.passport_series or "",
            "inn": patient.inn or "",
            "branch": patient.branch.name if patient.branch_id and patient.branch else "",
            "reception_date": patient.reception_date.isoformat() if patient.reception_date else "",
            "doctor": doctor.full_name if doctor else "",
            "mkb_10_name": ", ".join(names),
        }
        return Response(DistrictPatientDetailSerializer(data).data, status=status.HTTP_200_OK)


class DistrictStatsAPIView(APIView):
    # permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Monitor / District"],
        responses={200: DistrictStatsSerializer()},
        manual_parameters=[
            openapi.Parameter("district", openapi.IN_QUERY, description="Tuman nomi. Ro'yxatdagi district", type=openapi.TYPE_STRING, required=True),
            *DATE_PARAMS,
            openapi.Parameter("region", openapi.IN_QUERY, description="Viloyat nomi", type=openapi.TYPE_STRING, required=False),
        ],
    )
    def get(self, request):
        period, patients, _ = district_patients(request)
        if isinstance(period, Response):
            return period
        start, end, district = period
        views = PatientCurrentView.objects.filter(patient__in=patients)
        diseases = list(
            PattientCurrentDiagnosis.objects.filter(patient__in=patients)
            .exclude(mkb_10_name__isnull=True)
            .exclude(mkb_10_name="")
            .values("mkb_10_name")
            .annotate(count=Count("id"))
            .order_by("-count", "mkb_10_name")
        )
        branches = list(
            views.annotate(
                name=Coalesce("branch__name", "patient__branch__name", Value(""))
            )
            .exclude(name="")
            .values("name")
            .annotate(count=Count("id"))
            .order_by("-count", "name")
        )
        if not branches:
            branches = list(
                patients.exclude(branch__isnull=True)
                .values(name="branch__name")
                .annotate(count=Count("id"))
                .order_by("-count", "name")
            )
        data = {
            "district": district,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "diseases": [
                {"name": row["mkb_10_name"], "count": row["count"]}
                for row in diseases
            ],
            "branches": [
                {"name": row["name"], "count": row["count"]}
                for row in branches
            ],
        }
        return Response(DistrictStatsSerializer(data).data, status=status.HTTP_200_OK)

