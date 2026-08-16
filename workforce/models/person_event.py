from django.db import models

from workforce.enums import (
    EmploymentStatus,
    EventType,
    LeaveType,
)


class PersonEvent(models.Model):
    person = models.ForeignKey(
        "workforce.Person",
        on_delete=models.PROTECT,
        related_name="events",
    )

    effective_date = models.DateField()

    event_type = models.CharField(
        max_length=50,
        choices=EventType,
    )

    job = models.ForeignKey(
        "workforce.Job",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="person_events",
    )

    location = models.ForeignKey(
        "workforce.Location",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="person_events",
    )

    department = models.ForeignKey(
        "workforce.Department",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="person_events",
    )

    employment_status = models.CharField(
        max_length=20,
        choices=EmploymentStatus,
        null=True,
        blank=True,
    )

    leave_type = models.CharField(
        max_length=50,
        choices=LeaveType,
        null=True,
        blank=True,
    )

    notes = models.TextField(
        null=True,
        blank=True,
    )

    fte = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = (
            "effective_date",
            "id",
        )

    def __str__(self):
        return f"{self.person.corp_id} - {self.event_type} - {self.effective_date}"
