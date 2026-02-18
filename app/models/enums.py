import enum


class DriverType(str, enum.Enum):
    SELENIUM = "selenium"
    PLAYWRIGHT = "playwright"


class TypingProfileType(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"
    ROBOT = "robot"


class SessionStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class WinnerType(str, enum.Enum):
    SELENIUM = "selenium"
    PLAYWRIGHT = "playwright"
    TIE = "tie"
