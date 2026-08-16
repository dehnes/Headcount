from .database import get_connection
from .models import Department, Job, Location, Person


def add_person(person: Person) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO person (corp_id, first_name, last_name)
            VALUES (?, ?, ?)
            """,
            (
                person.corp_id,
                person.first_name,
                person.last_name,
            ),
        )

        connection.commit()


def get_all_people() -> list[Person]:
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT corp_id, first_name, last_name
            FROM person
            ORDER BY last_name, first_name
            """).fetchall()

    return [
        Person(
            corp_id=row["corp_id"],
            first_name=row["first_name"],
            last_name=row["last_name"],
        )
        for row in rows
    ]


def get_job(code: str) -> Job | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT code, name
            FROM job
            WHERE code = ?
            """,
            (code,),
        ).fetchone()

    if row is None:
        return None

    return Job(
        code=row["code"],
        name=row["name"],
    )


def get_location(code: str) -> Location | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT code, name
            FROM location
            WHERE code = ?
            """,
            (code,),
        ).fetchone()

    if row is None:
        return None

    return Location(
        code=row["code"],
        name=row["name"],
    )


def get_department(siglum: str) -> Department | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                siglum,
                name,
                parent_siglum
            FROM department
            WHERE siglum = ?
            """,
            (siglum,),
        ).fetchone()

    if row is None:
        return None

    return Department(
        siglum=row["siglum"],
        name=row["name"],
        parent_siglum=row["parent_siglum"],
    )


def get_all_corp_ids() -> list[str]:
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT corp_id
            FROM person
            ORDER BY corp_id
            """).fetchall()

    return [row["corp_id"] for row in rows]
