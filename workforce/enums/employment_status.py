from django.db import models


class EmploymentStatus(models.TextChoices):
    TEMPORARY = "TEMPORARY", "Temporary"
    PERMANENT = "PERMANENT", "Permanent"
