from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("appeals", "0002_alter_employeappleas_options_appeals_replay_admin"),
    ]

    operations = [
        migrations.AddField(
            model_name="employeappleas",
            name="telegram_id",
            field=models.BigIntegerField(blank=True, null=True, unique=True, verbose_name="Telegram ID"),
        ),
        migrations.AlterField(
            model_name="employeappleas",
            name="phone",
            field=models.CharField(max_length=255, unique=True, verbose_name="Телефон"),
        ),
    ]
