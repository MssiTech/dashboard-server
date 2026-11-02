import calendar
from datetime import date

from django.db.models import Count, Q
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from monitor.ambulator_doctor.serializers import AmbulatorDoctorSerializer, AmbulatorDoctorTopSerializer
from monitor.district_monitor.views import parse_day
from monitor.models import DoctorMonthPlan, Doctors, Patients
from monitor.pagination import PaginationList


class AmbulatorDoctorPagination(PaginationList):
    page_size = 20


def selected_month(request):
    today = date.today()
    raw_date = (request.query_params.get("date") or "").strip()
    day = parse_day(raw_date) if raw_date else None
    if raw_date and day is None:
        return Response({"date": "Sana YYYY-MM-DD formatida bo‘lishi kerak"}, status=status.HTTP_400_BAD_REQUEST)

    if day:
        year, month = day.year, day.month
    else:
        raw_year = (request.query_params.get("year") or "").strip()
        raw_month = (request.query_params.get("month") or "").strip()
        try:
            year = int(raw_year) if raw_year else today.year
            month = int(raw_month) if raw_month else today.month
        except ValueError:
            return Response({"date": "year va month butun son bo‘lishi kerak"}, status=status.HTTP_400_BAD_REQUEST)
        if month < 1 or month > 12:
            return Response({"date": "month 1 dan 12 gacha bo‘lishi kerak"}, status=status.HTTP_400_BAD_REQUEST)
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
        last_day = min(end, today) if year == today.year and month == today.month else end
        day = (
            Patients.objects.filter(
                is_stasionary=False,
                reception_date__range=(start, last_day),
                reception__doctor__polyclinic=True,
            )
            .order_by("-reception_date")
            .values_list("reception_date", flat=True)
            .first()
        ) or last_day
        return start, end, day

    start = date(year, month, 1)
    end = date(year, month, calendar.monthrange(year, month)[1])
    if day < start or day > end:
        day = min(max(day, start), end)
    return start, end, day


MONTH_PARAMS = [
    openapi.Parameter("year", openapi.IN_QUERY, description="Yil. Bo'sh bo'lsa joriy yil", type=openapi.TYPE_INTEGER, required=False),
    openapi.Parameter("month", openapi.IN_QUERY, description="Oy (1-12). Bo'sh bo'lsa joriy oy", type=openapi.TYPE_INTEGER, required=False),
    openapi.Parameter("date", openapi.IN_QUERY, description="Kunlik qabul sanasi (YYYY-MM-DD). Berilsa shu oy olinadi", type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE, required=False),
]


def plan_number(value):
    try:
        return float(str(value or "").replace(",", ".").strip() or 0)
    except ValueError:
        return 0.0


def plan_percent(count, limit):
    limit_value = plan_number(limit)
    if limit_value <= 0:
        return 0.0
    return round((count / limit_value) * 100, 1)


def doctor_plan_fields(doctor, plans):
    plan = plans.get(doctor.id)
    bid = (plan.bid if plan else doctor.bid) or ""
    daily_limit = (plan.daily_limit if plan else doctor.daily_limit) or ""
    monthly_limit = (plan.monthly_limit if plan else doctor.monthly_limit) or ""
    return bid, daily_limit, monthly_limit


def annotated_doctors(start, end, day):
    return Doctors.objects.filter(polyclinic=True).select_related("branch").annotate(
        daily_count=Count(
            "patientreception__patients",
            filter=Q(
                patientreception__patients__is_stasionary=False,
                patientreception__patients__reception_date=day,
            ),
            distinct=True,
        ),
        monthly_count=Count(
            "patientreception__patients",
            filter=Q(
                patientreception__patients__is_stasionary=False,
                patientreception__patients__reception_date__range=(start, end),
            ),
            distinct=True,
        ),
    )


class AmbulatorDoctorListAPIView(APIView):
    # permission_classes = [IsAuthenticated]
    pagination_class = AmbulatorDoctorPagination

    @swagger_auto_schema(
        tags=["Monitor / Ambulator"],
        responses={200: AmbulatorDoctorSerializer(many=True)},
        manual_parameters=MONTH_PARAMS + [
            openapi.Parameter("full_name", openapi.IN_QUERY, description="Shifokor F.I.Sh.", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("page", openapi.IN_QUERY, description="Sahifa", type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter("limit", openapi.IN_QUERY, description="Sahifadagi soni", type=openapi.TYPE_INTEGER, required=False),
        ],
    )
    def get(self, request):
        period = selected_month(request)
        if isinstance(period, Response):
            return period
        start, end, day = period
        full_name = (request.query_params.get("full_name") or "").strip()

        doctors = annotated_doctors(start, end, day).order_by("full_name")
        if full_name:
            doctors = doctors.filter(full_name__icontains=full_name)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(doctors, request, view=self)
        rows = page if page is not None else doctors
        plans = {
            plan.doctor_id: plan
            for plan in DoctorMonthPlan.objects.filter(year=start.year, month=start.month)
        }
        data = []
        for doctor in rows:
            bid, daily_limit, monthly_limit = doctor_plan_fields(doctor, plans)
            data.append({
                "id": doctor.id,
                "dmed_id": doctor.dmed_id,
                "full_name": doctor.full_name or "",
                "branch": doctor.branch.name if doctor.branch_id and doctor.branch else "",
                "bid": bid,
                "daily_limit": daily_limit,
                "monthly_limit": monthly_limit,
                "daily_count": doctor.daily_count,
                "daily_percent": plan_percent(doctor.daily_count, daily_limit),
                "monthly_count": doctor.monthly_count,
                "monthly_percent": plan_percent(doctor.monthly_count, monthly_limit),
            })
        payload = AmbulatorDoctorSerializer(data, many=True).data
        if page is None:
            return Response(payload, status=status.HTTP_200_OK)
        response = paginator.get_paginated_response(payload)
        response.data = {
            "year": start.year,
            "month": start.month,
            "date": day.isoformat(),
            **response.data,
        }
        return response


def ranked_doctors(start, end, day, reverse):
    plans = {
        plan.doctor_id: plan
        for plan in DoctorMonthPlan.objects.filter(year=start.year, month=start.month)
    }
    rows = []
    for doctor in annotated_doctors(start, end, day):
        bid, daily_limit, monthly_limit = doctor_plan_fields(doctor, plans)
        if doctor.monthly_count <= 0:
            continue
        rows.append({
            "id": doctor.id,
            "dmed_id": doctor.dmed_id,
            "full_name": doctor.full_name or "",
            "branch": doctor.branch.name if doctor.branch_id and doctor.branch else "",
            "bid": bid,
            "daily_limit": daily_limit,
            "daily_count": doctor.daily_count,
            "daily_percent": plan_percent(doctor.daily_count, daily_limit),
            "monthly_count": doctor.monthly_count,
            "monthly_percent": plan_percent(doctor.monthly_count, monthly_limit),
        })
    rows.sort(key=lambda row: row["monthly_count"], reverse=reverse)
    return rows[:5]


class AmbulatorDoctorTopAPIView(APIView):
    @swagger_auto_schema(
        tags=["Monitor / Ambulator"],
        responses={200: AmbulatorDoctorTopSerializer(many=True)},
        manual_parameters=MONTH_PARAMS,
    )
    def get(self, request):
        period = selected_month(request)
        if isinstance(period, Response):
            return period
        start, end, day = period
        payload = AmbulatorDoctorTopSerializer(ranked_doctors(start, end, day, reverse=True), many=True).data
        return Response(
            {
                "year": start.year,
                "month": start.month,
                "date": day.isoformat(),
                "results": payload,
            },
            status=status.HTTP_200_OK,
        )


class AmbulatorDoctorBottomAPIView(APIView):
    @swagger_auto_schema(
        tags=["Monitor / Ambulator"],
        responses={200: AmbulatorDoctorTopSerializer(many=True)},
        manual_parameters=MONTH_PARAMS,
    )
    def get(self, request):
        period = selected_month(request)
        if isinstance(period, Response):
            return period
        start, end, day = period
        payload = AmbulatorDoctorTopSerializer(ranked_doctors(start, end, day, reverse=False), many=True).data
        return Response(
            {
                "year": start.year,
                "month": start.month,
                "date": day.isoformat(),
                "results": payload,
            },
            status=status.HTTP_200_OK,
        )
