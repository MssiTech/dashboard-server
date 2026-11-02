from calendar import c
from django.db import models
from monitor.models import Doctors, PatientReception, Classification


class MonthMonitor(models.Model):
    doctor = models.ForeignKey(Doctors, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Врач")
    appointment_date = models.DateField(null=True, blank=True, verbose_name="Дата")
    patient_count = models.IntegerField(null=True, blank=True, verbose_name="Количество пациентов")
    is_branch = models.BooleanField(default=False, null=True, blank=True, verbose_name="Филиал")

    class Meta:
        verbose_name = "Месячный мониторинг"
        verbose_name_plural = "Месячные мониторинги"


class MonthPatient(models.Model):
    month_monitor = models.ForeignKey(MonthMonitor, on_delete=models.CASCADE, null=True, blank=True, related_name="month_patient", verbose_name="Месячный мониторинг")
    is_rezident = models.BooleanField(default=False, null=True, blank=True, verbose_name="Резident")
    branch = models.CharField(max_length=255, null=True, blank=True, verbose_name="Филиал")
    start_date = models.DateField(null=True, blank=True, verbose_name="Дата начала")
    end_date = models.DateField(null=True, blank=True, verbose_name="Дата окончания")
    patient = models.CharField(max_length=255, null=True, blank=True, verbose_name="Пациент")
    uuid = models.CharField(max_length=255, null=True, blank=True, verbose_name="UUID пациента")
    is_branch = models.BooleanField(default=False, null=True, blank=True, verbose_name="Филиал")
    reception_date = models.DateField(null=True, blank=True, verbose_name="Дата приема")


    def __str__(self):
        return f"{self.patient}"

    class Meta:
        db_table = "month_patient"
        verbose_name = "Пациент месяца"
        verbose_name_plural = "Пациенты месяца"


class PatientExaminationView(models.Model):
    doctor = models.ForeignKey(Doctors, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Врач")
    patient = models.ForeignKey(MonthPatient, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Пациент")
    date = models.DateField(null=True, blank=True, verbose_name="Дата")
    mkb_10 = models.ForeignKey(Classification, on_delete=models.CASCADE, null=True, blank=True, verbose_name="МКБ-10")
    mkb_10_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Название МКБ-10")

    class Meta:
        db_table = "patient_examination"
        verbose_name = "Осмотр пациента"
        verbose_name_plural = "Осмотры пациента"


class PatienMusterView(models.Model):
    patient_examination = models.ForeignKey(PatientExaminationView, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Осмотр пациента")
    doctor_full_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="ФИО врача")
    date = models.DateField(null=True, blank=True, verbose_name="Дата")
    mkb_10 = models.ForeignKey(Classification, on_delete=models.CASCADE, null=True, blank=True, verbose_name="МКБ-10")
    mkb_10_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Название МКБ-10")

    class Meta:
        db_table = "patient_muster"
        verbose_name = "Диагноз пациента"
        verbose_name_plural = "Диагнозы пациента"


class PatientDiagnosis(models.Model):
    patient_diagnosis = models.ForeignKey(PatientExaminationView, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Диагноз пациента")
    diagnosis = models.CharField(max_length=255, null=True, blank=True, verbose_name="Диагноз")
    is_exists = models.BooleanField(default=False, null=True, blank=True, verbose_name="Существует")

    class Meta:
        db_table = "patient_diagnosis"
        verbose_name = "Диагноз пациента"
        verbose_name_plural = "Диагнозы пациента"


class PatientLaboratory(models.Model):
    patient_current_view = models.ForeignKey(PatientExaminationView, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Текущий вид пациента")
    laboratory = models.CharField(max_length=255, null=True, blank=True, verbose_name="Лабораторное")
    is_exists = models.BooleanField(default=False, null=True, blank=True, verbose_name="Существует")

    class Meta:
        db_table = "patient_laboratory"
        verbose_name = "Исследование пациента"
        verbose_name_plural = "Исследования пациента"

