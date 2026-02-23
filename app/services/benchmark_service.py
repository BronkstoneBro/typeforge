import uuid
from datetime import datetime, timezone
from typing import List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.benchmark import BenchmarkRun
from app.models.session import BotSession
from app.models.enums import DriverType, TypingProfileType, SessionStatus, WinnerType
from app.services.session_service import SessionService


class BenchmarkService:
    """Service for managing comparative benchmarks"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.session_service = SessionService(db)

    async def run_benchmark(
        self,
        profile: TypingProfileType,
        runs_per_driver: int = 3
    ) -> BenchmarkRun:
        """
        Run comparative benchmark: both drivers with the same profile.

        Args:
            profile: Typing profile to use for both drivers
            runs_per_driver: Number of times to run each driver

        Returns:
            BenchmarkRun record with aggregated results
        """
        # Create benchmark record
        benchmark = BenchmarkRun(
            profile=profile,
            runs_per_driver=runs_per_driver,
            status=SessionStatus.PENDING
        )
        self.db.add(benchmark)
        await self.db.commit()
        await self.db.refresh(benchmark)

        try:
            # Update status to running
            benchmark.status = SessionStatus.RUNNING
            await self.db.commit()

            # Run Selenium sessions
            selenium_sessions = await self.session_service.run_session(
                driver=DriverType.SELENIUM,
                profile=profile,
                runs=runs_per_driver,
                benchmark_id=benchmark.id
            )

            # Run Playwright sessions
            playwright_sessions = await self.session_service.run_session(
                driver=DriverType.PLAYWRIGHT,
                profile=profile,
                runs=runs_per_driver,
                benchmark_id=benchmark.id
            )

            # Aggregate results
            selenium_stats = self._aggregate_sessions(selenium_sessions)
            playwright_stats = self._aggregate_sessions(playwright_sessions)

            # Update benchmark with aggregated data
            benchmark.selenium_avg_wpm = selenium_stats['avg_wpm']
            benchmark.selenium_avg_browser_start = selenium_stats['avg_browser_start']
            benchmark.selenium_avg_memory_mb = selenium_stats['avg_memory_mb']
            benchmark.selenium_avg_cpu_percent = selenium_stats['avg_cpu_percent']
            benchmark.selenium_avg_accuracy = selenium_stats['avg_accuracy']

            benchmark.playwright_avg_wpm = playwright_stats['avg_wpm']
            benchmark.playwright_avg_browser_start = playwright_stats['avg_browser_start']
            benchmark.playwright_avg_memory_mb = playwright_stats['avg_memory_mb']
            benchmark.playwright_avg_cpu_percent = playwright_stats['avg_cpu_percent']
            benchmark.playwright_avg_accuracy = playwright_stats['avg_accuracy']

            # Determine winner
            benchmark.winner = self._determine_winner(selenium_stats, playwright_stats)
            benchmark.status = SessionStatus.COMPLETED
            benchmark.completed_at = datetime.now(timezone.utc)

            await self.db.commit()
            await self.db.refresh(benchmark)

        except Exception as e:
            benchmark.status = SessionStatus.FAILED
            benchmark.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self.db.refresh(benchmark)
            raise

        return benchmark

    def _aggregate_sessions(self, sessions: List[BotSession]) -> dict:
        """Aggregate metrics from multiple sessions"""
        completed_sessions = [s for s in sessions if s.status == SessionStatus.COMPLETED]

        if not completed_sessions:
            return {
                'avg_wpm': None,
                'avg_browser_start': None,
                'avg_memory_mb': None,
                'avg_cpu_percent': None,
                'avg_accuracy': None,
            }

        total = len(completed_sessions)

        # Calculate averages only from non-None values
        def safe_avg(values):
            non_none = [v for v in values if v is not None]
            return sum(non_none) / len(non_none) if non_none else None

        return {
            'avg_wpm': safe_avg([s.wpm for s in completed_sessions]),
            'avg_browser_start': safe_avg([s.browser_start_ms for s in completed_sessions]),
            'avg_memory_mb': safe_avg([s.peak_memory_mb for s in completed_sessions]),
            'avg_cpu_percent': safe_avg([s.peak_cpu_percent for s in completed_sessions]),
            'avg_accuracy': safe_avg([s.accuracy for s in completed_sessions]),
        }

    def _determine_winner(self, selenium_stats: dict, playwright_stats: dict) -> WinnerType:
        """
        Determine winner based on WPM (primary metric).
        A tie is declared if difference is less than 0.5 WPM.
        """
        selenium_wpm = selenium_stats.get('avg_wpm')
        playwright_wpm = playwright_stats.get('avg_wpm')

        if selenium_wpm is None or playwright_wpm is None:
            return WinnerType.TIE

        diff = abs(selenium_wpm - playwright_wpm)
        threshold = 0.5  # Consider tie if difference < 0.5 WPM

        if diff < threshold:
            return WinnerType.TIE
        elif selenium_wpm > playwright_wpm:
            return WinnerType.SELENIUM
        else:
            return WinnerType.PLAYWRIGHT

    def generate_summary(self, benchmark: BenchmarkRun) -> str:
        """
        Generate human-readable summary comparing the two drivers.

        Example: "Playwright запустился в 2.6x быстрее, потребил на 23% меньше памяти"
        """
        if benchmark.winner == WinnerType.TIE:
            return "Результаты практически идентичны — ничья"

        # Determine winner name
        winner_name = "Playwright" if benchmark.winner == WinnerType.PLAYWRIGHT else "Selenium"
        loser_name = "Selenium" if benchmark.winner == WinnerType.PLAYWRIGHT else "Playwright"

        summary_parts = []

        # Browser startup time comparison
        winner_start = (benchmark.playwright_avg_browser_start
                       if benchmark.winner == WinnerType.PLAYWRIGHT
                       else benchmark.selenium_avg_browser_start)
        loser_start = (benchmark.selenium_avg_browser_start
                      if benchmark.winner == WinnerType.PLAYWRIGHT
                      else benchmark.playwright_avg_browser_start)

        if winner_start and loser_start and loser_start > 0:
            ratio = loser_start / winner_start
            if ratio > 1.1:  # Only mention if > 10% difference
                summary_parts.append(f"запустился в {ratio:.1f}x быстрее")

        # Memory usage comparison
        winner_mem = (benchmark.playwright_avg_memory_mb
                     if benchmark.winner == WinnerType.PLAYWRIGHT
                     else benchmark.selenium_avg_memory_mb)
        loser_mem = (benchmark.selenium_avg_memory_mb
                    if benchmark.winner == WinnerType.PLAYWRIGHT
                    else benchmark.playwright_avg_memory_mb)

        if winner_mem and loser_mem and loser_mem > 0:
            percent_diff = ((loser_mem - winner_mem) / loser_mem) * 100
            if percent_diff > 5:  # Only mention if > 5% difference
                summary_parts.append(f"потребил на {percent_diff:.0f}% меньше памяти")

        # CPU usage comparison
        winner_cpu = (benchmark.playwright_avg_cpu_percent
                     if benchmark.winner == WinnerType.PLAYWRIGHT
                     else benchmark.selenium_avg_cpu_percent)
        loser_cpu = (benchmark.selenium_avg_cpu_percent
                    if benchmark.winner == WinnerType.PLAYWRIGHT
                    else benchmark.playwright_avg_cpu_percent)

        if winner_cpu and loser_cpu and loser_cpu > 0:
            percent_diff = ((loser_cpu - winner_cpu) / loser_cpu) * 100
            if percent_diff > 10:  # Only mention if > 10% difference
                summary_parts.append(f"использовал на {percent_diff:.0f}% меньше CPU")

        if summary_parts:
            return f"{winner_name} " + ", ".join(summary_parts)
        else:
            return f"{winner_name} показал лучший результат по WPM"

    async def get_benchmark(self, benchmark_id: uuid.UUID) -> BenchmarkRun | None:
        """Get a single benchmark by ID"""
        result = await self.db.execute(
            select(BenchmarkRun).where(BenchmarkRun.id == benchmark_id)
        )
        return result.scalar_one_or_none()

    async def list_benchmarks(
        self,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[BenchmarkRun], int]:
        """
        List benchmarks with pagination.

        Returns:
            Tuple of (benchmarks list, total count)
        """
        # Get total count
        count_result = await self.db.execute(
            select(func.count(BenchmarkRun.id))
        )
        total = count_result.scalar()

        # Get benchmarks
        result = await self.db.execute(
            select(BenchmarkRun)
            .order_by(BenchmarkRun.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        benchmarks = list(result.scalars().all())

        return benchmarks, total
