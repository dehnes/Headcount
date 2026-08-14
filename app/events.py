from dataclasses import dataclass
from datetime import date, timedelta

from app.validation import (
    validate_event,
    validate_event_history,
    validate_event_references,
)

from .database import get_connection
from .models import (
    Department,
    EmploymentStatus,
    EventType,
    Job,
    LeaveType,
    Location,
    Person,
    PersonEvent,
    PersonHistoryEntry,
    PersonState,
    PersonStatus,
    PersonTimelineEntry,
)


@dataclass
class StateContext:
    jobs: dict[str, Job]
    locations: dict[str, Location]
    departments: dict[str, Department]


def add_event(event: PersonEvent) -> int:
    # ---------------------------------------------------------
    # 1. Structural validation
    # ---------------------------------------------------------
    validate_event(event)

    with get_connection() as connection:
        # -----------------------------------------------------
        # 2. Load existing event history
        # -----------------------------------------------------
        history_rows = connection.execute(
            """
            SELECT
                id,
                corp_id,
                effective_date,
                event_type,
                job_code,
                location_code,
                department_siglum,
                employment_status,
                leave_type,
                notes,
                fte
            FROM person_event
            WHERE corp_id = ?
            ORDER BY effective_date, id
            """,
            (event.corp_id,),
        ).fetchall()

        history = [
            PersonEvent(
                id=row["id"],
                corp_id=row["corp_id"],
                effective_date=date.fromisoformat(row["effective_date"]),
                event_type=EventType(row["event_type"]),
                job_code=row["job_code"],
                location_code=row["location_code"],
                department_siglum=row["department_siglum"],
                employment_status=(
                    EmploymentStatus(row["employment_status"])
                    if row["employment_status"]
                    else None
                ),
                leave_type=(
                    LeaveType(row["leave_type"]) if row["leave_type"] else None
                ),
                notes=row["notes"],
                fte=row["fte"],
            )
            for row in history_rows
        ]

        # -----------------------------------------------------
        # 3. Validate event against existing history
        # -----------------------------------------------------
        validate_event_history(
            event,
            history,
        )

        # -----------------------------------------------------
        # 4. Load master data
        # -----------------------------------------------------
        job_rows = connection.execute(
            """
            SELECT code, name
            FROM job
            """
        ).fetchall()

        location_rows = connection.execute(
            """
            SELECT code, name
            FROM location
            """
        ).fetchall()

        department_rows = connection.execute(
            """
            SELECT siglum, name, parent_siglum
            FROM department
            """
        ).fetchall()

        # -----------------------------------------------------
        # 5. Convert master data to domain objects
        # -----------------------------------------------------
        jobs = {
            row["code"]: Job(
                code=row["code"],
                name=row["name"],
            )
            for row in job_rows
        }

        locations = {
            row["code"]: Location(
                code=row["code"],
                name=row["name"],
            )
            for row in location_rows
        }

        departments = {
            row["siglum"]: Department(
                siglum=row["siglum"],
                name=row["name"],
                parent_siglum=row["parent_siglum"],
            )
            for row in department_rows
        }

        # -----------------------------------------------------
        # 6. Validate referenced master data
        # -----------------------------------------------------
        validate_event_references(
            event,
            jobs,
            locations,
            departments,
        )

        # -----------------------------------------------------
        # 7. Insert event
        # -----------------------------------------------------
        cursor = connection.execute(
            """
            INSERT INTO person_event (
                corp_id,
                effective_date,
                event_type,
                job_code,
                location_code,
                department_siglum,
                employment_status,
                leave_type,
                notes,
                fte
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.corp_id,
                event.effective_date.isoformat(),
                event.event_type.value,
                event.job_code,
                event.location_code,
                event.department_siglum,
                event.employment_status,
                event.leave_type,
                event.notes,
                event.fte,
            ),
        )

        return cursor.lastrowid


def get_events_for_person(corp_id: str) -> list[PersonEvent]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                corp_id,
                effective_date,
                event_type,
                job_code,
                location_code,
                department_siglum,
                employment_status,
                leave_type,
                notes
            FROM person_event
            WHERE corp_id = ?
            ORDER BY effective_date, id
            """,
            (corp_id,),
        ).fetchall()

    return [
        PersonEvent(
            id=row["id"],
            corp_id=row["corp_id"],
            effective_date=date.fromisoformat(row["effective_date"]),
            event_type=EventType(row["event_type"]),
            job_code=row["job_code"],
            location_code=row["location_code"],
            department_siglum=row["department_siglum"],
            employment_status=row["employment_status"],
            leave_type=row["leave_type"],
            notes=row["notes"],
        )
        for row in rows
    ]


def get_person_state(
    corp_id: str,
    as_of: date,
) -> PersonState:

    person, events, context = _load_person_context(corp_id)

    state = PersonState(
        person=person,
    )

    for event in events:
        if event.effective_date > as_of:
            break

        apply_event(
            state,
            event,
            context,
        )

    return state


def apply_event(
    state: PersonState,
    event: PersonEvent,
    context: StateContext,
) -> None:

    if event.event_type == EventType.JOIN:
        state.status = PersonStatus.ACTIVE

        state.department = (
            context.departments[event.department_siglum]
            if event.department_siglum
            else None
        )

        state.job = context.jobs[event.job_code] if event.job_code else None

        state.location = (
            context.locations[event.location_code] if event.location_code else None
        )
        state.fte = event.fte
        state.employment_status = event.employment_status
        state.leave_type = None

    elif event.event_type == EventType.TRANSFER:
        state.department = context.departments[event.department_siglum]

    elif event.event_type == EventType.JOB_CHANGE:
        state.job = context.jobs[event.job_code]

    elif event.event_type == EventType.LOCATION_CHANGE:
        state.location = context.locations[event.location_code]

    elif event.event_type == EventType.EMPLOYMENT_STATUS_CHANGE:
        state.employment_status = event.employment_status

    elif event.event_type == EventType.FTE_CHANGE:
        state.fte = event.fte

    elif event.event_type == EventType.LEAVE_START:
        state.leave_type = event.leave_type

    elif event.event_type == EventType.LEAVE_END:
        state.leave_type = None

    elif event.event_type == EventType.EXIT:
        state.status = PersonStatus.EXITED

        state.department = None
        state.job = None
        state.location = None
        state.employment_status = None
        state.leave_type = None
        state.fte = None


def get_person_history(
    corp_id: str,
) -> list[PersonHistoryEntry]:

    _, events, context = _load_person_context(corp_id)

    history: list[PersonHistoryEntry] = []

    for event in events:
        history.append(
            PersonHistoryEntry(
                event=event,
                job=(context.jobs[event.job_code] if event.job_code else None),
                location=(
                    context.locations[event.location_code]
                    if event.location_code
                    else None
                ),
                department=(
                    context.departments[event.department_siglum]
                    if event.department_siglum
                    else None
                ),
            )
        )

    return history


def get_person_timeline(
    corp_id: str,
) -> list[PersonTimelineEntry]:

    person, events, context = _load_person_context(corp_id)

    if not events:
        return []

    state = PersonState(
        person=person,
    )

    timeline: list[PersonTimelineEntry] = []

    for index, event in enumerate(events):
        apply_event(
            state,
            event,
            context,
        )

        start_date = event.effective_date

        if index + 1 < len(events):
            end_date = events[index + 1].effective_date - timedelta(days=1)
        else:
            end_date = None

        timeline.append(
            PersonTimelineEntry(
                start_date=start_date,
                end_date=end_date,
                department=state.department,
                job=state.job,
                location=state.location,
                employment_status=state.employment_status,
                leave_type=state.leave_type,
            )
        )

    return timeline


def _load_person_context(
    corp_id: str,
) -> tuple[Person, list[PersonEvent], StateContext]:

    with get_connection() as connection:
        # ---------------------------------------------------------
        # Person
        # ---------------------------------------------------------
        person_row = connection.execute(
            """
            SELECT corp_id, first_name, last_name
            FROM person
            WHERE corp_id = ?
            """,
            (corp_id,),
        ).fetchone()

        if person_row is None:
            raise ValueError(f"Person with CorpId '{corp_id}' does not exist.")

        person = Person(
            corp_id=person_row["corp_id"],
            first_name=person_row["first_name"],
            last_name=person_row["last_name"],
        )

        # ---------------------------------------------------------
        # Events
        # ---------------------------------------------------------
        event_rows = connection.execute(
            """
            SELECT
                id,
                corp_id,
                effective_date,
                event_type,
                job_code,
                location_code,
                department_siglum,
                employment_status,
                leave_type,
                notes,
                fte
            FROM person_event
            WHERE corp_id = ?
            ORDER BY effective_date, id
            """,
            (corp_id,),
        ).fetchall()

        # ---------------------------------------------------------
        # Jobs
        # ---------------------------------------------------------
        job_rows = connection.execute(
            """
            SELECT code, name
            FROM job
            """
        ).fetchall()

        # ---------------------------------------------------------
        # Locations
        # ---------------------------------------------------------
        location_rows = connection.execute(
            """
            SELECT code, name
            FROM location
            """
        ).fetchall()

        # ---------------------------------------------------------
        # Departments
        # ---------------------------------------------------------
        department_rows = connection.execute(
            """
            SELECT siglum, name, parent_siglum
            FROM department
            """
        ).fetchall()

    # -------------------------------------------------------------
    # Events in Python objects
    # -------------------------------------------------------------
    events = [
        PersonEvent(
            id=row["id"],
            corp_id=row["corp_id"],
            effective_date=date.fromisoformat(row["effective_date"]),
            event_type=EventType(row["event_type"]),
            job_code=row["job_code"],
            location_code=row["location_code"],
            department_siglum=row["department_siglum"],
            employment_status=(
                EmploymentStatus(row["employment_status"])
                if row["employment_status"]
                else None
            ),
            leave_type=(LeaveType(row["leave_type"]) if row["leave_type"] else None),
            notes=row["notes"],
            fte=row["fte"],
        )
        for row in event_rows
    ]

    # -------------------------------------------------------------
    # Context
    # -------------------------------------------------------------
    context = StateContext(
        jobs={
            row["code"]: Job(
                code=row["code"],
                name=row["name"],
            )
            for row in job_rows
        },
        locations={
            row["code"]: Location(
                code=row["code"],
                name=row["name"],
            )
            for row in location_rows
        },
        departments={
            row["siglum"]: Department(
                siglum=row["siglum"],
                name=row["name"],
                parent_siglum=row["parent_siglum"],
            )
            for row in department_rows
        },
    )

    return person, events, context
