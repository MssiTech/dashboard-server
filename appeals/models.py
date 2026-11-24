from django.db import models
from monitor.models import Branches


class EmployeAppleas(models.Model):
    full_name = models.CharField(max_length=255, verbose_name="ФИО")
    phone = models.CharField(max_length=255, unique=True, verbose_name="Телефон")
    position = models.CharField(max_length=255, verbose_name="Должность")
    branch = models.ForeignKey(Branches, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Филиал")
    telegram_id = models.BigIntegerField(unique=True, null=True, blank=True, verbose_name="Telegram ID")

    def __str__(self):
        return self.full_name

    class Meta:
        db_table = "employe_appleas"
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"


class TypeAppeals(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название")

    def __str__(self):
        return self.name

    class Meta:
        db_table = "type_appeals"
        verbose_name = "Тип обращения"
        verbose_name_plural = "Типы обращений"


class Appeals(models.Model):
    type = models.ForeignKey(TypeAppeals, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Тип обращения")
    branch = models.ForeignKey(Branches, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Филиал")
    employe = models.ForeignKey(EmployeAppleas, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Сотрудник")
    description = models.TextField(null=True, blank=True, verbose_name="Описание")
    is_completed = models.BooleanField(default=False, verbose_name="Выполнено")
    replay_admin = models.TextField(null=True, blank=True, verbose_name="Ответ администратора")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата выполнения")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    def __str__(self):
        return self.employe.full_name

    class Meta:
        db_table = "appeals"
        verbose_name = "Обращение"
        verbose_name_plural = "Обращения"


class AppealImages(models.Model):
    appeal = models.ForeignKey(Appeals, on_delete=models.CASCADE, null=True, blank=True, related_name="images_appeal", verbose_name="Обращение")
    image = models.ImageField(upload_to="appeals/images/", null=True, blank=True, verbose_name="Изображение")

    class Meta:
        db_table = "appeal_images"
        verbose_name = "Изображение обращения"
        verbose_name_plural = "Изображения обращения"