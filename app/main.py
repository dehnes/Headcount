from datetime import date

from .database import initialize_database
from .events import get_person_state
from .seed import seed


def main() -> None:
    initialize_database()
    seed()

    dates = [
        date(2022, 6, 1),
        date(2023, 6, 1),
        date(2024, 6, 1),
        date(2024, 6, 15),
        date(2025, 6, 1),
        date(2025, 8, 1),
        date(2026, 2, 1),
    ]

    for as_of in dates:
        state = get_person_state(
            corp_id="D12345",
            as_of=as_of,
        )

        print()
        print(f"State on {as_of}")
        print("-" * 40)
        print(f"Person: {state.person.first_name} {state.person.last_name}")
        print(f"Department: {state.departmentsiglum}")
        print(f"Job: {state.job_code}")
        print(f"Location: {state.location_code}")
        print(f"Employment: {state.employment_status}")
        print(f"Leave: {state.leave_type}")


if __name__ == "__main__":
    main()
