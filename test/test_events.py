from datetime import date

import pytest

from app.events import StateContext, apply_event, get_person_state
from app.models import (
    Department,
    EmploymentStatus,
    EventType,
    Job,
    LeaveType,
    Location,
    Person,
    PersonEvent,
    PersonState,
    PersonStatus,
)


def test_person_join(test_database):
    from app.events import add_event

    add_event(
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.TEMP,
        )
    )

    state = get_person_state(
        corp_id="D12345",
        as_of=date(2022, 1, 2),
    )

    assert state.person.corp_id == "D12345"
    assert state.department.siglum == "ASOSB"
    assert state.job.code == "JOB_A"
    assert state.location.code == "HAM"
    assert state.employment_status == EmploymentStatus.TEMP
    assert state.leave_type is None


def test_job_change(test_database):
    from app.events import add_event

    add_event(
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.TEMP,
        )
    )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2023, 1, 1),
            event_type=EventType.JOB_CHANGE,
            job_code="JOB_B",
        )
    )
    state_before = get_person_state(
        corp_id="D12345",
        as_of=date(2022, 12, 31),
    )

    assert state_before.job.code == "JOB_A"

    state_after = get_person_state(
        corp_id="D12345",
        as_of=date(2023, 1, 1),
    )

    assert state_after.job.code == "JOB_B"


def test_transfer(test_database):
    from app.events import add_event

    add_event(
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.TEMP,
        )
    )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2024, 6, 15),
            event_type=EventType.TRANSFER,
            department_siglum="ASOSBS",
        )
    )

    before = get_person_state(
        "D12345",
        date(2024, 6, 14),
    )

    assert before.department.siglum == "ASOSB"

    after = get_person_state(
        "D12345",
        date(2024, 6, 15),
    )

    assert after.department.siglum == "ASOSBS"


def test_parental_leave(test_database):
    from app.events import add_event

    add_event(
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.PERMANENT,
        )
    )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2025, 7, 1),
            event_type=EventType.LEAVE_START,
            leave_type=LeaveType.PARENTAL,
        )
    )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2026, 1, 1),
            event_type=EventType.LEAVE_END,
            leave_type=LeaveType.PARENTAL,
        )
    )

    before = get_person_state(
        "D12345",
        date(2025, 6, 30),
    )

    assert before.leave_type is None

    during = get_person_state(
        "D12345",
        date(2025, 8, 1),
    )

    assert during.leave_type == "PARENTAL"

    after = get_person_state(
        "D12345",
        date(2026, 1, 1),
    )

    assert after.leave_type is None


def test_apply_job_change():
    state = PersonState(
        person=Person(
            corp_id="D12345",
            first_name="Max",
            last_name="Mustermann",
        ),
        status=PersonStatus.ACTIVE,
        department=Department(
            siglum="ASOSB",
            name="Retrofit Operations",
        ),
        job=Job(
            code="JOB_A",
            name="Job A",
        ),
        location=Location(
            code="HAM",
            name="Hamburg",
        ),
        employment_status=EmploymentStatus.TEMP,
    )

    context = StateContext(
        jobs={
            "JOB_A": Job(
                code="JOB_A",
                name="Job A",
            ),
            "JOB_B": Job(
                code="JOB_B",
                name="Job B",
            ),
        },
        locations={
            "HAM": Location(
                code="HAM",
                name="Hamburg",
            ),
        },
        departments={
            "ASOSB": Department(
                siglum="ASOSB",
                name="Retrofit Operations",
            ),
        },
    )

    event = PersonEvent(
        id=None,
        corp_id="D12345",
        effective_date=date(2023, 1, 1),
        event_type=EventType.JOB_CHANGE,
        job_code="JOB_B",
    )

    apply_event(state, event, context)
    assert state.status == PersonStatus.ACTIVE
    assert state.job.code == "JOB_B"
    assert state.job.name == "Job B"

    # Andere Eigenschaften bleiben unverändert
    assert state.department.siglum == "ASOSB"
    assert state.location.code == "HAM"
    assert state.employment_status == EmploymentStatus.TEMP


def test_apply_transfer():
    state = PersonState(
        person=Person(
            corp_id="D12345",
            first_name="Max",
            last_name="Mustermann",
        ),
        status=PersonStatus.ACTIVE,
        department=Department(
            siglum="ASOSB",
            name="Retrofit Operations",
        ),
        job=Job(
            code="JOB_B",
            name="Job B",
        ),
        location=Location(
            code="HAM",
            name="Hamburg",
        ),
        employment_status=EmploymentStatus.TEMP,
    )

    context = StateContext(
        jobs={
            "JOB_B": Job(
                code="JOB_B",
                name="Job B",
            ),
        },
        locations={
            "HAM": Location(
                code="HAM",
                name="Hamburg",
            ),
        },
        departments={
            "ASOSB": Department(
                siglum="ASOSB",
                name="Retrofit Operations",
            ),
            "ASOSBS": Department(
                siglum="ASOSBS",
                name="Retrofit Operations A320",
                parent_siglum="ASOSB",
            ),
        },
    )

    event = PersonEvent(
        id=None,
        corp_id="D12345",
        effective_date=date(2024, 6, 15),
        event_type=EventType.TRANSFER,
        department_siglum="ASOSBS",
    )

    apply_event(state, event, context)
    assert state.status == PersonStatus.ACTIVE
    assert state.department.siglum == "ASOSBS"
    assert state.department.name == "Retrofit Operations A320"

    # Job, Location und Employment Status bleiben unverändert
    assert state.job.code == "JOB_B"
    assert state.location.code == "HAM"
    assert state.employment_status == EmploymentStatus.TEMP


def test_apply_parental_leave():
    state = PersonState(
        person=Person(
            corp_id="D12345",
            first_name="Max",
            last_name="Mustermann",
        ),
        status=PersonStatus.ACTIVE,
        department=Department(
            siglum="ASOSBS",
            name="Retrofit Operations A320",
            parent_siglum="ASOSB",
        ),
        job=Job(
            code="JOB_B",
            name="Job B",
        ),
        location=Location(
            code="HAM",
            name="Hamburg",
        ),
        employment_status=EmploymentStatus.PERMANENT,
    )

    context = StateContext(
        jobs={
            "JOB_B": Job(
                code="JOB_B",
                name="Job B",
            ),
        },
        locations={
            "HAM": Location(
                code="HAM",
                name="Hamburg",
            ),
        },
        departments={
            "ASOSBS": Department(
                siglum="ASOSBS",
                name="Retrofit Operations A320",
                parent_siglum="ASOSB",
            ),
        },
    )

    event = PersonEvent(
        id=None,
        corp_id="D12345",
        effective_date=date(2025, 7, 1),
        event_type=EventType.LEAVE_START,
        leave_type=LeaveType.PARENTAL,
    )

    apply_event(state, event, context)
    assert state.status == PersonStatus.ACTIVE
    assert state.leave_type == LeaveType.PARENTAL

    # Die übrigen Eigenschaften bleiben unverändert
    assert state.department.siglum == "ASOSBS"
    assert state.job.code == "JOB_B"
    assert state.location.code == "HAM"
    assert state.employment_status == EmploymentStatus.PERMANENT


def test_apply_leave_end_keeps_person_active():
    state = PersonState(
        person=Person(
            corp_id="D12345",
            first_name="Max",
            last_name="Mustermann",
        ),
        status=PersonStatus.ACTIVE,
        department=Department(
            siglum="ASOSB",
            name="Retrofit Operations",
        ),
        job=Job(
            code="JOB_A",
            name="Job A",
        ),
        location=Location(
            code="HAM",
            name="Hamburg",
        ),
        employment_status=EmploymentStatus.PERMANENT,
        leave_type=LeaveType.PARENTAL,
    )

    event = PersonEvent(
        id=None,
        corp_id="D12345",
        effective_date=date(2025, 6, 1),
        event_type=EventType.LEAVE_END,
    )

    context = StateContext(
        jobs={},
        locations={},
        departments={},
    )

    apply_event(state, event, context)

    assert state.status == PersonStatus.ACTIVE
    assert state.leave_type is None


def test_apply_exit():
    state = PersonState(
        person=Person(
            corp_id="D12345",
            first_name="Max",
            last_name="Mustermann",
        ),
        department=Department(
            siglum="ASOSBS",
            name="Retrofit Operations A320",
            parent_siglum="ASOSB",
        ),
        job=Job(
            code="JOB_B",
            name="Job B",
        ),
        location=Location(
            code="HAM",
            name="Hamburg",
        ),
        employment_status=EmploymentStatus.PERMANENT,
        leave_type=None,
    )

    context = StateContext(
        jobs={
            "JOB_B": Job(
                code="JOB_B",
                name="Job B",
            ),
        },
        locations={
            "HAM": Location(
                code="HAM",
                name="Hamburg",
            ),
        },
        departments={
            "ASOSBS": Department(
                siglum="ASOSBS",
                name="Retrofit Operations A320",
                parent_siglum="ASOSB",
            ),
        },
    )

    event = PersonEvent(
        id=None,
        corp_id="D12345",
        effective_date=date(2026, 1, 1),
        event_type=EventType.EXIT,
    )

    apply_event(state, event, context)
    assert state.status == PersonStatus.EXITED
    assert state.department is None
    assert state.job is None
    assert state.location is None
    assert state.employment_status is None
    assert state.leave_type is None


def test_complete_person_history(test_database):
    from app.events import add_event

    # 01.01.2022 - Eintritt
    add_event(
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.TEMP,
        )
    )

    # 01.01.2023 - Jobwechsel
    add_event(
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2023, 1, 1),
            event_type=EventType.JOB_CHANGE,
            job_code="JOB_B",
        )
    )

    # 15.06.2024 - Teamwechsel
    add_event(
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2024, 6, 15),
            event_type=EventType.TRANSFER,
            department_siglum="ASOSBS",
        )
    )

    # 01.01.2025 - Festanstellung
    add_event(
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2025, 1, 1),
            event_type=EventType.EMPLOYMENT_STATUS_CHANGE,
            employment_status=EmploymentStatus.PERMANENT,
        )
    )

    # 01.07.2025 - Elternzeit
    add_event(
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2025, 7, 1),
            event_type=EventType.LEAVE_START,
            leave_type=LeaveType.PARENTAL,
        )
    )

    # 01.01.2026 - Rückkehr
    add_event(
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2026, 1, 1),
            event_type=EventType.LEAVE_END,
            leave_type=LeaveType.PARENTAL,
        )
    )

    # 1. Zustand: direkt nach Eintritt
    state = get_person_state(
        "D12345",
        date(2022, 1, 1),
    )

    assert state.department.siglum == "ASOSB"
    assert state.job.code == "JOB_A"
    assert state.location.code == "HAM"
    assert state.employment_status == EmploymentStatus.TEMP
    assert state.leave_type is None

    # 2. Nach Jobwechsel
    state = get_person_state(
        "D12345",
        date(2023, 1, 1),
    )

    assert state.department.siglum == "ASOSB"
    assert state.job.code == "JOB_B"
    assert state.location.code == "HAM"
    assert state.employment_status == EmploymentStatus.TEMP

    # 3. Nach Teamwechsel
    state = get_person_state(
        "D12345",
        date(2024, 6, 15),
    )

    assert state.department.siglum == "ASOSBS"
    assert state.job.code == "JOB_B"
    assert state.location.code == "HAM"
    assert state.employment_status == EmploymentStatus.TEMP

    # 4. Nach Festanstellung
    state = get_person_state(
        "D12345",
        date(2025, 1, 1),
    )

    assert state.department.siglum == "ASOSBS"
    assert state.job.code == "JOB_B"
    assert state.location.code == "HAM"
    assert state.employment_status == EmploymentStatus.PERMANENT
    assert state.leave_type is None

    # 5. Während Elternzeit
    state = get_person_state(
        "D12345",
        date(2025, 8, 1),
    )

    assert state.department.siglum == "ASOSBS"
    assert state.job.code == "JOB_B"
    assert state.location.code == "HAM"
    assert state.employment_status == EmploymentStatus.PERMANENT
    assert state.leave_type == "PARENTAL"

    # 6. Nach Rückkehr
    state = get_person_state(
        "D12345",
        date(2026, 1, 1),
    )

    assert state.department.siglum == "ASOSBS"
    assert state.job.code == "JOB_B"
    assert state.location.code == "HAM"
    assert state.employment_status == EmploymentStatus.PERMANENT
    assert state.leave_type is None


def test_person_history(test_database):
    from app.events import add_event, get_person_history

    add_event(
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.TEMP,
        )
    )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2023, 1, 1),
            event_type=EventType.JOB_CHANGE,
            job_code="JOB_B",
        )
    )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2024, 6, 15),
            event_type=EventType.TRANSFER,
            department_siglum="ASOSBS",
        )
    )

    history = get_person_history("D12345")

    assert len(history) == 3

    assert history[0].event.event_type == EventType.JOIN
    assert history[0].event.effective_date == date(2022, 1, 1)
    assert history[0].job.code == "JOB_A"
    assert history[0].location.code == "HAM"
    assert history[0].department.siglum == "ASOSB"

    assert history[1].event.event_type == EventType.JOB_CHANGE
    assert history[1].job.code == "JOB_B"

    assert history[2].event.event_type == EventType.TRANSFER
    assert history[2].department.siglum == "ASOSBS"


def test_person_timeline(test_database):
    from app.events import (
        add_event,
        get_person_timeline,
    )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.TEMP,
        )
    )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2023, 1, 1),
            event_type=EventType.JOB_CHANGE,
            job_code="JOB_B",
        )
    )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2024, 6, 15),
            event_type=EventType.TRANSFER,
            department_siglum="ASOSBS",
        )
    )

    timeline = get_person_timeline("D12345")

    assert len(timeline) == 3

    # ---------------------------------------------------------
    # 2022
    # ---------------------------------------------------------
    assert timeline[0].start_date == date(2022, 1, 1)
    assert timeline[0].end_date == date(2022, 12, 31)

    assert timeline[0].department.siglum == "ASOSB"
    assert timeline[0].job.code == "JOB_A"
    assert timeline[0].location.code == "HAM"
    assert timeline[0].employment_status == EmploymentStatus.TEMP

    # ---------------------------------------------------------
    # 2023 - 2024
    # ---------------------------------------------------------
    assert timeline[1].start_date == date(2023, 1, 1)
    assert timeline[1].end_date == date(2024, 6, 14)

    assert timeline[1].department.siglum == "ASOSB"
    assert timeline[1].job.code == "JOB_B"

    # ---------------------------------------------------------
    # ab 15.06.2024
    # ---------------------------------------------------------
    assert timeline[2].start_date == date(2024, 6, 15)
    assert timeline[2].end_date is None

    assert timeline[2].department.siglum == "ASOSBS"
    assert timeline[2].job.code == "JOB_B"
    assert timeline[2].location.code == "HAM"


def test_add_event_requires_join_first(test_database):
    from app.events import add_event

    event = PersonEvent(
        id=None,
        corp_id="D12345",
        effective_date=date(2022, 1, 1),
        event_type=EventType.JOB_CHANGE,
        job_code="JOB_A",
    )

    with pytest.raises(
        ValueError,
        match="first event.*JOIN",
    ):
        add_event(event)


def test_add_event_rejects_second_join(test_database):
    from app.events import add_event

    add_event(
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.TEMP,
        )
    )

    with pytest.raises(
        ValueError,
        match="only have one JOIN",
    ):
        add_event(
            PersonEvent(
                id=None,
                corp_id="D12345",
                effective_date=date(2023, 1, 1),
                event_type=EventType.JOIN,
                job_code="JOB_A",
                location_code="HAM",
                department_siglum="ASOSB",
                employment_status=EmploymentStatus.TEMP,
            )
        )


def test_add_event_rejects_event_after_exit(test_database):
    from app.events import add_event

    add_event(
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.TEMP,
        )
    )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2024, 1, 1),
            event_type=EventType.EXIT,
        )
    )

    with pytest.raises(
        ValueError,
        match="after EXIT",
    ):
        add_event(
            PersonEvent(
                id=None,
                corp_id="D12345",
                effective_date=date(2025, 1, 1),
                event_type=EventType.JOB_CHANGE,
                job_code="JOB_B",
            )
        )


def test_add_event_rejects_unknown_job(test_database):
    from app.events import add_event

    add_event(
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.TEMP,
        )
    )

    with pytest.raises(
        ValueError,
        match="Job 'UNKNOWN' does not exist",
    ):
        add_event(
            PersonEvent(
                id=None,
                corp_id="D12345",
                effective_date=date(2023, 1, 1),
                event_type=EventType.JOB_CHANGE,
                job_code="UNKNOWN",
            )
        )


def test_apply_join():
    state = PersonState(
        person=Person(
            corp_id="D12345",
            first_name="Max",
            last_name="Mustermann",
        ),
    )

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

    context = StateContext(
        jobs={
            "JOB_A": Job(
                code="JOB_A",
                name="Job A",
            ),
        },
        locations={
            "HAM": Location(
                code="HAM",
                name="Hamburg",
            ),
        },
        departments={
            "ASOSB": Department(
                siglum="ASOSB",
                name="Retrofit Operations",
            ),
        },
    )

    apply_event(state, event, context)

    assert state.status == PersonStatus.ACTIVE
    assert state.job.code == "JOB_A"
    assert state.location.code == "HAM"
    assert state.department.siglum == "ASOSB"
    assert state.employment_status == EmploymentStatus.TEMP
    assert state.leave_type is None


def test_apply_location_change():
    state = PersonState(
        person=Person(
            corp_id="D12345",
            first_name="Max",
            last_name="Mustermann",
        ),
        status=PersonStatus.ACTIVE,
        department=Department(
            siglum="ASOSB",
            name="Retrofit Operations",
        ),
        job=Job(
            code="JOB_A",
            name="Job A",
        ),
        location=Location(
            code="HAM",
            name="Hamburg",
        ),
        employment_status=EmploymentStatus.TEMP,
    )

    event = PersonEvent(
        id=None,
        corp_id="D12345",
        effective_date=date(2024, 7, 1),
        event_type=EventType.LOCATION_CHANGE,
        location_code="FRA",
    )

    context = StateContext(
        jobs={},
        locations={
            "FRA": Location(
                code="FRA",
                name="Frankfurt",
            ),
        },
        departments={},
    )

    apply_event(state, event, context)

    assert state.status == PersonStatus.ACTIVE
    assert state.location.code == "FRA"
    assert state.location.name == "Frankfurt"


def test_apply_employment_status_change():
    state = PersonState(
        person=Person(
            corp_id="D12345",
            first_name="Max",
            last_name="Mustermann",
        ),
        status=PersonStatus.ACTIVE,
        department=Department(
            siglum="ASOSB",
            name="Retrofit Operations",
        ),
        job=Job(
            code="JOB_A",
            name="Job A",
        ),
        location=Location(
            code="HAM",
            name="Hamburg",
        ),
        employment_status=EmploymentStatus.TEMP,
    )

    event = PersonEvent(
        id=None,
        corp_id="D12345",
        effective_date=date(2024, 1, 1),
        event_type=EventType.EMPLOYMENT_STATUS_CHANGE,
        employment_status=EmploymentStatus.PERMANENT,
    )

    context = StateContext(
        jobs={},
        locations={},
        departments={},
    )

    apply_event(state, event, context)

    assert state.status == PersonStatus.ACTIVE
    assert state.employment_status == EmploymentStatus.PERMANENT


def test_get_person_state_over_time(test_database):
    from app.events import add_event, get_person_state

    # ---------------------------------------------------------
    # 01.01.2022 - JOIN
    # ---------------------------------------------------------

    add_event(
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.TEMP,
        )
    )

    # ---------------------------------------------------------
    # 01.01.2023 - Job change
    # ---------------------------------------------------------

    add_event(
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2023, 1, 1),
            event_type=EventType.JOB_CHANGE,
            job_code="JOB_B",
        )
    )

    # ---------------------------------------------------------
    # 15.06.2024 - Transfer
    # ---------------------------------------------------------

    add_event(
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2024, 6, 15),
            event_type=EventType.TRANSFER,
            department_siglum="ASOSBS",
        )
    )

    # ---------------------------------------------------------
    # 01.01.2025 - Parental leave
    # ---------------------------------------------------------

    add_event(
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2025, 1, 1),
            event_type=EventType.LEAVE_START,
            leave_type=LeaveType.PARENTAL,
        )
    )

    # ---------------------------------------------------------
    # 01.07.2025 - Leave ends
    # ---------------------------------------------------------

    add_event(
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2025, 7, 1),
            event_type=EventType.LEAVE_END,
        )
    )

    # ---------------------------------------------------------
    # 01.01.2026 - Exit
    # ---------------------------------------------------------

    add_event(
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2026, 1, 1),
            event_type=EventType.EXIT,
        )
    )

    # =========================================================
    # Check state: 2022
    # =========================================================

    state = get_person_state(
        "D12345",
        date(2022, 6, 1),
    )

    assert state.status == PersonStatus.ACTIVE
    assert state.job.code == "JOB_A"
    assert state.department.siglum == "ASOSB"
    assert state.location.code == "HAM"
    assert state.employment_status == EmploymentStatus.TEMP
    assert state.leave_type is None

    # =========================================================
    # Check state: 2023
    # =========================================================

    state = get_person_state(
        "D12345",
        date(2023, 6, 1),
    )

    assert state.status == PersonStatus.ACTIVE
    assert state.job.code == "JOB_B"
    assert state.department.siglum == "ASOSB"

    # =========================================================
    # Check state: after transfer
    # =========================================================

    state = get_person_state(
        "D12345",
        date(2024, 7, 1),
    )

    assert state.status == PersonStatus.ACTIVE
    assert state.job.code == "JOB_B"
    assert state.department.siglum == "ASOSBS"
    assert state.location.code == "HAM"

    # =========================================================
    # Check state: during parental leave
    # =========================================================

    state = get_person_state(
        "D12345",
        date(2025, 3, 1),
    )

    assert state.status == PersonStatus.ACTIVE
    assert state.leave_type == LeaveType.PARENTAL

    # Team/job should remain unchanged during leave

    assert state.department.siglum == "ASOSBS"
    assert state.job.code == "JOB_B"

    # =========================================================
    # Check state: after parental leave
    # =========================================================

    state = get_person_state(
        "D12345",
        date(2025, 8, 1),
    )

    assert state.status == PersonStatus.ACTIVE
    assert state.leave_type is None
    assert state.department.siglum == "ASOSBS"
    assert state.job.code == "JOB_B"

    # =========================================================
    # Check state: after exit
    # =========================================================

    state = get_person_state(
        "D12345",
        date(2026, 2, 1),
    )

    assert state.status == PersonStatus.EXITED
    assert state.department is None
    assert state.job is None
    assert state.location is None
    assert state.employment_status is None
    assert state.leave_type is None


def test_apply_join_sets_fte():
    state = PersonState(
        person=Person(
            corp_id="D12345",
            first_name="Max",
            last_name="Mustermann",
        ),
    )

    context = StateContext(
        jobs={
            "JOB_A": Job(
                code="JOB_A",
                name="Job A",
            ),
        },
        locations={
            "HAM": Location(
                code="HAM",
                name="Hamburg",
            ),
        },
        departments={
            "ASOSB": Department(
                siglum="ASOSB",
                name="Retrofit Operations",
            ),
        },
    )

    event = PersonEvent(
        id=None,
        corp_id="D12345",
        effective_date=date(2022, 1, 1),
        event_type=EventType.JOIN,
        job_code="JOB_A",
        location_code="HAM",
        department_siglum="ASOSB",
        employment_status=EmploymentStatus.TEMP,
        fte=1.0,
    )

    apply_event(state, event, context)

    assert state.status == PersonStatus.ACTIVE
    assert state.fte == 1.0


def test_apply_fte_change():
    state = PersonState(
        person=Person(
            corp_id="D12345",
            first_name="Max",
            last_name="Mustermann",
        ),
        status=PersonStatus.ACTIVE,
        fte=1.0,
    )

    context = StateContext(
        jobs={},
        locations={},
        departments={},
    )

    event = PersonEvent(
        id=None,
        corp_id="D12345",
        effective_date=date(2024, 1, 1),
        event_type=EventType.FTE_CHANGE,
        fte=0.8,
    )

    apply_event(state, event, context)

    assert state.fte == 0.8


def test_apply_exit_clears_fte():
    state = PersonState(
        person=Person(
            corp_id="D12345",
            first_name="Max",
            last_name="Mustermann",
        ),
        status=PersonStatus.ACTIVE,
        fte=0.8,
    )

    context = StateContext(
        jobs={},
        locations={},
        departments={},
    )

    event = PersonEvent(
        id=None,
        corp_id="D12345",
        effective_date=date(2026, 1, 1),
        event_type=EventType.EXIT,
    )

    apply_event(state, event, context)

    assert state.status == PersonStatus.EXITED
    assert state.fte is None
