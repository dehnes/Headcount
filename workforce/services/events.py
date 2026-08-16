from django.core.exceptions import ValidationError

from workforce.enums import (
    EmploymentStatus,
    EventType,
)
from workforce.models import PersonEvent


def validate_event_history(
    event: PersonEvent,
    history: list[PersonEvent],
) -> None:
    """
    Validate an event against the existing event history
    of a person.
    """

    # ---------------------------------------------------------
    # Chronology
    # ---------------------------------------------------------

    if history:
        last_event = history[-1]

        if event.effective_date < last_event.effective_date:
            raise ValidationError(
                "Event date cannot be earlier than the last existing event."
            )

    # ---------------------------------------------------------
    # JOIN
    # ---------------------------------------------------------

    if event.event_type == EventType.JOIN and any(
        existing.event_type == EventType.JOIN for existing in history
    ):
        raise ValidationError("A person can only have one JOIN event.")

    # ---------------------------------------------------------
    # Events after EXIT
    # ---------------------------------------------------------

    if any(existing.event_type == EventType.EXIT for existing in history):
        raise ValidationError("No events are allowed after EXIT.")

    # ---------------------------------------------------------
    # Employment status
    # ---------------------------------------------------------

    if event.event_type == EventType.EMPLOYMENT_STATUS_CHANGE:
        _validate_employment_status_change(
            event,
            history,
        )


def _validate_employment_status_change(
    event: PersonEvent,
    history: list[PersonEvent],
) -> None:

    if event.employment_status is None:
        raise ValidationError("Employment status is required.")

    previous_status = None

    for existing in reversed(history):
        if existing.employment_status is not None:
            previous_status = existing.employment_status
            break

    if previous_status is None:
        return

    if (
        previous_status == EmploymentStatus.PERMANENT
        and event.employment_status == EmploymentStatus.TEMPORARY
    ):
        raise ValidationError(
            "Employment status cannot change from PERMANENT to TEMPORARY."
        )


def add_event(event: PersonEvent) -> PersonEvent:
    """
    Validate and persist a PersonEvent.
    """

    history = list(
        PersonEvent.objects.filter(person=event.person).order_by("effective_date", "id")
    )

    validate_event_history(
        event,
        history,
    )

    event.full_clean()
    event.save()

    return event
