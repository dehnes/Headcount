from django.db import models


class Person(models.Model):
    corp_id = models.CharField(
        max_length=20,
        unique=True,
    )
    first_name = models.CharField(
        max_length=100,
    )
    last_name = models.CharField(
        max_length=100,
    )

    class Meta:
        ordering = ("corp_id",)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.corp_id})"
