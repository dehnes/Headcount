import django.core.validators
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0002_remove_employee_employee_corp_id_eight_digits_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="employee",
            options={"verbose_name": "employee", "verbose_name_plural": "employees"},
        ),
        migrations.AddField(
            model_name="employee",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True,
                default=django.utils.timezone.now,
                verbose_name="created at",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="employee",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True,
                default=django.utils.timezone.now,
                verbose_name="updated at",
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="employee",
            name="corp_id",
            field=models.PositiveIntegerField(
                unique=True,
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(99999999),
                ],
                verbose_name="corporate ID",
            ),
        ),
        migrations.AlterField(
            model_name="employee",
            name="first_name",
            field=models.CharField(max_length=150, verbose_name="first name"),
        ),
        migrations.AlterField(
            model_name="employee",
            name="last_name",
            field=models.CharField(max_length=150, verbose_name="last name"),
        ),
        migrations.AlterField(
            model_name="employee",
            name="email",
            field=models.EmailField(max_length=254, verbose_name="email address"),
        ),
        migrations.AlterField(
            model_name="employee",
            name="status",
            field=models.CharField(
                choices=[
                    ("onboarding", "Onboarding"),
                    ("active", "Active"),
                    ("retired", "Retired"),
                    ("dormant", "Dormant"),
                    ("fired", "Fired"),
                ],
                max_length=20,
                verbose_name="employment status",
            ),
        ),
    ]
