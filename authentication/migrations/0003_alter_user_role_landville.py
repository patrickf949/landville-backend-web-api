# Rebrand: role label 'LANDVILLE ADMIN' -> 'LANDVILLE ADMIN'.
# Choices-only change (no DB schema change); keeps migration state in sync
# with the model so makemigrations --check passes.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0002_alter_user_first_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('LA', 'LANDVILLE ADMIN'),
                    ('CA', 'CLIENT ADMIN'),
                    ('BY', 'BUYER'),
                ],
                default='BY',
                max_length=2,
                verbose_name='user role',
            ),
        ),
    ]
