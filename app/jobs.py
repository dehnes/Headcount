from .database import get_connection
from .models import Job


def add_job(job: Job) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO job (code, name)
            VALUES (?, ?)
            """,
            (
                job.code,
                job.name,
            ),
        )

        connection.commit()


def get_all_jobs() -> list[Job]:
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT code, name
            FROM job
            ORDER BY name
            """).fetchall()

    return [
        Job(
            code=row["code"],
            name=row["name"],
        )
        for row in rows
    ]
