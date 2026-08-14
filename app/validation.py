from .models import Department, EmploymentStatus, EventType, Job, Location, PersonEvent


def validate_event(event: PersonEvent) -> None:
    """
    Validate the structural requirements of a PersonEvent.

    Raises:
        ValueError: If the event is invalid.
    """

    if not event.corp_id:
        raise ValueError("corp_id is required.")

    if event.event_type == EventType.JOIN:
        _require(
            event.job_code,
            "JOIN requires a job.",
        )
        _require(
            event.location_code,
            "JOIN requires a location.",
        )
        _require(
            event.department_siglum,
            "JOIN requires a department.",
        )
        _require(
            event.employment_status,
            "JOIN requires employment_status.",
        )

    elif event.event_type == EventType.JOB_CHANGE:
        _require(
            event.job_code,
            "JOB_CHANGE requires a job.",
        )

    elif event.event_type == EventType.TRANSFER:
        _require(
            event.department_siglum,
            "TRANSFER requires a department.",
        )

    elif event.event_type == EventType.LOCATION_CHANGE:
        _require(
            event.location_code,
            "LOCATION_CHANGE requires a location.",
        )

    elif event.event_type == EventType.EMPLOYMENT_STATUS_CHANGE:
        _require(
            event.employment_status,
            "EMPLOYMENT_STATUS_CHANGE requires employment_status.",
        )

    elif event.event_type == EventType.LEAVE_START:
        _require(
            event.leave_type,
            "LEAVE_START requires leave_type.",
        )

    elif event.event_type == EventType.LEAVE_END or event.event_type == EventType.EXIT:
        pass


def _require(value: object, message: str) -> None:
    if value is None or value == "":
        raise ValueError(message)


def validate_event_references(
    event: PersonEvent,
    jobs: dict[str, Job],
    locations: dict[str, Location],
    departments: dict[str, Department],
) -> None:
    """
    Validate that all referenced master data exists.
    """

    if event.job_code is not None and event.job_code not in jobs:
        raise ValueError(f"Job '{event.job_code}' does not exist.")

    if event.location_code is not None and event.location_code not in locations:
        raise ValueError(f"Location '{event.location_code}' does not exist.")

    if (
        event.department_siglum is not None
        and event.department_siglum not in departments
    ):
        raise ValueError(f"Department '{event.department_siglum}' does not exist.")


def validate_event_history(
    event: PersonEvent,
    history: list[PersonEvent],
) -> None:
    """
    Validate an event against the existing history of a person.
    """

    if not history:
        if event.event_type != EventType.JOIN:
            raise ValueError("The first event for a person must be JOIN.")

        return

    # Events müssen chronologisch sein.
    latest_event = history[-1]

    if event.effective_date < latest_event.effective_date:
        raise ValueError(
            "Event effective_date cannot be before the latest existing event."
        )

    # JOIN darf nur einmal vorkommen.
    if event.event_type == EventType.JOIN and any(
        existing.event_type == EventType.JOIN for existing in history
    ):
        raise ValueError("A person can only have one JOIN event.")

    # Nach EXIT darf nichts mehr passieren.
    if any(existing.event_type == EventType.EXIT for existing in history):
        raise ValueError("No events are allowed after EXIT.")

    # LEAVE_END benötigt eine aktive Leave.
    if event.event_type == EventType.LEAVE_END:
        leave_active = False

        for existing in history:
            if existing.event_type == EventType.LEAVE_START:
                leave_active = True

            elif existing.event_type == EventType.LEAVE_END:
                leave_active = False

        if not leave_active:
            raise ValueError("LEAVE_END requires an active leave.")

    # Employment Status darf sich nur von TEMP nach PERMANENT ändern.
    if event.event_type == EventType.EMPLOYMENT_STATUS_CHANGE:
        current_employment_status = None

        for existing in history:
            if (
                existing.event_type == EventType.JOIN
                or existing.event_type == EventType.EMPLOYMENT_STATUS_CHANGE
            ):
                current_employment_status = existing.employment_status

        if current_employment_status == event.employment_status:
            raise ValueError("Employment status has not changed.")

        if (
            current_employment_status == EmploymentStatus.PERMANENT
            and event.employment_status == EmploymentStatus.TEMP
        ):
            raise ValueError("Employment status cannot change from PERMANENT to TEMP.")

    if event.event_type == EventType.FTE_CHANGE:
        if event.fte is None:
            raise ValueError("FTE_CHANGE requires fte.")

        if event.fte < 0:
            raise ValueError("FTE must be greater or equals than 0.")

        if event.fte > 1:
            raise ValueError("FTE cannot exceed 1.")

        current_fte = None

        for existing in history:
            if (
                existing.event_type == EventType.JOIN
                or existing.event_type == EventType.FTE_CHANGE
            ):
                current_fte = existing.fte

        if current_fte == event.fte:
            raise ValueError("FTE has not changed.")
