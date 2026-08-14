import pytest

from app.database import get_connection, initialize_database


@pytest.fixture
def test_database(tmp_path, monkeypatch):
    database_path = tmp_path / "test.db"

    monkeypatch.setattr(
        "app.database.DATABASE_PATH",
        database_path,
    )

    initialize_database()

    with get_connection() as connection:
        # Person
        connection.execute(
            """
            INSERT INTO person (
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
            INSERT INTO job (
                code,
                name
            )
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
            INSERT INTO location (
                code,
                name
            )
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
            INSERT INTO department (
                siglum,
                name,
                parent_siglum
            )
            VALUES (?, ?, ?)
            """,
            departments,
        )

        connection.commit()

    return database_path
