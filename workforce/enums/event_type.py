from django.db import models


class EventType(models.TextChoices):
    JOIN = "JOIN", "Join"
    JOB_CHANGE = "JOB_CHANGE", "Job Change"
    TRANSFER = "TRANSFER", "Transfer"
    LOCATION_CHANGE = "LOCATION_CHANGE", "Location Change"
    EMPLOYMENT_STATUS_CHANGE = (
        "EMPLOYMENT_STATUS_CHANGE",
        "Employment Status Change",
    )
    LEAVE_END = "LEAVE_END", "Leave End"
    EXIT = "EXIT", "Exit"
