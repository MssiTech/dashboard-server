from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0019_alter_classification_title_and_more'),
    ]

    operations = [
        migrations.DeleteModel(
            name='PattientViewDiagnostic',
        ),
        migrations.DeleteModel(
            name='PattientViewLaboratory',
        ),
    ]
