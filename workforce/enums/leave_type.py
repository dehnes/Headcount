from django.db import models


class LeaveType(models.TextChoices):
    PARENTAL = "PARENTAL", "Parental Leave"
    SABBATICAL = "SABBATICAL", "Sabbatical"
