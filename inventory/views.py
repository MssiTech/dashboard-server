from django.db.models import Count, Q
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from monitor.pagination import PaginationList

from inventory.serializers import DeviceTypeSerializer, InventorySerializer, InventoryCrudSerializer
from inventory.models import DeviceStatus, DeviceType, Inventory


def status_value(raw):
    text = (raw or "").strip()
    if not text:
        return ""
    for key, label in DeviceStatus.choices:
        if text.casefold() in (key.casefold(), label.casefold()):
            return key
    return text


class DeviceTypeViewSet(APIView):

    @swagger_auto_schema(
        tags=["Inventory"],
        responses={200: DeviceTypeSerializer(many=True)},
    )
    def get(self, request):
        device_types = DeviceType.objects.all()
        serializer = DeviceTypeSerializer(device_types, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class InventoryListAPIView(APIView):
    pagination_class = PaginationList

    @swagger_auto_schema(
        tags=["Inventory"],
        manual_parameters=[
            openapi.Parameter("branch", openapi.IN_QUERY, description="Bo'lim id yoki nomi", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("device_status", openapi.IN_QUERY, description="Holat: new, available, repair_required, outdated, other yoki Yangi", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("page", openapi.IN_QUERY, description="Sahifa", type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter("limit", openapi.IN_QUERY, description="Sahifadagi soni", type=openapi.TYPE_INTEGER, required=False),
        ],
        responses={200: InventorySerializer(many=True)},
    )
    def get(self, request):
        inventories = Inventory.objects.select_related("device_type", "branch").order_by("-id")
        branch = (request.query_params.get("branch") or "").strip()
        if branch:
            if branch.isdigit():
                inventories = inventories.filter(branch_id=int(branch))
            else:
                inventories = inventories.filter(branch__name__icontains=branch)
        holat = status_value(request.query_params.get("device_status") or request.query_params.get("holat"))
        if holat:
            inventories = inventories.filter(device_status=holat)
        paginator = self.pagination_class()
        result = paginator.paginate_queryset(inventories, request)
        serializer = InventorySerializer(result, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


    @swagger_auto_schema(
        tags=["Inventory"],
        responses={201: InventoryCrudSerializer()},
    )
    def post(self, request):
        serializer = InventoryCrudSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InventoryDetailAPIView(APIView):
    @swagger_auto_schema(
        tags=["Inventory"],
        responses={200: InventoryCrudSerializer()},
    )
    def get(self, request, pk):
        inventory = Inventory.objects.get(id=pk)
        serializer = InventoryCrudSerializer(inventory, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        tags=["Inventory"],
        responses={200: InventoryCrudSerializer()},
    )
    def put(self, request, pk):
        inventory = Inventory.objects.get(id=pk)
        serializer = InventoryCrudSerializer(inventory, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

    @swagger_auto_schema(
        tags=["Inventory"],
        responses={204: None},
    )
    def delete(self, request, pk):
        inventory = Inventory.objects.get(id=pk)
        inventory.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
