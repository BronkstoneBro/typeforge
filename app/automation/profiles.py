import asyncio
import random

from app.models.enums import TypingProfileType


async def keystroke_delay(profile: TypingProfileType) -> None:
    delays = {
        TypingProfileType.BEGINNER:     (0.200, 0.080),
        TypingProfileType.INTERMEDIATE: (0.100, 0.030),
        TypingProfileType.EXPERT:       (0.050, 0.015),
        TypingProfileType.ROBOT:        (0.0,   0.0),
    }

    base, jitter = delays[profile]
    delay = max(0, base + random.uniform(-jitter, jitter))

    if delay > 0:
        await asyncio.sleep(delay)


def word_pause(profile: TypingProfileType) -> float:
    pauses = {
        TypingProfileType.BEGINNER:     (0.3, 1.0),
        TypingProfileType.INTERMEDIATE: (0.05, 0.15),
        TypingProfileType.EXPERT:       (0.0, 0.02),
        TypingProfileType.ROBOT:        (0.0, 0.0),
    }

    lo, hi = pauses[profile]
    return random.uniform(lo, hi)


def get_profile_description(profile: TypingProfileType) -> str:
    descriptions = {
        TypingProfileType.BEGINNER: "Slow typing with frequent pauses (200ms ±80ms per key)",
        TypingProfileType.INTERMEDIATE: "Moderate speed with small pauses (100ms ±30ms per key)",
        TypingProfileType.EXPERT: "Fast and consistent typing (50ms ±15ms per key)",
        TypingProfileType.ROBOT: "Maximum speed, no delays (instant typing)",
    }

    return descriptions[profile]
