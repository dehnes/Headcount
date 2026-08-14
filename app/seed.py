from datetime import date

from .database import get_connection
from .models import EventType, PersonEvent


def seed() -> None:
    with get_connection() as connection:
        # Person
        connection.execute(
            """
            INSERT OR IGNORE INTO person (
                corp_id,
                first_name,
                last_name
            )
            VALUES (?, ?, ?)
            """,
            (
                "D12345",
                "Max",
                "Mustermann",
            ),
        )

        # Jobs
        jobs = [
            ("JOB_A", "Job A"),
            ("JOB_B", "Job B"),
        ]

        connection.executemany(
            """
            INSERT OR IGNORE INTO job (code, name)
            VALUES (?, ?)
            """,
            jobs,
        )

        # Locations
        locations = [
            ("HAM", "Hamburg"),
        ]

        connection.executemany(
            """
            INSERT OR IGNORE INTO location (code, name)
            VALUES (?, ?)
            """,
            locations,
        )

        # Departments
        departments = [
            (
                "ASOSB",
                "Retrofit Operations",
                None,
            ),
            (
                "ASOSBS",
                "Retrofit Operations A320",
                "ASOSB",
            ),
            (
                "ASOSBL",
                "Retrofit Operations A350",
                "ASOSB",
            ),
        ]

        connection.executemany(
            """
            INSERT OR IGNORE INTO department (
                siglum,
                name,
                parent_siglum
            )
            VALUES (?, ?, ?)
            """,
            departments,
        )

        connection.commit()

        seed_events()


def seed_events() -> None:
    events = [
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2022, 1, 1),
            event_type=EventType.JOIN,
            job_code="JOB_A",
            location_code="HAM",
            department_siglum="ASOSB",
            employment_status="TEMP",
            notes="Joined company as temporary employee",
        ),
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2023, 1, 1),
            event_type=EventType.JOB_CHANGE,
            job_code="JOB_B",
            notes="Changed from Job A to Job B",
        ),
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2024, 6, 15),
            event_type=EventType.TRANSFER,
            department_siglum="ASOSBS",
            notes="Transferred to A320 team",
        ),
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2025, 1, 1),
            event_type=EventType.EMPLOYMENT_STATUS_CHANGE,
            employment_status="PERMANENT",
            notes="Converted from temporary to permanent employee",
        ),
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2025, 7, 1),
            event_type=EventType.LEAVE_START,
            leave_type="PARENTAL",
            notes="Started parental leave",
        ),
        PersonEvent(
            id=None,
            corp_id="D12345",
            effective_date=date(2026, 1, 1),
            event_type=EventType.LEAVE_END,
            leave_type="PARENTAL",
            notes="Returned from parental leave",
        ),
    ]

    with get_connection() as connection:
        for event in events:
            connection.execute(
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
                    notes
                )
                SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM person_event
                    WHERE corp_id = ?
                      AND effective_date = ?
                      AND event_type = ?
                )
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
                    event.corp_id,
                    event.effective_date.isoformat(),
                    event.event_type.value,
                ),
            )

        connection.commit()
