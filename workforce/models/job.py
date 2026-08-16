from django.db import models


class Job(models.Model):
    code = models.CharField(
        max_length=50,
        unique=True,
    )
    name = models.CharField(
        max_length=200,
    )

    class Meta:
        ordering = ("code",)

    def __str__(self):
        return f"{self.code} - {self.name}"
