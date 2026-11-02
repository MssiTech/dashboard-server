from datetime import date

from django.db import migrations, models
import django.db.models.deletion


def backfill_current_month_plans(apps, schema_editor):
    Doctors = apps.get_model("monitor", "Doctors")
    DoctorMonthPlan = apps.get_model("monitor", "DoctorMonthPlan")
    today = date.today()
    for doctor in Doctors.objects.all():
        if not doctor.bid and doctor.daily_limit in (None, "", "0") and doctor.monthly_limit in (None, "", "0"):
            continue
        DoctorMonthPlan.objects.update_or_create(
            doctor=doctor,
            year=today.year,
            month=today.month,
            defaults={
                "bid": doctor.bid,
                "daily_limit": doctor.daily_limit,
                "monthly_limit": doctor.monthly_limit,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("monitor", "0031_doctors_time_count_patient_doctors_work_normal_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="DoctorMonthPlan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("year", models.IntegerField(verbose_name="Год")),
                ("month", models.IntegerField(verbose_name="Месяц")),
                ("bid", models.CharField(blank=True, max_length=255, null=True, verbose_name="занимаемые ставки")),
                ("daily_limit", models.CharField(blank=True, max_length=255, null=True, verbose_name="кол-во отработ.  дней")),
                ("monthly_limit", models.CharField(blank=True, max_length=255, null=True, verbose_name="план")),
                ("doctor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="month_plans", to="monitor.doctors", verbose_name="Врач")),
            ],
            options={
                "verbose_name": "План врача за месяц",
                "verbose_name_plural": "Планы врачей за месяц",
                "db_table": "doctor_month_plans",
                "unique_together": {("doctor", "year", "month")},
            },
        ),
        migrations.RunPython(backfill_current_month_plans, migrations.RunPython.noop),
    ]
