from rest_framework import serializers
from inventory.models import DeviceType, Inventory
from monitor.month_monitor.serializers import BranchMonitoringSerializer, StationaryDoctorSerializer

class DeviceTypeSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = DeviceType
        fields = "__all__"

class InventorySerializer(serializers.ModelSerializer):
    device_type = DeviceTypeSerializer()
    branch = serializers.CharField()
    device_status = serializers.CharField(source="get_device_status_display")
    
    class Meta:
        model = Inventory
        fields = "__all__"


class InventoryCrudSerializer(serializers.ModelSerializer):

    class Meta:
        model = Inventory
        fields = ["name", "device_type", "branch", "person", "serial_number", "description", "year_manufacture", "device_status", "image", "room"]