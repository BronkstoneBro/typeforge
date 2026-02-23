import uuid
from datetime import datetime, timezone
from typing import List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import BotSession
from app.models.enums import DriverType, TypingProfileType, SessionStatus
from app.automation.selenium_driver import SeleniumTypingDriver
from app.automation.playwright_driver import PlaywrightTypingDriver
from app.automation.base_driver import TypingResult


class SessionService:
    """Service for managing bot typing sessions"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_session(
        self,
        driver: DriverType,
        profile: TypingProfileType,
        runs: int = 1,
        benchmark_id: uuid.UUID | None = None
    ) -> List[BotSession]:
        """
        Run typing session(s) with the specified driver and profile.

        Args:
            driver: Type of driver to use (selenium or playwright)
            profile: Typing profile (beginner, intermediate, expert, robot)
            runs: Number of times to run the session
            benchmark_id: Optional benchmark ID to associate sessions with

        Returns:
            List of completed BotSession records
        """
        sessions = []

        # Create driver instance
        if driver == DriverType.SELENIUM:
            typing_driver = SeleniumTypingDriver()
        else:
            typing_driver = PlaywrightTypingDriver()

        for _ in range(runs):
            # Create session record
            session = BotSession(
                driver=driver,
                profile=profile,
                status=SessionStatus.PENDING,
                benchmark_id=benchmark_id
            )
            self.db.add(session)
            await self.db.commit()
            await self.db.refresh(session)

            try:
                # Update status to running
                session.status = SessionStatus.RUNNING
                await self.db.commit()

                # Run the driver
                result: TypingResult = await typing_driver.run(profile)

                # Update session with results
                session.wpm = result.wpm
                session.accuracy = result.accuracy
                session.duration_sec = result.duration_sec
                session.browser_start_ms = result.browser_start_ms
                session.peak_memory_mb = result.peak_memory_mb
                session.peak_cpu_percent = result.peak_cpu_percent
                session.screenshot_before = result.screenshot_before
                session.screenshot_after = result.screenshot_after
                session.status = SessionStatus.COMPLETED
                session.completed_at = datetime.now(timezone.utc)

                await self.db.commit()
                await self.db.refresh(session)

            except Exception as e:
                session.status = SessionStatus.FAILED
                session.error_message = str(e)
                session.completed_at = datetime.now(timezone.utc)
                await self.db.commit()
                await self.db.refresh(session)

            sessions.append(session)

        return sessions

    async def get_session(self, session_id: uuid.UUID) -> BotSession | None:
        """Get a single session by ID"""
        result = await self.db.execute(
            select(BotSession).where(BotSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def list_sessions(
        self,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[BotSession], int]:
        """
        List sessions with pagination.

        Returns:
            Tuple of (sessions list, total count)
        """
        # Get total count
        count_result = await self.db.execute(
            select(func.count(BotSession.id))
        )
        total = count_result.scalar()

        # Get sessions
        result = await self.db.execute(
            select(BotSession)
            .order_by(BotSession.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        sessions = list(result.scalars().all())

        return sessions, total
