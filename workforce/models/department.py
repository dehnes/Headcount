from django.db import models


class Department(models.Model):
    siglum = models.CharField(
        max_length=50,
        unique=True,
    )
    name = models.CharField(
        max_length=200,
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )

    class Meta:
        ordering = ("siglum",)

    def __str__(self):
        return f"{self.siglum} - {self.name}"
