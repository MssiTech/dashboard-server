from django.db.models import Count, Q
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class InventoryListAPIView(APIView):
    @swagger_auto_schema(
        tags=["Inventory"],
        responses={200: InventorySerializer(many=True)},
    )
    def get(self, request):
        return Response(status=status.HTTP_200_OK)

