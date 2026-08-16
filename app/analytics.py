from dataclasses import dataclass
from datetime import date, timedelta

from app.database import get_connection
from app.events import get_person_state
from app.models import (
    Department,
    EventType,
    PersonStatus,
    WorkforceMetrics,
)


@dataclass
class WorkforceMovement:
    corp_id: str
    effective_date: date
    event_type: EventType

    previous_location_code: str | None
    previous_department_siglum: str | None
    previous_job_code: str | None
    previous_fte: float | None

    new_location_code: str | None
    new_department_siglum: str | None
    new_job_code: str | None
    new_fte: float | None


@dataclass
class WorkforceMovements:
    joins: int
    exits: int


@dataclass
class WorkforcePoint:
    date: date
    headcount: int
    fte: float


@dataclass
class WorkforceSnapshot:
    as_of: date
    headcount: int
    fte: float


@dataclass
class WorkforceChange:
    from_date: date
    to_date: date
    headcount_change: int
    fte_change: float


def get_workforce(
    as_of: date,
    *,
    location_code: str | None = None,
    department_siglum: str | None = None,
    job_code: str | None = None,
) -> WorkforceMetrics:

    with get_connection() as connection:
        person_rows = connection.execute("""
            SELECT corp_id
            FROM person
            ORDER BY corp_id
            """).fetchall()

        department_rows = connection.execute("""
            SELECT siglum, name, parent_siglum
            FROM department
            """).fetchall()

    departments = {
        row["siglum"]: Department(
            siglum=row["siglum"],
            name=row["name"],
            parent_siglum=row["parent_siglum"],
        )
        for row in department_rows
    }

    department_tree: set[str] | None = None

    if department_siglum is not None:
        department_tree = get_department_tree(
            departments,
            department_siglum,
        )

    headcount = 0
    fte = 0.0

    for person_row in person_rows:
        state = get_person_state(
            person_row["corp_id"],
            as_of,
        )

        if state.status != PersonStatus.ACTIVE:
            continue

        if location_code is not None and (
            state.location is None or state.location.code != location_code
        ):
            continue

        if department_tree is not None and (
            state.department is None or state.department.siglum not in department_tree
        ):
            continue

        if job_code is not None and (state.job is None or state.job.code != job_code):
            continue

        headcount += 1
        fte += state.fte or 0.0

    return WorkforceMetrics(
        headcount=headcount,
        fte=fte,
    )


def get_workforce_trend(
    start: date,
    end: date,
    *,
    location_code: str | None = None,
    department_siglum: str | None = None,
    job_code: str | None = None,
) -> list[WorkforcePoint]:

    if end < start:
        raise ValueError("end cannot be before start.")

    # Alle Personen laden
    with get_connection() as connection:
        person_rows = connection.execute("""
            SELECT corp_id
            FROM person
            ORDER BY corp_id
            """).fetchall()

        event_rows = connection.execute(
            """
            SELECT effective_date
            FROM person_event
            WHERE effective_date >= ?
              AND effective_date <= ?
            ORDER BY effective_date
            """,
            (
                start.isoformat(),
                end.isoformat(),
            ),
        ).fetchall()

    # Alle relevanten Zeitpunkte bestimmen
    dates = sorted(
        {
            start,
            *(date.fromisoformat(row["effective_date"]) for row in event_rows),
        }
    )

    result: list[WorkforcePoint] = []

    for as_of in dates:
        headcount = 0
        fte = 0.0

        for person_row in person_rows:
            state = get_person_state(
                person_row["corp_id"],
                as_of,
            )

            if state.status != PersonStatus.ACTIVE:
                continue

            if location_code is not None and (
                state.location is None or state.location.code != location_code
            ):
                continue

            if department_siglum is not None and (
                state.department is None or state.department.siglum != department_siglum
            ):
                continue

            if job_code is not None and (
                state.job is None or state.job.code != job_code
            ):
                continue

            headcount += 1
            fte += state.fte or 0.0

        result.append(
            WorkforcePoint(
                date=as_of,
                headcount=headcount,
                fte=fte,
            )
        )

    return result


def get_department_tree(
    departments: dict[str, Department],
    root_siglum: str,
) -> set[str]:
    result = {root_siglum}

    changed = True

    while changed:
        changed = False

        for department in departments.values():
            if department.parent_siglum in result and department.siglum not in result:
                result.add(department.siglum)
                changed = True

    return result


def get_workforce_by_department(
    as_of: date,
    *,
    location_code: str | None = None,
) -> dict[str, WorkforceMetrics]:

    with get_connection() as connection:
        department_rows = connection.execute("""
            SELECT siglum
            FROM department
            ORDER BY siglum
            """).fetchall()

    result = {
        row["siglum"]: WorkforceMetrics(
            headcount=0,
            fte=0.0,
        )
        for row in department_rows
    }

    with get_connection() as connection:
        person_rows = connection.execute("""
            SELECT corp_id
            FROM person
            ORDER BY corp_id
            """).fetchall()

    for person_row in person_rows:
        state = get_person_state(
            person_row["corp_id"],
            as_of,
        )

        if state.status != PersonStatus.ACTIVE:
            continue

        if state.department is None:
            continue

        if location_code is not None and (
            state.location is None or state.location.code != location_code
        ):
            continue

        siglum = state.department.siglum

        # Sollte aus irgendeinem Grund eine Abteilung im State
        # stehen, die nicht mehr in den Masterdaten existiert,
        # ignorieren wir sie.
        if siglum not in result:
            continue

        result[siglum].headcount += 1
        result[siglum].fte += state.fte or 0.0

    return result


def get_workforce_by_department_tree(
    as_of: date,
    *,
    location_code: str | None = None,
) -> dict[str, WorkforceMetrics]:

    with get_connection() as connection:
        department_rows = connection.execute("""
            SELECT siglum, name, parent_siglum
            FROM department
            ORDER BY siglum
            """).fetchall()

        person_rows = connection.execute("""
            SELECT corp_id
            FROM person
            ORDER BY corp_id
            """).fetchall()

    departments = {
        row["siglum"]: Department(
            siglum=row["siglum"],
            name=row["name"],
            parent_siglum=row["parent_siglum"],
        )
        for row in department_rows
    }

    result = {
        siglum: WorkforceMetrics(
            headcount=0,
            fte=0.0,
        )
        for siglum in departments
    }

    for person_row in person_rows:
        state = get_person_state(
            person_row["corp_id"],
            as_of,
        )

        if state.status != PersonStatus.ACTIVE:
            continue

        if state.department is None:
            continue

        if location_code is not None and (
            state.location is None or state.location.code != location_code
        ):
            continue

        department_siglum = state.department.siglum

        if department_siglum not in departments:
            continue

        # ---------------------------------------------------------
        # Die Person zählt in ihrer eigenen Abteilung und in allen
        # übergeordneten Abteilungen.
        # ---------------------------------------------------------

        current_siglum: str | None = department_siglum

        while current_siglum is not None:
            result[current_siglum].headcount += 1
            result[current_siglum].fte += state.fte or 0.0

            current_department = departments[current_siglum]

            current_siglum = current_department.parent_siglum

    return result


def get_workforce_history(
    dates: list[date],
    *,
    location_code: str | None = None,
    department_siglum: str | None = None,
    job_code: str | None = None,
) -> list[WorkforceSnapshot]:

    return [
        WorkforceSnapshot(
            as_of=as_of,
            headcount=metrics.headcount,
            fte=metrics.fte,
        )
        for as_of in sorted(dates)
        for metrics in [
            get_workforce(
                as_of=as_of,
                location_code=location_code,
                department_siglum=department_siglum,
                job_code=job_code,
            )
        ]
    ]


def calculate_workforce_changes(
    snapshots: list[WorkforceSnapshot],
) -> list[WorkforceChange]:

    snapshots = sorted(
        snapshots,
        key=lambda snapshot: snapshot.as_of,
    )

    changes: list[WorkforceChange] = []

    for previous, current in zip(
        snapshots,
        snapshots[1:],
    ):
        changes.append(
            WorkforceChange(
                from_date=previous.as_of,
                to_date=current.as_of,
                headcount_change=(current.headcount - previous.headcount),
                fte_change=current.fte - previous.fte,
            )
        )

    return changes


def get_workforce_movements(
    from_date: date,
    to_date: date,
) -> list[WorkforceMovement]:

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                corp_id,
                effective_date,
                event_type
            FROM person_event
            WHERE effective_date >= ?
              AND effective_date <= ?
            ORDER BY effective_date, id
            """,
            (
                from_date.isoformat(),
                to_date.isoformat(),
            ),
        ).fetchall()

    movements: list[WorkforceMovement] = []

    for row in rows:
        event_date = date.fromisoformat(row["effective_date"])

        event_type = EventType(row["event_type"])

        # ---------------------------------------------------------
        # Zustand vor dem Event
        # ---------------------------------------------------------

        previous_state = get_person_state(
            row["corp_id"],
            event_date - timedelta(days=1),
        )

        # ---------------------------------------------------------
        # Zustand nach dem Event
        # ---------------------------------------------------------

        new_state = get_person_state(
            row["corp_id"],
            event_date,
        )

        movements.append(
            WorkforceMovement(
                corp_id=row["corp_id"],
                effective_date=event_date,
                event_type=event_type,
                previous_location_code=(
                    previous_state.location.code
                    if previous_state.location is not None
                    else None
                ),
                previous_department_siglum=(
                    previous_state.department.siglum
                    if previous_state.department is not None
                    else None
                ),
                previous_job_code=(
                    previous_state.job.code if previous_state.job is not None else None
                ),
                previous_fte=previous_state.fte,
                new_location_code=(
                    new_state.location.code if new_state.location is not None else None
                ),
                new_department_siglum=(
                    new_state.department.siglum
                    if new_state.department is not None
                    else None
                ),
                new_job_code=(
                    new_state.job.code if new_state.job is not None else None
                ),
                new_fte=new_state.fte,
            )
        )

    return movements


@dataclass
class WorkforceMovementSummary:
    joins_headcount: int = 0
    joins_fte: float = 0.0

    exits_headcount: int = 0
    exits_fte: float = 0.0

    transfers_in_headcount: int = 0
    transfers_in_fte: float = 0.0

    transfers_out_headcount: int = 0
    transfers_out_fte: float = 0.0

    location_changes_in_headcount: int = 0
    location_changes_in_fte: float = 0.0

    location_changes_out_headcount: int = 0
    location_changes_out_fte: float = 0.0

    job_changes_headcount: int = 0
    job_changes_fte: float = 0.0

    fte_changes_headcount: int = 0
    fte_changes_fte: float = 0.0


def get_workforce_movement_summary(
    from_date: date,
    to_date: date,
    *,
    location_code: str | None = None,
    department_siglum: str | None = None,
    job_code: str | None = None,
) -> WorkforceMovementSummary:

    movements = get_workforce_movements(
        from_date,
        to_date,
    )

    # ---------------------------------------------------------
    # Department hierarchy
    # ---------------------------------------------------------

    departments: dict[str, Department] = {}

    if department_siglum is not None:
        with get_connection() as connection:
            department_rows = connection.execute("""
                SELECT
                    siglum,
                    name,
                    parent_siglum
                FROM department
                """).fetchall()

        departments = {
            row["siglum"]: Department(
                siglum=row["siglum"],
                name=row["name"],
                parent_siglum=row["parent_siglum"],
            )
            for row in department_rows
        }

        department_tree = get_department_tree(
            departments,
            department_siglum,
        )

    else:
        department_tree = None

    result = WorkforceMovementSummary()

    for movement in movements:
        # -----------------------------------------------------
        # JOIN
        # -----------------------------------------------------

        if movement.event_type == EventType.JOIN:
            if location_code is not None and (
                movement.new_location_code != location_code
            ):
                continue

            if department_tree is not None and (
                movement.new_department_siglum not in department_tree
            ):
                continue

            if job_code is not None and (movement.new_job_code != job_code):
                continue

            result.joins_headcount += 1
            result.joins_fte += movement.new_fte or 0.0

        # -----------------------------------------------------
        # EXIT
        # -----------------------------------------------------

        elif movement.event_type == EventType.EXIT:
            if location_code is not None and (
                movement.previous_location_code != location_code
            ):
                continue

            if department_tree is not None and (
                movement.previous_department_siglum not in department_tree
            ):
                continue

            if job_code is not None and (movement.previous_job_code != job_code):
                continue

            result.exits_headcount += 1
            result.exits_fte += movement.previous_fte or 0.0

        # -----------------------------------------------------
        # TRANSFER
        # -----------------------------------------------------

        elif movement.event_type == EventType.TRANSFER:
            matches_previous = True
            matches_new = True

            # OUT: Zustand vor dem Transfer
            if location_code is not None:
                matches_previous = movement.previous_location_code == location_code

            if department_tree is not None:
                matches_previous = matches_previous and (
                    movement.previous_department_siglum in department_tree
                )

            if job_code is not None:
                matches_previous = matches_previous and (
                    movement.previous_job_code == job_code
                )

            if matches_previous:
                result.transfers_out_headcount += 1
                result.transfers_out_fte += movement.previous_fte or 0.0

            # IN: Zustand nach dem Transfer
            if location_code is not None:
                matches_new = movement.new_location_code == location_code

            if department_tree is not None:
                matches_new = matches_new and (
                    movement.new_department_siglum in department_tree
                )

            if job_code is not None:
                matches_new = matches_new and (movement.new_job_code == job_code)

            if matches_new:
                result.transfers_in_headcount += 1
                result.transfers_in_fte += movement.new_fte or 0.0

        # -----------------------------------------------------
        # LOCATION CHANGE
        # -----------------------------------------------------

        elif movement.event_type == EventType.LOCATION_CHANGE:
            matches_previous = True
            matches_new = True

            # OUT
            if location_code is not None:
                matches_previous = movement.previous_location_code == location_code

            if department_tree is not None:
                matches_previous = matches_previous and (
                    movement.previous_department_siglum in department_tree
                )

            if job_code is not None:
                matches_previous = matches_previous and (
                    movement.previous_job_code == job_code
                )

            if matches_previous:
                result.location_changes_out_headcount += 1
                result.location_changes_out_fte += movement.previous_fte or 0.0

            # IN
            if location_code is not None:
                matches_new = movement.new_location_code == location_code

            if department_tree is not None:
                matches_new = matches_new and (
                    movement.new_department_siglum in department_tree
                )

            if job_code is not None:
                matches_new = matches_new and (movement.new_job_code == job_code)

            if matches_new:
                result.location_changes_in_headcount += 1
                result.location_changes_in_fte += movement.new_fte or 0.0

        # -----------------------------------------------------
        # JOB CHANGE
        # -----------------------------------------------------

        elif movement.event_type == EventType.JOB_CHANGE:
            if location_code is not None and (
                movement.previous_location_code != location_code
            ):
                continue

            if department_tree is not None and (
                movement.previous_department_siglum not in department_tree
            ):
                continue

            if job_code is not None and not (
                movement.previous_job_code == job_code
                or movement.new_job_code == job_code
            ):
                continue

            result.job_changes_headcount += 1
            result.job_changes_fte += movement.previous_fte or 0.0

        # -----------------------------------------------------
        # FTE CHANGE
        # -----------------------------------------------------

        elif movement.event_type == EventType.FTE_CHANGE:
            if location_code is not None and (
                movement.new_location_code != location_code
            ):
                continue

            if department_tree is not None and (
                movement.new_department_siglum not in department_tree
            ):
                continue

            if job_code is not None and (movement.new_job_code != job_code):
                continue

            result.fte_changes_headcount += 1

            result.fte_changes_fte += (movement.new_fte or 0.0) - (
                movement.previous_fte or 0.0
            )

    return result
