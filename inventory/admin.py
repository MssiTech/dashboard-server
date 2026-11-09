from django.contrib import admin
from inventory.models import DeviceType, Inventory

@admin.register(DeviceType)
class DeviceTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "model", "serial")
    search_fields = ("name", "model", "serial")
    list_filter = ("name", "model", "serial")

@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ("name", "device_type", "branch", "person", "serial_number", "year_manufacture", "room")
    search_fields = ("name", "device_type", "branch", "person", "serial_number", "year_manufacture", "room")