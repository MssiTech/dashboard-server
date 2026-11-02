from datetime import date

from django.db import models

class Prices(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Название")
    dmed_id = models.CharField(max_length=255, unique=True, null=True, blank=True, verbose_name="ID DMED")

    def __str__(self):
        return self.name
    
    class Meta:
        db_table = "prices"
        verbose_name = "01. Цена"
        verbose_name_plural = "01. Цены"


class Branches(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Название")
    dmed_id = models.CharField(max_length=255, unique=True, null=True, blank=True, verbose_name="ID DMED")

    def __str__(self):
        return self.name
    
    class Meta:
        db_table = "branches"
        verbose_name = "02. Филиал"
        verbose_name_plural = "02. Филиалы"


class Doctors(models.Model):
    dmed_id = models.CharField(max_length=255, unique=True, null=True, blank=True, verbose_name="ID врача")
    full_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="ФИО врача")
    branch = models.ForeignKey(Branches, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Филиал")
    specialization = models.CharField(max_length=255, null=True, blank=True, verbose_name="Специализация врача")
    polyclinic = models.BooleanField(default=False, null=True, blank=True, verbose_name="Поликлиника")
    bid = models.CharField(max_length=255, null=True, blank=True, verbose_name="занимаемые ставки")
    daily_limit = models.CharField(max_length=255, null=True, blank=True, verbose_name="кол-во отработ.  дней")
    monthly_limit = models.CharField(max_length=255, null=True, blank=True, verbose_name="план")
    time_count_patient = models.CharField(max_length=255, null=True, blank=True, verbose_name="кол-во пациентов в час")
    work_normal = models.CharField(max_length=255, null=True, blank=True, verbose_name="нормальный график")

    def __str__(self):
        return self.full_name

    class Meta:
        db_table = "doctors"
        verbose_name = "03. Врач"
        verbose_name_plural = "03. Врачи"


class DoctorMonthPlan(models.Model):
    doctor = models.ForeignKey(Doctors, on_delete=models.CASCADE, related_name="month_plans", verbose_name="Врач")
    year = models.IntegerField(verbose_name="Год")
    month = models.IntegerField(verbose_name="Месяц")
    bid = models.CharField(max_length=255, null=True, blank=True, verbose_name="занимаемые ставки")
    daily_limit = models.CharField(max_length=255, null=True, blank=True, verbose_name="кол-во отработ.  дней")
    monthly_limit = models.CharField(max_length=255, null=True, blank=True, verbose_name="план")

    def __str__(self):
        name = self.doctor.full_name if self.doctor_id else ""
        return f"{name} {self.year}-{self.month:02d}"

    class Meta:
        db_table = "doctor_month_plans"
        unique_together = ("doctor", "year", "month")
        verbose_name = "План врача за месяц"
        verbose_name_plural = "Планы врачей за месяц"


def snapshot_doctor_plan(doctor, year=None, month=None):
    today = date.today()
    year = int(year) if year not in (None, "") else today.year
    month = int(month) if month not in (None, "") else today.month
    DoctorMonthPlan.objects.update_or_create(
        doctor=doctor,
        year=year,
        month=month,
        defaults={
            "bid": doctor.bid,
            "daily_limit": doctor.daily_limit,
            "monthly_limit": doctor.monthly_limit,
        },
    )


class Classification(models.Model):
    title = models.CharField(max_length=800, null=True, blank=True, verbose_name="Заголовок")
    name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Название")

    class Meta:
        db_table = "classification"
        verbose_name = "04. МКБ-10"
        verbose_name_plural = "04. МКБ-10"


class DiagnsticExamination(models.Model):
    classification = models.ForeignKey(Classification, on_delete=models.CASCADE, null=True, blank=True, related_name="diagnostic_examination", verbose_name="Классификация")
    name = models.CharField(max_length=800, null=True, blank=True, verbose_name="Название")
    
    class Meta:
        db_table = "diagnostic_examination"
        verbose_name = "Диагностическое исследование МКБ-10"
        verbose_name_plural = "Диагностические исследования МКБ-10"


class LaboratoryExamination(models.Model):
    classification = models.ForeignKey(Classification, on_delete=models.CASCADE, null=True, blank=True, related_name="laboratory_examination", verbose_name="Классификация")
    name = models.CharField(max_length=800, null=True, blank=True, verbose_name="Название")
    
    class Meta:
        db_table = "laboratory_examination"
        verbose_name = "Лабораторное исследование МКБ-10"
        verbose_name_plural = "Лабораторные исследования МКБ-10"


class PatientReception(models.Model):
    doctor = models.ForeignKey(Doctors, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Врач")
    reception_count = models.IntegerField(default=0, verbose_name="Количество приемов")
    reception_date = models.DateField(null=True, blank=True, verbose_name="Дата приема")

    class Meta:
        db_table = "patient_receptions"
        verbose_name = "05. Врач - Пациент"
        verbose_name_plural = "05. Врач - Пациент"


class Patients(models.Model):
    reception = models.ForeignKey(PatientReception, on_delete=models.CASCADE, null=True, blank=True, related_name="patients", verbose_name="Прием пациента")
    patient = models.CharField(max_length=255, null=True, blank=True, verbose_name="Пациент")
    uuid = models.CharField(max_length=255, null=True, blank=True, verbose_name="UUID пациента")
    region = models.CharField(max_length=255, null=True, blank=True, verbose_name="Область")
    city = models.CharField(max_length=255, null=True, blank=True, verbose_name="Город/Район")
    neighborhood = models.CharField(max_length=255, null=True, blank=True, verbose_name="Адрес")
    polyclinic = models.CharField(max_length=255, null=True, blank=True, verbose_name="Поликлиника")
    phone = models.CharField(max_length=255, null=True, blank=True, verbose_name="Телефон")
    birth_date = models.DateField(null=True, blank=True, verbose_name="Дата рождения")
    passport_series = models.CharField(max_length=255, null=True, blank=True, verbose_name="Серия паспорта")
    inn = models.CharField(max_length=255, null=True, blank=True, verbose_name="ИНН")
    branch = models.ForeignKey(Branches, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Филиал")
    is_stasionary = models.BooleanField(default=False, null=True, blank=True, verbose_name="Стационарный пациент")
    price_type = models.CharField(max_length=32, null=True, blank=True, verbose_name="Резидент")
    start_date = models.DateField(null=True, blank=True, verbose_name="Дата начала стационара")
    end_date = models.DateField(null=True, blank=True, verbose_name="Дата окончания стационара")
    reception_date = models.DateField(null=True, blank=True, verbose_name="Дата приема")

    class Meta:
        db_table = "patients"
        verbose_name = "Пациент - Прием"
        verbose_name_plural = "Пациент - Прием"


class PatientCurrentView(models.Model):
    doctor = models.ForeignKey(Doctors, on_delete=models.CASCADE, null=True, blank=True, related_name="patient_current_view", verbose_name="Врач")
    patient = models.ForeignKey(Patients, on_delete=models.CASCADE, null=True, blank=True, related_name="patient_current_view", verbose_name="Пациент")
    branch = models.ForeignKey(Branches, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Филиал")
    date = models.DateField(null=True, blank=True, verbose_name="Дата")
    examiner_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Врач осмотра")
    mkb_10 = models.ForeignKey(Classification, on_delete=models.CASCADE, null=True, blank=True, related_name="patient_current_view", verbose_name="МКБ-10")
    mkb_10_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Название МКБ-10")

    class Meta:
        db_table = "patient_current_view"
        verbose_name = "Осмотры"
        verbose_name_plural = "Осмотры"


class PattientCurrentDiagnosis(models.Model):
    doctor = models.ForeignKey(Doctors, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Врач")
    patient = models.ForeignKey(Patients, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Пациент")
    date = models.DateField(null=True, blank=True, verbose_name="Дата")
    mkb_10 = models.ForeignKey(Classification, on_delete=models.CASCADE, null=True, blank=True, verbose_name="МКБ-10")
    mkb_10_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Название МКБ-10")

    class Meta:
        db_table = "pattient_current_diagnosis"
        verbose_name = "Диагноз пациента"
        verbose_name_plural = "Диагнозы пациента"


class CurrentViewDiagnosis(models.Model):
    patient_current_view = models.ForeignKey(PattientCurrentDiagnosis, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Текущий вид пациента")
    diagnosis = models.CharField(max_length=255, null=True, blank=True, verbose_name="Диагноз")
    is_exists = models.BooleanField(default=False, null=True, blank=True, verbose_name="Существует")

    class Meta:
        db_table = "current_view_diagnosis"
        verbose_name = "Диагноз пациента"
        verbose_name_plural = "Диагнозы пациента"


class CurrentViewLaboratory(models.Model):
    patient_current_view = models.ForeignKey(PattientCurrentDiagnosis, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Текущий вид пациента")
    laboratory = models.CharField(max_length=255, null=True, blank=True, verbose_name="Лабораторное")
    is_exists = models.BooleanField(default=False, null=True, blank=True, verbose_name="Существует")

    class Meta:
        db_table = "current_view_laboratory"
        verbose_name = "Исследование пациента"
        verbose_name_plural = "Исследования пациента"


class Monitoring(models.Model):
    doctor = models.ForeignKey(Doctors, on_delete=models.CASCADE, null=True, blank=True, related_name="monitoring", verbose_name="Врач")
    branch = models.ForeignKey(Branches, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Филиал")
    appointment_count = models.IntegerField(default=0, null=True, blank=True, verbose_name="Приёмы")
    current_view_count = models.IntegerField(default=0, null=True, blank=True, verbose_name="Текущие Осмотры")
    rezident_count = models.IntegerField(default=0, null=True, blank=True, verbose_name="Резидентов")
    non_rezident_count = models.IntegerField(default=0, null=True, blank=True, verbose_name="Нерезидентов")
    simple_count = models.IntegerField(default=0, null=True, blank=True, verbose_name="Простые")
    examination_count = models.IntegerField(default=0, null=True, blank=True, verbose_name="Осмотры")    
    diagnosis_count = models.IntegerField(default=0, null=True, blank=True, verbose_name="Диагнозы")
    analysis_count = models.IntegerField(default=0, null=True, blank=True, verbose_name="Анализы")
    diagnostika_count = models.IntegerField(default=0, null=True, blank=True, verbose_name="Диагностика")
    is_stasionary = models.BooleanField(default=False, null=True, blank=True, verbose_name="Стационарный пациент")
    date = models.DateField(null=True, blank=True, verbose_name="Дата")

    class Meta:
        db_table = "monitoring"
        verbose_name = "06. Мониторинг"
        verbose_name_plural = "06. Мониторинг"