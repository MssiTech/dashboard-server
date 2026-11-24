from datetime import date, datetime

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


from monitor.models import (
    Doctors,
    Monitoring,
    Patients,
    PatientCurrentView,
    PattientCurrentDiagnosis,
)
from monitor.ambulator.serializers import (
    DoctorsSerializer,
    MonitoringSerializer,
    PatientMonitoringSerializer,
    patient_passport,
)
from monitor.pagination import PaginationList
from main import save_polyclinic_patients

class DoctorsListAPIView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Doctors.objects.all()
    serializer_class = DoctorsSerializer
    pagination_class = PaginationList
    
    @swagger_auto_schema(
        tags=["Monitor / Doctors"],
        manual_parameters=[
            openapi.Parameter('full_name', openapi.IN_QUERY, description="Shifokor ismi bo'yicha qidiruv", type=openapi.TYPE_STRING, required=False),
        ],
        responses={200: DoctorsSerializer(many=True)},
    )
    def get(self, request):
        doctors = self.get_queryset()
        full_name = (request.query_params.get('full_name') or '').strip()
        if full_name:
            doctors = doctors.filter(full_name__icontains=full_name)
        serializer = self.get_serializer(doctors, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class MonitoringListAPIView(APIView):
    # permission_classes = [IsAuthenticated]
    pagination_class = PaginationList
    
    @swagger_auto_schema(
        tags=["Monitor / Monitoring"], 
        responses={200: MonitoringSerializer(many=True)},
        manual_parameters=[
            openapi.Parameter('date', openapi.IN_QUERY, description="Sana (YYYY-MM-DD). Bo'sh bo'lsa bugungi kun", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('full_name', openapi.IN_QUERY, description="Shifokor F.I.Sh.", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('page', openapi.IN_QUERY, description="Номер страницы", type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter('limit', openapi.IN_QUERY, description="Количество элементов на странице", type=openapi.TYPE_INTEGER, required=False)
        ]
    )
    def get(self, request):
        selected_date = request.query_params.get('date') or date.today().isoformat()
        full_name = (request.query_params.get('full_name') or '').strip()

        try:
            selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'date': 'Sana YYYY-MM-DD formatida bo‘lishi kerak'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        monitoring = Monitoring.objects.filter(date=selected_date, doctor__polyclinic=True)
        if full_name:
            monitoring = monitoring.filter(doctor__full_name__icontains=full_name)
        monitoring = monitoring.order_by('-id')
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(monitoring, request)
        serializer = MonitoringSerializer(page, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class DoctorMonitoringAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Monitor / Monitoring"],
        manual_parameters=[
            openapi.Parameter('date', openapi.IN_QUERY, description="Sana (YYYY-MM-DD). Bo'sh bo'lsa bugungi kun", type=openapi.TYPE_STRING, required=False),
        ]
    )
    def get(self, request, doctor_id):
        selected_date = request.query_params.get('date') or date.today().isoformat()

        try:
            selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'date': 'Sana YYYY-MM-DD formatida bo‘lishi kerak'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        doctor = get_object_or_404(Doctors, id=doctor_id)
        patients = Patients.objects.filter(
            reception__doctor=doctor,
            reception_date=selected_date,
        ).prefetch_related(
            Prefetch(
                'patient_current_view',
                queryset=PatientCurrentView.objects.filter(date=selected_date),
            ),
            Prefetch(
                'pattientcurrentdiagnosis_set',
                queryset=PattientCurrentDiagnosis.objects.filter(
                    date=selected_date,
                ).prefetch_related('currentviewdiagnosis_set', 'currentviewlaboratory_set'),
            ),
        ).order_by('id')

        return Response(
            PatientMonitoringSerializer(patients, many=True).data,
            status=status.HTTP_200_OK,
        )


class GetPatientDoctorAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return Response(save_polyclinic_patients(), status=status.HTTP_200_OK)


class PatientDoctorsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Monitor / Patients"],
        manual_parameters=[
            openapi.Parameter('doctor_id', openapi.IN_QUERY, description="Shifokor ID", type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter('start_date', openapi.IN_QUERY, description="Boshlanish sanasi (YYYY-MM-DD). Bo'sh bo'lsa bugun", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('end_date', openapi.IN_QUERY, description="Tugash sanasi (YYYY-MM-DD). Bo'sh bo'lsa bugun", type=openapi.TYPE_STRING, required=False),
        ]
    )
    def get(self, request):
        today = date.today().isoformat()
        doctor_id = request.query_params.get('doctor_id')
        if not doctor_id:
            return Response({"date": today, "patients": []}, status=status.HTTP_200_OK)

        start_date, end_date, error = self._dates(request, today)
        if error:
            return error

        doctor = get_object_or_404(Doctors, id=doctor_id)
        patients = Patients.objects.filter(
            reception__doctor=doctor,
            reception_date__range=(start_date, end_date),
        ).prefetch_related(
            Prefetch(
                'patient_current_view',
                queryset=PatientCurrentView.objects.filter(date__range=(start_date, end_date)),
            ),
            Prefetch(
                'pattientcurrentdiagnosis_set',
                queryset=PattientCurrentDiagnosis.objects.filter(
                    date__range=(start_date, end_date),
                ).prefetch_related('currentviewdiagnosis_set', 'currentviewlaboratory_set'),
            ),
        ).order_by('reception_date', 'id')

        return Response({
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "patients": [self._patient(patient) for patient in patients],
        }, status=status.HTTP_200_OK)

    def _dates(self, request, today):
        start_raw = request.query_params.get('start_date') or today
        end_raw = request.query_params.get('end_date') or today
        try:
            start_date = datetime.strptime(start_raw, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_raw, '%Y-%m-%d').date()
        except ValueError:
            return None, None, Response(
                {'date': 'Sana YYYY-MM-DD formatida bo‘lishi kerak'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if start_date > end_date:
            return None, None, Response(
                {'date': 'start_date end_date dan katta bo‘lmasligi kerak'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return start_date, end_date, None

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