from django.db.models import Count
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from monitor.branch_monitor.serializers import BranchReceptionSerializer
from monitor.district_monitor.views import DATE_PARAMS, query_dates
from monitor.models import Patients


def polyclinic_branch_patients(request):
    period = query_dates(request)
    if isinstance(period, Response):
        return period, None
    start, end = period
    patients = Patients.objects.filter(
        is_stasionary=False,
        reception_date__range=(start, end),
        reception__doctor__polyclinic=True,
        reception__doctor__branch_id__isnull=False,
    )
    return (start, end), patients


class BranchReceptionListAPIView(APIView):
    # permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Monitor / Branch"],
        responses={200: BranchReceptionSerializer(many=True)},
        manual_parameters=DATE_PARAMS,
    )
    def get(self, request):
        period, patients = polyclinic_branch_patients(request)
        if isinstance(period, Response):
            return period
        rows = (
            patients.values("reception__doctor__branch_id", "reception__doctor__branch__name")
            .annotate(count=Count("id"))
            .order_by("-count", "reception__doctor__branch__name")
        )
        data = [
            {
                "id": row["reception__doctor__branch_id"],
                "branch": row["reception__doctor__branch__name"] or "",
                "count": row["count"],
            }
            for row in rows
        ]
        return Response(BranchReceptionSerializer(data, many=True).data, status=status.HTTP_200_OK)
