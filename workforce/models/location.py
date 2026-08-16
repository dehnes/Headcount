from django.db import models


class Location(models.Model):
    code = models.CharField(
        max_length=20,
        unique=True,
    )
    name = models.CharField(
        max_length=200,
    )

    class Meta:
        ordering = ("code",)

    def __str__(self):
        return f"{self.code} - {self.name}"
