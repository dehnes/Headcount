from .database import get_connection
from .models import Location


def add_location(location: Location) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO location (code, name)
            VALUES (?, ?)
            """,
            (
                location.code,
                location.name,
            ),
        )

        connection.commit()


def get_all_locations() -> list[Location]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT code, name
            FROM location
            ORDER BY name
            """
        ).fetchall()

    return [
        Location(
            code=row["code"],
            name=row["name"],
        )
        for row in rows
    ]
