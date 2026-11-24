from django.urls import path
from inventory.views import DeviceTypeViewSet, InventoryListAPIView, InventoryDetailAPIView


urlpatterns = [
    path("device-type/", DeviceTypeViewSet.as_view(), name="device-type"),
    path("inventory/", InventoryListAPIView.as_view(), name="inventory"),
    path("inventory/<int:pk>/", InventoryDetailAPIView.as_view(), name="inventory-detail"),


]