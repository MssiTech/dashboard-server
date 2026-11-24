from django.contrib import admin
from django.forms import BaseInlineFormSet
from django.core.exceptions import ValidationError

from appeals.models import EmployeAppleas, TypeAppeals, Appeals, AppealImages



class EmployeAppleasAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone", "position", "branch", "telegram_id")
    search_fields = ("full_name", "phone", "position")
    list_filter = ("branch",)

admin.site.register(EmployeAppleas, EmployeAppleasAdmin)

class TypeAppealsAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    list_filter = ("name",)
    list_per_page = 10

admin.site.register(TypeAppeals, TypeAppealsAdmin)


class LimitAppealImages(BaseInlineFormSet):
    def clean(self):
        super().clean()
        # count all forms that have not been marked for deletion
        count = sum(1 for form in self.forms if not self._should_delete_form(form))
        max_num = 4 # specify your max number of images here
        if count > max_num:
            raise ValidationError(f'You can only associate up to {max_num} images with this product.')


class AppealImagesInline(admin.TabularInline):
    model = AppealImages
    formset = LimitAppealImages
    extra = 1
    min_num = 1
    max_num = 4



class AppealsAdmin(admin.ModelAdmin):
    inlines = [AppealImagesInline]
    list_display = ("type", "branch", "employe", "description", "is_completed", "completed_at")
    search_fields = ("type", "branch", "employe", "description", "is_completed", "completed_at")
    list_filter = ("type", "branch", "employe", "description", "is_completed", "completed_at")
    list_per_page = 10

admin.site.register(Appeals, AppealsAdmin)