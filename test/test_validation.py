from datetime import date

import pytest

from app.models import (
    Department,
    EmploymentStatus,
    EventType,
    Job,
    Location,
    PersonEvent,
)
from app.validation import (
    validate_event,
    validate_event_history,
    validate_event_references,
)


def test_job_change_requires_job():
    event = PersonEvent(
        id=None,
        corp_id="D12345",
        effective_date=date(2024, 1, 1),
        event_type=EventType.JOB_CHANGE,
    )

    with pytest.raises(
        ValueError,
        match="JOB_CHANGE requires a job.",
    ):
        validate_event(event)


def test_transfer_requires_department():
    event = PersonEvent(
        id=None,
        corp_id="D12345",
        effective_date=date(2024, 1, 1),
        event_type=EventType.TRANSFER,
    )

    with pytest.raises(
        ValueError,
        match="TRANSFER requires a department.",
    ):
        validate_event(event)


def test_join_requires_job():
    event = PersonEvent(
        id=None,
        corp_id="D12345",
        effective_date=date(2022, 1, 1),
        event_type=EventType.JOIN,
        location_code="HAM",
        department_siglum="ASOSB",
        employment_status=EmploymentStatus.TEMP,
    )

    with pytest.raises(
        ValueError,
        match="JOIN requires a job.",
    ):
        validate_event(event)


def test_valid_job_change():
    event = PersonEvent(
        id=None,
        corp_id="D12345",
        effective_date=date(2024, 1, 1),
        event_type=EventType.JOB_CHANGE,
        job_code="JOB_B",
    )

    validate_event(event)


def test_location_change_requires_location():
    event = PersonEvent(
        id=None,
        corp_id="D12345",
        effective_date=date(2023, 1, 1),
        event_type=EventType.LOCATION_CHANGE,
        location_code=None,
    )

    with pytest.raises(
        ValueError,
        match="LOCATION_CHANGE requires a location.",
    ):
        validate_event(event)


def test_leave_start_requires_leave_type():
    event = PersonEvent(
        id=None,
        corp_id="D12345",
        effective_date=date(2025, 7, 1),
        event_type=EventType.LEAVE_START,
        leave_type=None,
    )

    with pytest.raises(
        ValueError,
        match="LEAVE_START requires leave_type",
    ):
        validate_event(event)


def test_valid_join():
    event = PersonEvent(
        id=None,
        corp_id="D12345",
        effective_date=date(2022, 1, 1),
        event_type=EventType.JOIN,
        job_code="JOB_A",
        location_code="HAM",
        department_siglum="ASOSB",
        employment_status=EmploymentStatus.TEMP,
    )

    validate_event(event)


def test_job_reference_must_exist():
    event = PersonEvent(
        id=None,
        corp_id="D12345",
        effective_date=date(2024, 1, 1),
        event_type=EventType.JOB_CHANGE,
        job_code="UNKNOWN",
    )

    jobs = {
        "JOB_A": Job(
            code="JOB_A",
            name="Job A",
        ),
    }

    with pytest.raises(
        ValueError,
        match="Job 'UNKNOWN' does not exist",
    ):
        validate_event_references(
            event,
            jobs,
            {},
            {},
        )


def test_location_reference_must_exist():
    event = PersonEvent(
        id=None,
        corp_id="D12345",
        effective_date=date(2024, 1, 1),
        event_type=EventType.LOCATION_CHANGE,
        location_code="UNKNOWN",
    )

    locations = {
        "HAM": Location(
            code="HAM",
            name="Hamburg",
        ),
    }

    with pytest.raises(
        ValueError,
        match="Location 'UNKNOWN' does not exist",
    ):
        validate_event_references(
            event,
            {},
            locations,
            {},
        )


def test_department_reference_must_exist():
    event = PersonEvent(
        id=None,
        corp_id="D12345",
        effective_date=date(2024, 1, 1),
        event_type=EventType.TRANSFER,
        department_siglum="UNKNOWN",
    )

    departments = {
        "ASOSB": Department(
            siglum="ASOSB",
            name="Retrofit Operations",
        ),
    }

    with pytest.raises(
        ValueError,
        match="Department 'UNKNOWN' does not exist",
    ):
        validate_event_references(
            event,
            {},
            {},
            departments,
        )


def test_valid_references():
    event = PersonEvent(
        id=None,
        corp_id="D12345",
        effective_date=date(2024, 1, 1),
        event_type=EventType.TRANSFER,
        department_siglum="ASOSB",
    )

    departments = {
        "ASOSB": Department(
            siglum="ASOSB",
            name="Retrofit Operations",
        ),
    }

    validate_event_references(
        event,
        {},
        {},
        departments,
    )


def test_employment_status_can_change_from_temp_to_permanent():
    history = [
        PersonEvent(
            id=1,
            corp_id="D12345",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            employment_status=EmploymentStatus.TEMP,
        ),
    ]

    event = PersonEvent(
        id=2,
        corp_id="D12345",
        effective_date=date(2024, 1, 1),
        event_type=EventType.EMPLOYMENT_STATUS_CHANGE,
        employment_status=EmploymentStatus.PERMANENT,
    )

    validate_event_history(event, history)


def test_employment_status_cannot_change_from_permanent_to_temp():
    history = [
        PersonEvent(
            id=1,
            corp_id="D12345",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            employment_status=EmploymentStatus.PERMANENT,
        ),
    ]

    event = PersonEvent(
        id=2,
        corp_id="D12345",
        effective_date=date(2024, 1, 1),
        event_type=EventType.EMPLOYMENT_STATUS_CHANGE,
        employment_status=EmploymentStatus.TEMP,
    )

    with pytest.raises(
        ValueError,
        match="PERMANENT.*TEMP",
    ):
        validate_event_history(event, history)


def test_employment_status_cannot_change_to_same_status():
    history = [
        PersonEvent(
            id=1,
            corp_id="D12345",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            employment_status=EmploymentStatus.PERMANENT,
        ),
    ]

    event = PersonEvent(
        id=2,
        corp_id="D12345",
        effective_date=date(2024, 1, 1),
        event_type=EventType.EMPLOYMENT_STATUS_CHANGE,
        employment_status=EmploymentStatus.PERMANENT,
    )

    with pytest.raises(
        ValueError,
        match="Employment status has not changed",
    ):
        validate_event_history(event, history)


def test_fte_change_can_be_zero():
    history = [
        PersonEvent(
            id=1,
            corp_id="D12345",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            fte=1.0,
        ),
    ]

    event = PersonEvent(
        id=2,
        corp_id="D12345",
        effective_date=date(2024, 1, 1),
        event_type=EventType.FTE_CHANGE,
        fte=0.0,
    )

    validate_event_history(event, history)


def test_fte_change_cannot_exceed_one():
    history = [
        PersonEvent(
            id=1,
            corp_id="D12345",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            fte=1.0,
        ),
    ]

    event = PersonEvent(
        id=2,
        corp_id="D12345",
        effective_date=date(2024, 1, 1),
        event_type=EventType.FTE_CHANGE,
        fte=1.2,
    )

    with pytest.raises(
        ValueError,
        match="FTE cannot exceed 1",
    ):
        validate_event_history(event, history)


def test_fte_change_must_change_fte():
    history = [
        PersonEvent(
            id=1,
            corp_id="D12345",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            fte=0.8,
        ),
    ]

    event = PersonEvent(
        id=2,
        corp_id="D12345",
        effective_date=date(2024, 1, 1),
        event_type=EventType.FTE_CHANGE,
        fte=0.8,
    )

    with pytest.raises(
        ValueError,
        match="FTE has not changed",
    ):
        validate_event_history(event, history)
