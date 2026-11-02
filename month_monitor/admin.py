from django.contrib import admin
from django.forms import BaseInlineFormSet
from django.core.exceptions import ValidationError
from month_monitor.models import MonthMonitor, MonthPatient, PatientExaminationView, PatientDiagnosis, PatientLaboratory, PatienMusterView
from django.contrib.admin import ModelAdmin



class LimitMonthPatient(BaseInlineFormSet):
    def clean(self):
        super().clean()
        # count all forms that have not been marked for deletion
        count = sum(1 for form in self.forms if not self._should_delete_form(form))
        max_num = 5000 # specify your max number of images here
        if count > max_num:
            raise ValidationError(f'You can only associate up to {max_num} images with this product.')

class MonthPatientInline(admin.TabularInline):
    model = MonthPatient
    formset = LimitMonthPatient
    extra = 1
    min_num = 1
    max_num = 5000

@admin.register(MonthMonitor)
class MonthMonitorAdmin(ModelAdmin):
    inlines = [MonthPatientInline]
    list_display = ('doctor', 'appointment_date', 'patient_count')
    list_filter = ('doctor', 'appointment_date')
    search_fields = ('doctor__full_name', 'appointment_date')




class LimitPatientDiagnosis(BaseInlineFormSet):
    def clean(self):
        super().clean()
        # count all forms that have not been marked for deletion
        count = sum(1 for form in self.forms if not self._should_delete_form(form))
        max_num = 5000 # specify your max number of images here
        if count > max_num:
            raise ValidationError(f'You can only associate up to {max_num} images with this product.')


class PatientDiagnosisInline(admin.TabularInline):
    model = PatientDiagnosis
    formset = LimitPatientDiagnosis
    extra = 1
    min_num = 1
    max_num = 5000


class LimitPatientLaboratory(BaseInlineFormSet):
    def clean(self):
        super().clean()
        # count all forms that have not been marked for deletion
        count = sum(1 for form in self.forms if not self._should_delete_form(form))
        max_num = 5000 # specify your max number of images here
        if count > max_num:
            raise ValidationError(f'You can only associate up to {max_num} images with this product.')


class PatientLaboratoryInline(admin.TabularInline):
    model = PatientLaboratory
    formset = LimitPatientLaboratory
    extra = 1
    min_num = 1
    max_num = 5000


class PatienMusterInline(admin.TabularInline):
    model = PatienMusterView
    extra = 1
    min_num = 1
    max_num = 5000




@admin.register(PatientExaminationView)
class PatientExaminationViewAdmin(ModelAdmin):
    inlines = [PatientDiagnosisInline, PatienMusterInline, PatientLaboratoryInline]
    list_display = ('doctor', 'patient', 'date')
    search_fields = ('doctor__full_name__icontains', 'patient__icontains', 'date__icontains')