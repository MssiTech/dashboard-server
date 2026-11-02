from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from django.forms import BaseInlineFormSet
from django.core.exceptions import ValidationError
from monitor.models import (
    Prices,
    Branches,
    Doctors,
    DoctorMonthPlan, 
    PatientReception, 
    Patients, 
    Monitoring, 
    Classification, 
    DiagnsticExamination, 
    LaboratoryExamination,
    PatientCurrentView,
    PattientCurrentDiagnosis,
    CurrentViewDiagnosis,
    CurrentViewLaboratory
)


@admin.register(Prices)
class PricesAdmin(ImportExportModelAdmin):
    list_display = ['name', 'dmed_id']
    search_fields = ['name']


@admin.register(Branches)
class BranchesAdmin(ImportExportModelAdmin):
    list_display = ['name', 'dmed_id']
    search_fields = ['name']


class LimitDoctorMonthPlan(BaseInlineFormSet):
    def clean(self):
        super().clean()
        # count all forms that have not been marked for deletion
        count = sum(1 for form in self.forms if not self._should_delete_form(form))
        max_num = 100 # specify your max number of images here
        if count > max_num:
            raise ValidationError(f'You can only associate up to {max_num} images with this product.')


class DoctorMonthPlanInline(admin.TabularInline):
    model = DoctorMonthPlan
    formset = LimitDoctorMonthPlan
    extra = 1
    min_num = 1
    max_num = 100


@admin.register(Doctors)
class DoctorsAdmin(ImportExportModelAdmin):
    inlines = [DoctorMonthPlanInline]
    readonly_fields = ['dmed_id']
    list_display = ['full_name', 'specialization', 'dmed_id', 'branch', 'polyclinic']
    search_fields = ['full_name', 'specialization', 'polyclinic']


# @admin.register(DoctorMonthPlan)
# class DoctorMonthPlanAdmin(admin.ModelAdmin):
#     list_display = ['doctor', 'year', 'month', 'bid', 'daily_limit', 'monthly_limit']
#     search_fields = ['doctor__full_name']
#     list_filter = ['year', 'month']


class LimitPatients(BaseInlineFormSet):
    def clean(self):
        super().clean()
        # count all forms that have not been marked for deletion
        count = sum(1 for form in self.forms if not self._should_delete_form(form))
        max_num = 100 # specify your max number of images here
        if count > max_num:
            raise ValidationError(f'You can only associate up to {max_num} images with this product.')


class PatientsInline(admin.TabularInline):
    model = Patients
    formset = LimitPatients
    extra = 1
    min_num = 1
    max_num = 100


@admin.register(PatientReception)
class PatientReceptionAdmin(admin.ModelAdmin):
    inlines = [PatientsInline]
    search_fields = ['doctor__full_name', 'reception_date']
    list_display = ['doctor', 'reception_count', 'reception_date']



@admin.register(Monitoring)
class MonitoringAdmin(admin.ModelAdmin):
    list_display = ['doctor', 'appointment_count', 'rezident_count', 'non_rezident_count', 'simple_count', 'examination_count', 'diagnosis_count', 'analysis_count', 'diagnostika_count', 'is_stasionary', 'date']



class LimitDiagnsticExamination(BaseInlineFormSet):
    def clean(self):
        super().clean()
        # count all forms that have not been marked for deletion
        count = sum(1 for form in self.forms if not self._should_delete_form(form))
        max_num = 100  # specify your max number of images here
        if count > max_num:
            raise ValidationError(f'You can only associate up to {max_num} images with this product.')


class DiagnsticExaminationInline(admin.TabularInline):
    model = DiagnsticExamination
    formset = LimitDiagnsticExamination
    extra = 1
    min_num = 1
    max_num = 100


class LimitLaboratoryExamination(BaseInlineFormSet):
    def clean(self):
        super().clean()
        # count all forms that have not been marked for deletion
        count = sum(1 for form in self.forms if not self._should_delete_form(form))
        max_num = 100  # specify your max number of images here
        if count > max_num:
            raise ValidationError(f'You can only associate up to {max_num} images with this product.')


class LaboratoryExaminationInline(admin.TabularInline):
    model = LaboratoryExamination
    formset = LimitLaboratoryExamination
    extra = 1
    min_num = 1
    max_num = 100


@admin.register(Classification)
class ClassificationAdmin(admin.ModelAdmin):
    inlines = [DiagnsticExaminationInline, LaboratoryExaminationInline]
    search_fields = ['title', 'name']
    list_display = ['title', 'name']


@admin.register(PatientCurrentView)
class PatientCurrentViewAdmin(admin.ModelAdmin):
    list_display = ['doctor', 'patient', 'date', 'mkb_10', 'mkb_10_name']



class LimitCurrentDiagnosis(BaseInlineFormSet):
    def clean(self):
        super().clean()
        # count all forms that have not been marked for deletion
        count = sum(1 for form in self.forms if not self._should_delete_form(form))
        max_num = 100  # specify your max number of images here
        if count > max_num:
            raise ValidationError(f'You can only associate up to {max_num} images with this product.')


class CurrentDiagnosisInline(admin.TabularInline):
    model = CurrentViewDiagnosis
    formset = LimitCurrentDiagnosis
    extra = 1
    min_num = 1
    max_num = 100


class LimitCurrentLaboratory(BaseInlineFormSet):
    def clean(self):
        super().clean()
        # count all forms that have not been marked for deletion
        count = sum(1 for form in self.forms if not self._should_delete_form(form))
        max_num = 100  # specify your max number of images here
        if count > max_num:
            raise ValidationError(f'You can only associate up to {max_num} images with this product.')


class CurrentLaboratoryInline(admin.TabularInline):
    model = CurrentViewLaboratory
    formset = LimitCurrentLaboratory
    extra = 1
    min_num = 1
    max_num = 100


@admin.register(PattientCurrentDiagnosis)
class PattientCurrentDiagnosisAdmin(admin.ModelAdmin):
    inlines = [CurrentDiagnosisInline, CurrentLaboratoryInline]
    list_display = ['doctor', 'patient', 'date', 'mkb_10', 'mkb_10_name']


# @admin.register(CurrentViewDiagnosis)
# class CurrentViewDiagnosisAdmin(admin.ModelAdmin):
#     list_display = ['patient_current_view', 'diagnosis', 'is_exists']

