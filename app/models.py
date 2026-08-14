from dataclasses import dataclass
from datetime import date
from enum import Enum


class EmploymentStatus(str, Enum):
    TEMP = "TEMP"
    PERMANENT = "PERMANENT"


class LeaveType(str, Enum):
    PARENTAL = "PARENTAL"
    SABBATICAL = "SABBATICAL"


class PersonStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXITED = "EXITED"


@dataclass
class Person:
    corp_id: str
    first_name: str
    last_name: str


@dataclass
class Job:
    code: str
    name: str


@dataclass
class Location:
    code: str
    name: str


@dataclass
class Department:
    siglum: str
    name: str
    parent_siglum: str | None = None


class EventType(str, Enum):
    JOIN = "JOIN"
    TRANSFER = "TRANSFER"
    JOB_CHANGE = "JOB_CHANGE"
    LOCATION_CHANGE = "LOCATION_CHANGE"
    EMPLOYMENT_STATUS_CHANGE = "EMPLOYMENT_STATUS_CHANGE"
    LEAVE_START = "LEAVE_START"
    LEAVE_END = "LEAVE_END"
    EXIT = "EXIT"
    FTE_CHANGE = "FTE_CHANGE"


@dataclass
class PersonEvent:
    id: int | None
    corp_id: str
    effective_date: date
    event_type: EventType
    job_code: str | None = None
    location_code: str | None = None
    department_siglum: str | None = None
    employment_status: EmploymentStatus | None = None
    leave_type: LeaveType | None = None
    notes: str | None = None
    fte: float | None = None


@dataclass
class PersonState:
    person: Person
    status: PersonStatus = PersonStatus.EXITED
    department: Department | None = None
    job: Job | None = None
    location: Location | None = None
    employment_status: EmploymentStatus | None = None
    leave_type: LeaveType | None = None
    fte: float | None = None


@dataclass
class PersonHistoryEntry:
    event: PersonEvent
    job: Job | None = None
    location: Location | None = None
    department: Department | None = None


@dataclass
class PersonTimelineEntry:
    start_date: date
    end_date: date | None
    department: Department | None
    job: Job | None
    location: Location | None
    employment_status: EmploymentStatus | None
    leave_type: LeaveType | None


@dataclass
class WorkforceMetrics:
    headcount: int
    fte: float
