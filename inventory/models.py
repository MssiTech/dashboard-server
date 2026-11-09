from django.db import models
from monitor.models import Branches, Doctors


class DeviceType(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название")
    model = models.CharField(max_length=255, null=True, blank=True, verbose_name="Модель")
    serial = models.CharField(max_length=255, null=True, blank=True, verbose_name="Серийный")
    description = models.TextField(verbose_name="Описание", null=True, blank=True)

    class Meta:
        db_table = "device_type"
        verbose_name = "Тип устройства"
        verbose_name_plural = "Типы устройств"

    def __str__(self):
        return self.name


class Inventory(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название")
    device_type = models.ForeignKey(DeviceType, on_delete=models.CASCADE, verbose_name="Тип устройства")
    branch = models.ForeignKey(Branches, on_delete=models.CASCADE, verbose_name="Филиал")
    person = models.ForeignKey(Doctors, on_delete=models.CASCADE, verbose_name="Врач")
    serial_number = models.CharField(max_length=255, verbose_name="Серийный номер")
    description = models.TextField(verbose_name="Описание")
    year_manufacture = models.DateField(verbose_name="Год производства")
    room = models.CharField(max_length=255, null=True, blank=True, verbose_name="Комната")

    def __str__(self):
        return self.name

    class Meta:
        db_table = "inventory"
        verbose_name = "Инвентарь"
        verbose_name_plural = "Инвентарь"