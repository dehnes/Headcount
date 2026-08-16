from datetime import date

import pytest

from app.analytics import (
    WorkforcePoint,
    WorkforceSnapshot,
    calculate_workforce_changes,
    get_department_tree,
    get_workforce,
    get_workforce_by_department,
    get_workforce_by_department_tree,
    get_workforce_history,
    get_workforce_movement_summary,
    get_workforce_movements,
    get_workforce_trend,
)
from app.database import get_connection
from app.events import add_event, get_person_state
from app.models import (
    Department,
    EmploymentStatus,
    EventType,
    PersonEvent,
)


def test_workforce_by_location(test_database):
    with get_connection() as connection:
        connection.execute(
            """
        INSERT INTO person (
            corp_id,
            first_name,
            last_name
        )
        VALUES (?, ?, ?)
        """,
            ("D10001", "Max", "Mustermann"),
        )

        connection.execute(
            """
            INSERT INTO person (
                corp_id,
                first_name,
                last_name
            )
            VALUES (?, ?, ?)
            """,
            ("D10002", "Anna", "Musterfrau"),
        )

        connection.execute(
            """
            INSERT INTO person (
                corp_id,
                first_name,
                last_name
            )
            VALUES (?, ?, ?)
            """,
            ("D10003", "Peter", "Muster"),
        )
    # Max - 1.0 FTE
    add_event(
        PersonEvent(
            id=None,
            corp_id="D10001",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.PERMANENT,
            fte=1.0,
        )
    )

    # Anna - 0.8 FTE
    add_event(
        PersonEvent(
            id=None,
            corp_id="D10002",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.PERMANENT,
            fte=0.8,
        )
    )

    # Peter - 0.0 FTE, zählt aber als Head
    add_event(
        PersonEvent(
            id=None,
            corp_id="D10003",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.PERMANENT,
            fte=0.0,
        )
    )

    result = get_workforce(
        as_of=date(2024, 1, 1),
        location_code="HAM",
    )

    assert result.headcount == 3
    assert result.fte == 1.8


def test_person_state_contains_fte(test_database):
    # ---------------------------------------------------------
    # Master data
    # ---------------------------------------------------------
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO person (
                corp_id,
                first_name,
                last_name
            )
            VALUES (?, ?, ?)
            """,
            ("D10001", "Max", "Mustermann"),
        )

    # ---------------------------------------------------------
    # JOIN event
    # ---------------------------------------------------------
    add_event(
        PersonEvent(
            id=None,
            corp_id="D10001",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.PERMANENT,
            fte=0.8,
        )
    )

    # ---------------------------------------------------------
    # Assert
    # ---------------------------------------------------------
    state = get_person_state(
        "D10001",
        date(2024, 1, 1),
    )

    assert state.fte == 0.8


def test_workforce_trend(test_database):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO person (
                corp_id,
                first_name,
                last_name
            )
            VALUES (?, ?, ?)
            """,
            ("D10001", "Max", "Mustermann"),
        )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10001",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.PERMANENT,
            fte=1.0,
        )
    )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10001",
            effective_date=date(2023, 1, 1),
            event_type=EventType.FTE_CHANGE,
            fte=0.8,
        )
    )

    result = get_workforce_trend(
        start=date(2022, 1, 1),
        end=date(2024, 1, 1),
        location_code="HAM",
    )

    assert result == [
        WorkforcePoint(
            date=date(2022, 1, 1),
            headcount=1,
            fte=1.0,
        ),
        WorkforcePoint(
            date=date(2023, 1, 1),
            headcount=1,
            fte=0.8,
        ),
    ]


def test_workforce_trend_uses_state_before_start(test_database):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO person (
                corp_id,
                first_name,
                last_name
            )
            VALUES (?, ?, ?)
            """,
            ("D10001", "Max", "Mustermann"),
        )

    # Person kommt bereits 2020 ins Unternehmen
    add_event(
        PersonEvent(
            id=None,
            corp_id="D10001",
            effective_date=date(2020, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.PERMANENT,
            fte=1.0,
        )
    )

    # FTE-Änderung innerhalb unseres Analysezeitraums
    add_event(
        PersonEvent(
            id=None,
            corp_id="D10001",
            effective_date=date(2023, 1, 1),
            event_type=EventType.FTE_CHANGE,
            fte=0.8,
        )
    )

    result = get_workforce_trend(
        start=date(2022, 1, 1),
        end=date(2024, 1, 1),
        location_code="HAM",
    )

    assert result == [
        WorkforcePoint(
            date=date(2022, 1, 1),
            headcount=1,
            fte=1.0,
        ),
        WorkforcePoint(
            date=date(2023, 1, 1),
            headcount=1,
            fte=0.8,
        ),
    ]


def test_workforce_trend_after_exit(test_database):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO person (
                corp_id,
                first_name,
                last_name
            )
            VALUES (?, ?, ?)
            """,
            ("D10001", "Max", "Mustermann"),
        )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10001",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.PERMANENT,
            fte=1.0,
        )
    )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10001",
            effective_date=date(2023, 6, 1),
            event_type=EventType.EXIT,
        )
    )

    result = get_workforce_trend(
        start=date(2022, 1, 1),
        end=date(2024, 1, 1),
        location_code="HAM",
    )

    assert result == [
        WorkforcePoint(
            date=date(2022, 1, 1),
            headcount=1,
            fte=1.0,
        ),
        WorkforcePoint(
            date=date(2023, 6, 1),
            headcount=0,
            fte=0.0,
        ),
    ]


def test_get_department_tree_supports_multiple_levels():
    departments = {
        "ASOSB": Department(
            siglum="ASOSB",
            name="Retrofit Operations",
            parent_siglum=None,
        ),
        "ASOSBS": Department(
            siglum="ASOSBS",
            name="Retrofit Operations A320",
            parent_siglum="ASOSB",
        ),
        "ASOSBSA": Department(
            siglum="ASOSBSA",
            name="A320 Engineering",
            parent_siglum="ASOSBS",
        ),
        "ASOSBSAX": Department(
            siglum="ASOSBSAX",
            name="A320 Engineering Structures",
            parent_siglum="ASOSBSA",
        ),
        "ASOSBL": Department(
            siglum="ASOSBL",
            name="Retrofit Operations A350",
            parent_siglum="ASOSB",
        ),
    }

    result = get_department_tree(
        departments,
        "ASOSB",
    )

    assert result == {
        "ASOSB",
        "ASOSBS",
        "ASOSBSA",
        "ASOSBSAX",
        "ASOSBL",
    }


def test_get_department_tree_returns_only_subtree():
    departments = {
        "ASOSB": Department(
            siglum="ASOSB",
            name="Retrofit Operations",
            parent_siglum=None,
        ),
        "ASOSBS": Department(
            siglum="ASOSBS",
            name="A320",
            parent_siglum="ASOSB",
        ),
        "ASOSBSA": Department(
            siglum="ASOSBSA",
            name="A320 Engineering",
            parent_siglum="ASOSBS",
        ),
        "OTHER": Department(
            siglum="OTHER",
            name="Other Department",
            parent_siglum=None,
        ),
        "OTHERA": Department(
            siglum="OTHERA",
            name="Other Child",
            parent_siglum="OTHER",
        ),
    }

    result = get_department_tree(
        departments,
        "ASOSB",
    )

    assert result == {
        "ASOSB",
        "ASOSBS",
        "ASOSBSA",
    }


def test_workforce_by_department_includes_children(test_database):
    with get_connection() as connection:
        # ---------------------------------------------------------
        # Personen
        # ---------------------------------------------------------
        connection.execute(
            """
            INSERT INTO person (
                corp_id,
                first_name,
                last_name
            )
            VALUES (?, ?, ?)
            """,
            ("D10001", "Max", "Mustermann"),
        )

        connection.execute(
            """
            INSERT INTO person (
                corp_id,
                first_name,
                last_name
            )
            VALUES (?, ?, ?)
            """,
            ("D10002", "Anna", "Musterfrau"),
        )

        connection.execute(
            """
            INSERT INTO person (
                corp_id,
                first_name,
                last_name
            )
            VALUES (?, ?, ?)
            """,
            ("D10003", "Peter", "Muster"),
        )

        connection.execute(
            """
            INSERT INTO person (
                corp_id,
                first_name,
                last_name
            )
            VALUES (?, ?, ?)
            """,
            ("D10004", "Julia", "Beispiel"),
        )

        # ---------------------------------------------------------
        # Zusätzliche Abteilungen
        #
        # ASOSB und ASOSBS existieren bereits in der Testdatenbank.
        # ---------------------------------------------------------
        connection.execute(
            """
            INSERT INTO department (
                siglum,
                name,
                parent_siglum
            )
            VALUES (?, ?, ?)
            """,
            (
                "ASOSBSA",
                "A320 Engineering",
                "ASOSBS",
            ),
        )

        connection.execute(
            """
            INSERT INTO department (
                siglum,
                name,
                parent_siglum
            )
            VALUES (?, ?, ?)
            """,
            (
                "OTHER",
                "Other Department",
                None,
            ),
        )

    # ---------------------------------------------------------
    # Max: direkt in ASOSB
    # ---------------------------------------------------------

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10001",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.PERMANENT,
            fte=1.0,
        )
    )

    # ---------------------------------------------------------
    # Anna: eine Ebene darunter
    # ---------------------------------------------------------

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10002",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSBS",
            employment_status=EmploymentStatus.PERMANENT,
            fte=0.8,
        )
    )

    # ---------------------------------------------------------
    # Peter: zwei Ebenen darunter
    # ---------------------------------------------------------

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10003",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSBSA",
            employment_status=EmploymentStatus.PERMANENT,
            fte=0.5,
        )
    )

    # ---------------------------------------------------------
    # Julia: außerhalb des ASOSB-Teilbaums
    # ---------------------------------------------------------

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10004",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="OTHER",
            employment_status=EmploymentStatus.PERMANENT,
            fte=1.0,
        )
    )

    # ---------------------------------------------------------
    # ASOSB inklusive aller Unterabteilungen
    # ---------------------------------------------------------

    result = get_workforce(
        as_of=date(2024, 1, 1),
        department_siglum="ASOSB",
    )

    assert result.headcount == 3
    assert result.fte == 2.3


def test_workforce_filters_can_be_combined(test_database):
    with get_connection() as connection:
        # ---------------------------------------------------------
        # Personen
        # ---------------------------------------------------------
        for corp_id, first_name, last_name in [
            ("D10001", "Max", "Mustermann"),
            ("D10002", "Anna", "Musterfrau"),
            ("D10003", "Peter", "Muster"),
            ("D10004", "Julia", "Beispiel"),
        ]:
            connection.execute(
                """
                INSERT INTO person (
                    corp_id,
                    first_name,
                    last_name
                )
                VALUES (?, ?, ?)
                """,
                (corp_id, first_name, last_name),
            )

        # Zusätzliche Abteilung für den Test
        connection.execute(
            """
            INSERT INTO department (
                siglum,
                name,
                parent_siglum
            )
            VALUES (?, ?, ?)
            """,
            (
                "ASOSBSA",
                "A320 Engineering",
                "ASOSBS",
            ),
        )
        # Zusätzlicher Standort für den Test
        connection.execute(
            """
            INSERT INTO location (
                code,
                name
            )
            VALUES (?, ?)
            """,
            (
                "FRA",
                "Frankfurt",
            ),
        )

    # ---------------------------------------------------------
    # Max
    # ASOSB / HAM / JOB_A
    # ---------------------------------------------------------

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10001",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.PERMANENT,
            fte=1.0,
        )
    )

    # ---------------------------------------------------------
    # Anna
    # ASOSBS / HAM / JOB_A
    # ---------------------------------------------------------

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10002",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSBS",
            employment_status=EmploymentStatus.PERMANENT,
            fte=0.8,
        )
    )

    # ---------------------------------------------------------
    # Peter
    # ASOSBSA / HAM / JOB_B
    #
    # Gehört zwar zum ASOSB-Teilbaum und nach HAM,
    # hat aber einen anderen Job.
    # ---------------------------------------------------------

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10003",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_B",
            location_code="HAM",
            department_siglum="ASOSBSA",
            employment_status=EmploymentStatus.PERMANENT,
            fte=0.5,
        )
    )

    # ---------------------------------------------------------
    # Julia
    # ASOSB / anderer Standort / JOB_A
    #
    # Gehört zur Abteilung und hat den richtigen Job,
    # aber nicht zum gesuchten Standort.
    # ---------------------------------------------------------

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10004",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="FRA",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.PERMANENT,
            fte=1.0,
        )
    )

    result = get_workforce(
        as_of=date(2024, 1, 1),
        department_siglum="ASOSB",
        location_code="HAM",
        job_code="JOB_A",
    )

    assert result.headcount == 2
    assert result.fte == 1.8


def test_workforce_by_department(test_database):
    with get_connection() as connection:
        for corp_id, first_name, last_name in [
            ("D10001", "Max", "Mustermann"),
            ("D10002", "Anna", "Musterfrau"),
            ("D10003", "Peter", "Muster"),
        ]:
            connection.execute(
                """
                INSERT INTO person (
                    corp_id,
                    first_name,
                    last_name
                )
                VALUES (?, ?, ?)
                """,
                (corp_id, first_name, last_name),
            )

        connection.execute(
            """
            INSERT INTO department (
                siglum,
                name,
                parent_siglum
            )
            VALUES (?, ?, ?)
            """,
            (
                "ASOSBSA",
                "A320 Engineering",
                "ASOSBS",
            ),
        )

    # Max → ASOSB → 1.0 FTE

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10001",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.PERMANENT,
            fte=1.0,
        )
    )

    # Anna → ASOSBS → 0.8 FTE

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10002",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSBS",
            employment_status=EmploymentStatus.PERMANENT,
            fte=0.8,
        )
    )

    # Peter → ASOSBSA → 0.5 FTE

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10003",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSBSA",
            employment_status=EmploymentStatus.PERMANENT,
            fte=0.5,
        )
    )

    result = get_workforce_by_department(
        as_of=date(2024, 1, 1),
    )

    assert result["ASOSB"].headcount == 1
    assert result["ASOSB"].fte == 1.0

    assert result["ASOSBS"].headcount == 1
    assert result["ASOSBS"].fte == 0.8

    assert result["ASOSBSA"].headcount == 1
    assert result["ASOSBSA"].fte == 0.5


def test_workforce_by_department_tree(test_database):
    with get_connection() as connection:
        for corp_id, first_name, last_name in [
            ("D10001", "Max", "Mustermann"),
            ("D10002", "Anna", "Musterfrau"),
            ("D10003", "Peter", "Muster"),
        ]:
            connection.execute(
                """
                INSERT INTO person (
                    corp_id,
                    first_name,
                    last_name
                )
                VALUES (?, ?, ?)
                """,
                (corp_id, first_name, last_name),
            )

        connection.execute(
            """
            INSERT INTO department (
                siglum,
                name,
                parent_siglum
            )
            VALUES (?, ?, ?)
            """,
            (
                "ASOSBSA",
                "A320 Engineering",
                "ASOSBS",
            ),
        )

    # Max → ASOSB → 1.0 FTE

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10001",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.PERMANENT,
            fte=1.0,
        )
    )

    # Anna → ASOSBS → 0.8 FTE

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10002",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSBS",
            employment_status=EmploymentStatus.PERMANENT,
            fte=0.8,
        )
    )

    # Peter → ASOSBSA → 0.5 FTE

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10003",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSBSA",
            employment_status=EmploymentStatus.PERMANENT,
            fte=0.5,
        )
    )

    result = get_workforce_by_department_tree(
        as_of=date(2024, 1, 1),
    )

    # ASOSB:
    # Max + Anna + Peter
    assert result["ASOSB"].headcount == 3
    assert result["ASOSB"].fte == 2.3

    # ASOSBS:
    # Anna + Peter
    assert result["ASOSBS"].headcount == 2
    assert result["ASOSBS"].fte == 1.3

    # ASOSBSA:
    # Peter
    assert result["ASOSBSA"].headcount == 1
    assert result["ASOSBSA"].fte == 0.5


def test_workforce_history(test_database):
    with get_connection() as connection:
        for corp_id, first_name, last_name in [
            ("D10001", "Max", "Mustermann"),
            ("D10002", "Anna", "Musterfrau"),
        ]:
            connection.execute(
                """
                INSERT INTO person (
                    corp_id,
                    first_name,
                    last_name
                )
                VALUES (?, ?, ?)
                """,
                (corp_id, first_name, last_name),
            )

    # Max kommt 2022 mit 1.0 FTE

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10001",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.PERMANENT,
            fte=1.0,
        )
    )

    # Anna kommt erst 2023 mit 0.8 FTE

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10002",
            effective_date=date(2023, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.PERMANENT,
            fte=0.8,
        )
    )

    history = get_workforce_history(
        dates=[
            date(2022, 1, 1),
            date(2023, 1, 1),
        ],
    )

    assert len(history) == 2

    assert history[0].as_of == date(2022, 1, 1)
    assert history[0].headcount == 1
    assert history[0].fte == 1.0

    assert history[1].as_of == date(2023, 1, 1)
    assert history[1].headcount == 2
    assert history[1].fte == 1.8


def test_calculate_workforce_changes():
    snapshots = [
        WorkforceSnapshot(
            as_of=date(2022, 1, 1),
            headcount=10,
            fte=8.0,
        ),
        WorkforceSnapshot(
            as_of=date(2023, 1, 1),
            headcount=12,
            fte=9.5,
        ),
        WorkforceSnapshot(
            as_of=date(2024, 1, 1),
            headcount=11,
            fte=9.0,
        ),
    ]

    changes = calculate_workforce_changes(
        snapshots,
    )

    assert len(changes) == 2

    assert changes[0].from_date == date(2022, 1, 1)
    assert changes[0].to_date == date(2023, 1, 1)
    assert changes[0].headcount_change == 2
    assert changes[0].fte_change == 1.5

    assert changes[1].from_date == date(2023, 1, 1)
    assert changes[1].to_date == date(2024, 1, 1)
    assert changes[1].headcount_change == -1
    assert changes[1].fte_change == -0.5


def test_get_workforce_movements(test_database):
    with get_connection() as connection:
        for corp_id, first_name, last_name in [
            ("D10001", "Max", "Mustermann"),
            ("D10002", "Anna", "Musterfrau"),
        ]:
            connection.execute(
                """
                INSERT INTO person (
                    corp_id,
                    first_name,
                    last_name
                )
                VALUES (?, ?, ?)
                """,
                (corp_id, first_name, last_name),
            )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10001",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.PERMANENT,
            fte=1.0,
        )
    )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10002",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.PERMANENT,
            fte=0.8,
        )
    )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10002",
            effective_date=date(2023, 6, 1),
            event_type=EventType.FTE_CHANGE,
            fte=0.5,
        )
    )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10001",
            effective_date=date(2023, 10, 1),
            event_type=EventType.EXIT,
        )
    )

    result = get_workforce_movements(
        from_date=date(2023, 1, 1),
        to_date=date(2023, 12, 31),
    )

    assert len(result) == 2

    assert result[0].corp_id == "D10002"
    assert result[0].effective_date == date(2023, 6, 1)
    assert result[0].event_type == EventType.FTE_CHANGE

    assert result[1].corp_id == "D10001"
    assert result[1].effective_date == date(2023, 10, 1)
    assert result[1].event_type == EventType.EXIT


def test_workforce_movement_contains_previous_state(test_database):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO person (
                corp_id,
                first_name,
                last_name
            )
            VALUES (?, ?, ?)
            """,
            ("D10001", "Max", "Mustermann"),
        )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10001",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.PERMANENT,
            fte=1.0,
        )
    )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10001",
            effective_date=date(2023, 10, 1),
            event_type=EventType.EXIT,
        )
    )

    result = get_workforce_movements(
        from_date=date(2023, 1, 1),
        to_date=date(2023, 12, 31),
    )

    assert len(result) == 1

    movement = result[0]

    assert movement.corp_id == "D10001"
    assert movement.event_type == EventType.EXIT
    assert movement.previous_location_code == "HAM"
    assert movement.previous_department_siglum == "ASOSB"
    assert movement.previous_job_code == "JOB_A"
    assert movement.previous_fte == 1.0

    assert movement.new_location_code is None
    assert movement.new_department_siglum is None
    assert movement.new_job_code is None
    assert movement.new_fte is None


def test_workforce_movement_contains_previous_and_new_fte(test_database):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO person (
                corp_id,
                first_name,
                last_name
            )
            VALUES (?, ?, ?)
            """,
            ("D10001", "Max", "Mustermann"),
        )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10001",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.PERMANENT,
            fte=1.0,
        )
    )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10001",
            effective_date=date(2023, 1, 1),
            event_type=EventType.FTE_CHANGE,
            fte=0.8,
        )
    )

    result = get_workforce_movements(
        from_date=date(2023, 1, 1),
        to_date=date(2023, 12, 31),
    )

    assert len(result) == 1

    movement = result[0]

    assert movement.corp_id == "D10001"
    assert movement.event_type == EventType.FTE_CHANGE

    assert movement.previous_fte == 1.0
    assert movement.new_fte == 0.8

    assert movement.previous_location_code == "HAM"
    assert movement.new_location_code == "HAM"

    assert movement.previous_department_siglum == "ASOSB"
    assert movement.new_department_siglum == "ASOSB"

    assert movement.previous_job_code == "JOB_A"
    assert movement.new_job_code == "JOB_A"


def test_workforce_movement_contains_previous_and_new_department(
    test_database,
):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO person (
                corp_id,
                first_name,
                last_name
            )
            VALUES (?, ?, ?)
            """,
            ("D10001", "Max", "Mustermann"),
        )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10001",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.PERMANENT,
            fte=1.0,
        )
    )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10001",
            effective_date=date(2023, 1, 1),
            event_type=EventType.TRANSFER,
            department_siglum="ASOSBS",
        )
    )

    result = get_workforce_movements(
        from_date=date(2023, 1, 1),
        to_date=date(2023, 12, 31),
    )

    assert len(result) == 1

    movement = result[0]

    assert movement.corp_id == "D10001"
    assert movement.event_type == EventType.TRANSFER

    # Zustand vorher
    assert movement.previous_department_siglum == "ASOSB"
    assert movement.previous_location_code == "HAM"
    assert movement.previous_job_code == "JOB_A"
    assert movement.previous_fte == 1.0

    # Zustand nachher
    assert movement.new_department_siglum == "ASOSBS"
    assert movement.new_location_code == "HAM"
    assert movement.new_job_code == "JOB_A"
    assert movement.new_fte == 1.0


def test_workforce_movement_contains_previous_and_new_location(
    test_database,
):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO person (
                corp_id,
                first_name,
                last_name
            )
            VALUES (?, ?, ?)
            """,
            ("D10001", "Max", "Mustermann"),
        )

        connection.execute(
            """
            INSERT INTO location (
                code,
                name
            )
            VALUES (?, ?)
            """,
            ("FRA", "Frankfurt"),
        )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10001",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.PERMANENT,
            fte=1.0,
        )
    )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10001",
            effective_date=date(2023, 1, 1),
            event_type=EventType.LOCATION_CHANGE,
            location_code="FRA",
        )
    )

    result = get_workforce_movements(
        from_date=date(2023, 1, 1),
        to_date=date(2023, 12, 31),
    )

    assert len(result) == 1

    movement = result[0]

    assert movement.corp_id == "D10001"
    assert movement.event_type == EventType.LOCATION_CHANGE

    # Zustand vorher
    assert movement.previous_location_code == "HAM"
    assert movement.previous_department_siglum == "ASOSB"
    assert movement.previous_job_code == "JOB_A"
    assert movement.previous_fte == 1.0

    # Zustand nachher
    assert movement.new_location_code == "FRA"
    assert movement.new_department_siglum == "ASOSB"
    assert movement.new_job_code == "JOB_A"
    assert movement.new_fte == 1.0


def test_workforce_movement_contains_previous_and_new_job(
    test_database,
):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO person (
                corp_id,
                first_name,
                last_name
            )
            VALUES (?, ?, ?)
            """,
            ("D10001", "Max", "Mustermann"),
        )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10001",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.PERMANENT,
            fte=1.0,
        )
    )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10001",
            effective_date=date(2023, 1, 1),
            event_type=EventType.JOB_CHANGE,
            job_code="JOB_B",
        )
    )

    result = get_workforce_movements(
        from_date=date(2023, 1, 1),
        to_date=date(2023, 12, 31),
    )

    assert len(result) == 1

    movement = result[0]

    assert movement.corp_id == "D10001"
    assert movement.event_type == EventType.JOB_CHANGE

    # Zustand vorher
    assert movement.previous_job_code == "JOB_A"
    assert movement.previous_location_code == "HAM"
    assert movement.previous_department_siglum == "ASOSB"
    assert movement.previous_fte == 1.0

    # Zustand nachher
    assert movement.new_job_code == "JOB_B"
    assert movement.new_location_code == "HAM"
    assert movement.new_department_siglum == "ASOSB"
    assert movement.new_fte == 1.0


def test_get_workforce_movement_summary(test_database):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO person (
                corp_id,
                first_name,
                last_name
            )
            VALUES (?, ?, ?)
            """,
            ("D10001", "Max", "Mustermann"),
        )
        connection.execute(
            """
    INSERT INTO person (
        corp_id,
        first_name,
        last_name
    )
    VALUES (?, ?, ?)
    """,
            ("D10003", "Peter", "Muster"),
        )

        connection.execute(
            """
            INSERT INTO person (
                corp_id,
                first_name,
                last_name
            )
            VALUES (?, ?, ?)
            """,
            ("D10002", "Anna", "Musterfrau"),
        )

    # Max: JOIN mit 1.0 FTE

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10001",
            effective_date=date(2023, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.PERMANENT,
            fte=1.0,
        )
    )

    # Anna: JOIN mit 0.8 FTE

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10002",
            effective_date=date(2023, 2, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.PERMANENT,
            fte=0.8,
        )
    )

    # Anna verlässt das Unternehmen mit 0.8 FTE

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10002",
            effective_date=date(2023, 10, 1),
            event_type=EventType.EXIT,
        )
    )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10003",
            effective_date=date(2023, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.PERMANENT,
            fte=0.5,
        )
    )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10003",
            effective_date=date(2023, 6, 1),
            event_type=EventType.TRANSFER,
            department_siglum="ASOSBS",
        )
    )

    result = get_workforce_movement_summary(
        from_date=date(2023, 1, 1),
        to_date=date(2023, 12, 31),
    )

    assert result.joins_headcount == 3
    assert result.joins_fte == 2.3

    assert result.exits_headcount == 1
    assert result.exits_fte == 0.8

    assert result.transfers_out_headcount == 1
    assert result.transfers_out_fte == 0.5

    assert result.transfers_in_headcount == 1
    assert result.transfers_in_fte == 0.5

    assert result.location_changes_out_headcount == 0
    assert result.location_changes_out_fte == 0.0

    assert result.location_changes_in_headcount == 0
    assert result.location_changes_in_fte == 0.0

    assert result.job_changes_headcount == 0
    assert result.job_changes_fte == 0.0

    assert result.fte_changes_headcount == 0


def test_workforce_movement_summary_location_filter(
    test_database,
):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO person (
                corp_id,
                first_name,
                last_name
            )
            VALUES (?, ?, ?)
            """,
            ("D10004", "Peter", "Muster"),
        )
        connection.execute(
            """
        INSERT INTO location (
            code,
            name
        )
        VALUES (?, ?)
        """,
            ("FRA", "Frankfurt"),
        )
    add_event(
        PersonEvent(
            id=None,
            corp_id="D10004",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.PERMANENT,
            fte=1.0,
        )
    )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10004",
            effective_date=date(2023, 1, 1),
            event_type=EventType.LOCATION_CHANGE,
            location_code="FRA",
        )
    )

    # ---------------------------------------------------------
    # Hamburg: Person verlässt den Standort
    # ---------------------------------------------------------

    result_ham = get_workforce_movement_summary(
        from_date=date(2023, 1, 1),
        to_date=date(2023, 12, 31),
        location_code="HAM",
    )

    assert result_ham.location_changes_out_headcount == 1
    assert result_ham.location_changes_out_fte == 1.0

    assert result_ham.location_changes_in_headcount == 0
    assert result_ham.location_changes_in_fte == 0.0

    # ---------------------------------------------------------
    # Frankfurt: Person kommt an den Standort
    # ---------------------------------------------------------

    result_fra = get_workforce_movement_summary(
        from_date=date(2023, 1, 1),
        to_date=date(2023, 12, 31),
        location_code="FRA",
    )

    assert result_fra.location_changes_out_headcount == 0
    assert result_fra.location_changes_out_fte == 0.0

    assert result_fra.location_changes_in_headcount == 1
    assert result_fra.location_changes_in_fte == 1.0


def test_workforce_movement_summary_department_filter_includes_children(
    test_database,
):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO person (
                corp_id,
                first_name,
                last_name
            )
            VALUES (?, ?, ?)
            """,
            ("D10005", "Peter", "Muster"),
        )
        connection.execute(
            """
    INSERT INTO department (
        siglum,
        name,
        parent_siglum
    )
    VALUES (?, ?, ?)
    """,
            (
                "ASOSBSA",
                "A320 Engineering",
                "ASOSBS",
            ),
        )

    # ---------------------------------------------------------
    # JOIN in ASOSBSA
    # ---------------------------------------------------------

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10005",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSBSA",
            employment_status=EmploymentStatus.PERMANENT,
            fte=0.8,
        )
    )

    # ---------------------------------------------------------
    # Transfer von ASOSBSA nach ASOSBL
    # ---------------------------------------------------------

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10005",
            effective_date=date(2023, 1, 1),
            event_type=EventType.TRANSFER,
            department_siglum="ASOSBL",
        )
    )

    # ---------------------------------------------------------
    # Filter auf ASOSB
    # ---------------------------------------------------------

    result = get_workforce_movement_summary(
        from_date=date(2023, 1, 1),
        to_date=date(2023, 12, 31),
        department_siglum="ASOSB",
    )

    # Person verlässt den ASOSB-Baum:
    # ASOSBSA → ASOSBL
    assert result.transfers_out_headcount == 1
    assert result.transfers_out_fte == 0.8

    # Person bleibt innerhalb des ASOSB-Baums:
    # ASOSBL ist ebenfalls Kind von ASOSB
    assert result.transfers_in_headcount == 1
    assert result.transfers_in_fte == 0.8


def test_workforce_movement_summary_department_filter_in_out(
    test_database,
):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO person (
                corp_id,
                first_name,
                last_name
            )
            VALUES (?, ?, ?)
            """,
            ("D10006", "Anna", "Muster"),
        )

        connection.execute(
            """
            INSERT INTO department (
                siglum,
                name,
                parent_siglum
            )
            VALUES (?, ?, ?)
            """,
            (
                "ASOSBSA",
                "A320 Engineering",
                "ASOSBS",
            ),
        )

        connection.execute(
            """
            INSERT INTO department (
                siglum,
                name,
                parent_siglum
            )
            VALUES (?, ?, ?)
            """,
            (
                "EXT",
                "External Department",
                None,
            ),
        )

    # ---------------------------------------------------------
    # JOIN außerhalb des ASOSB-Baums
    # ---------------------------------------------------------

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10006",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="EXT",
            employment_status=EmploymentStatus.PERMANENT,
            fte=0.5,
        )
    )

    # ---------------------------------------------------------
    # EXT → ASOSBSA
    # ---------------------------------------------------------

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10006",
            effective_date=date(2023, 1, 1),
            event_type=EventType.TRANSFER,
            department_siglum="ASOSBSA",
        )
    )

    result = get_workforce_movement_summary(
        from_date=date(2023, 1, 1),
        to_date=date(2023, 12, 31),
        department_siglum="ASOSB",
    )

    assert result.transfers_in_headcount == 1
    assert result.transfers_in_fte == 0.5

    assert result.transfers_out_headcount == 0
    assert result.transfers_out_fte == 0.0


def test_workforce_movement_summary_respects_date_range(
    test_database,
):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO person (
                corp_id,
                first_name,
                last_name
            )
            VALUES (?, ?, ?)
            """,
            ("D10007", "Max", "Mustermann"),
        )

        connection.execute(
            """
            INSERT INTO department (
                siglum,
                name,
                parent_siglum
            )
            VALUES (?, ?, ?)
            """,
            (
                "EXT2",
                "External Department 2",
                None,
            ),
        )

    # ---------------------------------------------------------
    # JOIN außerhalb des ASOSB-Baums
    # ---------------------------------------------------------

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10007",
            effective_date=date(2020, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="EXT2",
            employment_status=EmploymentStatus.PERMANENT,
            fte=1.0,
        )
    )

    # ---------------------------------------------------------
    # 2021: Eintritt in ASOSB
    # ---------------------------------------------------------

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10007",
            effective_date=date(2021, 1, 1),
            event_type=EventType.TRANSFER,
            department_siglum="ASOSB",
        )
    )

    # ---------------------------------------------------------
    # 2022: zurück nach außen
    # ---------------------------------------------------------

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10007",
            effective_date=date(2022, 1, 1),
            event_type=EventType.TRANSFER,
            department_siglum="EXT2",
        )
    )

    # ---------------------------------------------------------
    # 2023: wieder in ASOSB
    # ---------------------------------------------------------

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10007",
            effective_date=date(2023, 1, 1),
            event_type=EventType.TRANSFER,
            department_siglum="ASOSB",
        )
    )

    # ---------------------------------------------------------
    # Analysezeitraum: nur 2022
    # ---------------------------------------------------------

    result = get_workforce_movement_summary(
        from_date=date(2022, 1, 1),
        to_date=date(2022, 12, 31),
        department_siglum="ASOSB",
    )

    assert result.transfers_in_headcount == 0
    assert result.transfers_in_fte == 0.0

    assert result.transfers_out_headcount == 1
    assert result.transfers_out_fte == 1.0


def test_workforce_movement_summary_fte_change(
    test_database,
):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO person (
                corp_id,
                first_name,
                last_name
            )
            VALUES (?, ?, ?)
            """,
            ("D10008", "Laura", "Musterfrau"),
        )

    # ---------------------------------------------------------
    # JOIN
    # ---------------------------------------------------------

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10008",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.PERMANENT,
            fte=0.5,
        )
    )

    # ---------------------------------------------------------
    # FTE Change: 0.5 → 0.8
    # ---------------------------------------------------------

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10008",
            effective_date=date(2023, 1, 1),
            event_type=EventType.FTE_CHANGE,
            fte=0.8,
        )
    )

    result = get_workforce_movement_summary(
        from_date=date(2023, 1, 1),
        to_date=date(2023, 12, 31),
        department_siglum="ASOSB",
    )

    # FTE_CHANGE ist kein Join
    assert result.joins_headcount == 0
    assert result.joins_fte == 0.0

    # FTE_CHANGE ist kein Exit
    assert result.exits_headcount == 0
    assert result.exits_fte == 0.0

    # FTE_CHANGE ist kein Transfer
    assert result.transfers_in_headcount == 0
    assert result.transfers_in_fte == 0.0

    assert result.transfers_out_headcount == 0
    assert result.transfers_out_fte == 0.0

    # FTE Change selbst
    assert result.fte_changes_headcount == 1
    assert result.fte_changes_fte == pytest.approx(0.3)


def test_workforce_movement_summary_fte_change_net(
    test_database,
):
    with get_connection() as connection:
        connection.executemany(
            """
            INSERT INTO person (
                corp_id,
                first_name,
                last_name
            )
            VALUES (?, ?, ?)
            """,
            [
                ("D10009", "Max", "Mustermann"),
                ("D10010", "Anna", "Musterfrau"),
                ("D10011", "Peter", "Muster"),
            ],
        )

    # ---------------------------------------------------------
    # Max: 0.5 → 0.8 = +0.3
    # ---------------------------------------------------------

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10009",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.PERMANENT,
            fte=0.5,
        )
    )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10009",
            effective_date=date(2023, 1, 1),
            event_type=EventType.FTE_CHANGE,
            fte=0.8,
        )
    )

    # ---------------------------------------------------------
    # Anna: 1.0 → 0.7 = -0.3
    # ---------------------------------------------------------

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10010",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.PERMANENT,
            fte=1.0,
        )
    )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10010",
            effective_date=date(2023, 1, 1),
            event_type=EventType.FTE_CHANGE,
            fte=0.7,
        )
    )

    # ---------------------------------------------------------
    # Peter: 0.5 → 0.8 = +0.3
    # ---------------------------------------------------------

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10011",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status=EmploymentStatus.PERMANENT,
            fte=0.5,
        )
    )

    add_event(
        PersonEvent(
            id=None,
            corp_id="D10011",
            effective_date=date(2023, 1, 1),
            event_type=EventType.FTE_CHANGE,
            fte=0.8,
        )
    )

    # ---------------------------------------------------------
    # Analyse
    # ---------------------------------------------------------

    result = get_workforce_movement_summary(
        from_date=date(2023, 1, 1),
        to_date=date(2023, 12, 31),
        department_siglum="ASOSB",
    )

    assert result.fte_changes_headcount == 3
    assert result.fte_changes_fte == pytest.approx(0.3)
