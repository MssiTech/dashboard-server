from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from monitor.employe.serializers import EmployeeSerializer, EmployeUpdateSerializer, BranchSerializer
from monitor.models import Doctors, Branches, snapshot_doctor_plan
from monitor.pagination import PaginationList


class EmployeeListAPIView(APIView):
    # permission_classes = [IsAuthenticated]
    serializer_class = EmployeeSerializer
    pagination_class = PaginationList

    @swagger_auto_schema(
        tags=['Employees'],
        manual_parameters=[
            openapi.Parameter('full_name', openapi.IN_QUERY, description='Full name', type=openapi.TYPE_STRING),
            openapi.Parameter('polyclinic', openapi.IN_QUERY, description='true / false', type=openapi.TYPE_BOOLEAN, required=False),
            openapi.Parameter('page', openapi.IN_QUERY, description='Page', type=openapi.TYPE_INTEGER),
            openapi.Parameter('limit', openapi.IN_QUERY, description='Limit', type=openapi.TYPE_INTEGER),
        ],
        responses={200: EmployeeSerializer(many=True)},
    )
    def get(self, request):
        full_name = (request.query_params.get('full_name') or '').strip()
        polyclinic = (request.query_params.get('polyclinic') or '').strip().lower()
        employees = Doctors.objects.all().order_by('id')
        if full_name:
            employees = employees.filter(full_name__icontains=full_name)
        if polyclinic in ('true', '1'):
            employees = employees.filter(polyclinic=True)
        elif polyclinic in ('false', '0'):
            employees = employees.filter(polyclinic=False)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(employees, request)
        serializer = EmployeeSerializer(page, many=True, context={'request': request})

        return paginator.get_paginated_response(serializer.data)


class EmployeDetailAPIView(APIView):
    # permission_classes = [IsAuthenticated]
    serializer_class = EmployeeSerializer

    @swagger_auto_schema(
        tags=['Employees'],
        responses={200: EmployeeSerializer()},
    )
    def get(self, request, pk):
        employee = get_object_or_404(Doctors, pk=pk)
        serializer = EmployeeSerializer(employee)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        tags=['Employees'],
        request_body=EmployeUpdateSerializer,
        responses={200: EmployeeSerializer()},
    )
    def put(self, request, pk):
        employee = get_object_or_404(Doctors, pk=pk)
        serializer = EmployeUpdateSerializer(employee, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            snapshot_doctor_plan(
                employee,
                year=request.data.get("year"),
                month=request.data.get("month"),
            )
            return Response(EmployeeSerializer(employee).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BranchListAPIView(APIView):
    # permission_classes = [IsAuthenticated]
    serializer_class = BranchSerializer

    @swagger_auto_schema(
        tags=['Employees'],
        responses={200: BranchSerializer(many=True)},
    )
    def get(self, request):
        branches = Branches.objects.all().order_by('id')
        serializer = BranchSerializer(branches, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)