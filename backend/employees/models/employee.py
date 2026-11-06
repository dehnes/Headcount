from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q


class Employee(models.Model):
    class Status(models.TextChoices):
        ONBOARDING = "onboarding", "Onboarding"
        ACTIVE = "active", "Active"
        RETIRED = "retired", "Retired"
        DORMANT = "dormant", "Dormant"
        FIRED = "fired", "Fired"

    corp_id = models.PositiveIntegerField(
        "corporate ID",
        unique=True,
        validators=[MinValueValidator(1), MaxValueValidator(99999999)],
    )
    first_name = models.CharField("first name", max_length=150)
    last_name = models.CharField("last name", max_length=150)
    email = models.EmailField("email address")
    status = models.CharField(
        "employment status", max_length=20, choices=Status.choices
    )
    created_at = models.DateTimeField("created at", auto_now_add=True)
    updated_at = models.DateTimeField("updated at", auto_now=True)

    class Meta:
        verbose_name = "employee"
        verbose_name_plural = "employees"
        constraints = [
            models.CheckConstraint(
                condition=Q(corp_id__gte=1, corp_id__lte=99999999),
                name="employee_corp_id_valid_range",
            ),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
