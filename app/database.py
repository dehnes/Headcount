import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).parent.parent / "data" / "team.db"


def get_connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialize_database() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS person (
                corp_id TEXT PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS job (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS location (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS department (
                siglum TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                parent_siglum TEXT,
                FOREIGN KEY (parent_siglum)
                    REFERENCES department (siglum)
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS person_event (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                corp_id TEXT NOT NULL,
                effective_date TEXT NOT NULL,
                event_type TEXT NOT NULL,
                job_code TEXT,
                location_code TEXT,
                department_siglum TEXT,
                employment_status TEXT,
                leave_type TEXT,
                notes TEXT,
                fte REAL,

                FOREIGN KEY (corp_id)
                    REFERENCES person (corp_id),

                FOREIGN KEY (job_code)
                    REFERENCES job (code),

                FOREIGN KEY (location_code)
                    REFERENCES location (code),

                FOREIGN KEY (department_siglum)
                    REFERENCES department (siglum)
            )
            """
        )

        connection.commit()
