from datetime import date

import pytest
from django.core.exceptions import ValidationError

from workforce.enums import EmploymentStatus, EventType
from workforce.models import Department, Job, Location, Person, PersonEvent
from workforce.services.events import add_event


@pytest.mark.django_db
def test_add_join_event():
    person = Person.objects.create(
        corp_id="D10001",
        first_name="Max",
        last_name="Mustermann",
    )

    job = Job.objects.create(
        code="JOB_A",
        name="Job A",
    )

    location = Location.objects.create(
        code="HAM",
        name="Hamburg",
    )

    department = Department.objects.create(
        siglum="ASOSB",
        name="Retrofit Operations",
    )

    event = PersonEvent(
        person=person,
        effective_date=date(2022, 1, 1),
        event_type=EventType.JOIN,
        job=job,
        location=location,
        department=department,
        employment_status=EmploymentStatus.PERMANENT,
        fte=1.0,
    )

    result = add_event(event)

    assert result.pk is not None
    assert result.person == person
    assert result.job == job
    assert result.location == location
    assert result.department == department
    assert result.fte == 1.0


@pytest.mark.django_db
def test_person_can_only_have_one_join():
    person = Person.objects.create(
        corp_id="D10001",
        first_name="Max",
        last_name="Mustermann",
    )

    first_join = PersonEvent(
        person=person,
        effective_date=date(2022, 1, 1),
        event_type=EventType.JOIN,
    )

    add_event(first_join)

    second_join = PersonEvent(
        person=person,
        effective_date=date(2023, 1, 1),
        event_type=EventType.JOIN,
    )

    with pytest.raises(ValidationError):
        add_event(second_join)
