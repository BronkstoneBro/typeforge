from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.models.enums import TypingProfileType


@dataclass
class TypingResult:
    wpm: float
    accuracy: float
    duration_sec: float
    browser_start_ms: float
    peak_memory_mb: float
    peak_cpu_percent: float
    screenshot_before: str
    screenshot_after: str


class TypingDriver(ABC):
    @abstractmethod
    async def run(self, profile: TypingProfileType) -> TypingResult:
        ...
