from rest_framework import serializers
from inventory.models import DeviceType, Inventory
from monitor.serializers import BranchSerializer, DoctorSerializer

class DeviceTypeSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = DeviceType
        fields = "__all__"

class InventorySerializer(serializers.ModelSerializer):
    device_type = DeviceTypeSerializer()
    branch = BranchSerializer()
    person = DoctorSerializer()
    
    class Meta:
        model = Inventory
        fields = "__all__"