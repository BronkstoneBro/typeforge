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
    def __init__(self, db: AsyncSession):
        self.db = db
        self.session_service = SessionService(db)

    async def run_benchmark(
        self,
        profile: TypingProfileType,
        runs_per_driver: int = 3
    ) -> BenchmarkRun:
        benchmark = BenchmarkRun(
            profile=profile,
            runs_per_driver=runs_per_driver,
            status=SessionStatus.PENDING
        )
        self.db.add(benchmark)
        await self.db.commit()
        await self.db.refresh(benchmark)

        try:
            benchmark.status = SessionStatus.RUNNING
            await self.db.commit()

            selenium_sessions = await self.session_service.run_session(
                driver=DriverType.SELENIUM,
                profile=profile,
                runs=runs_per_driver,
                benchmark_id=benchmark.id
            )

            playwright_sessions = await self.session_service.run_session(
                driver=DriverType.PLAYWRIGHT,
                profile=profile,
                runs=runs_per_driver,
                benchmark_id=benchmark.id
            )

            selenium_stats = self._aggregate_sessions(selenium_sessions)
            playwright_stats = self._aggregate_sessions(playwright_sessions)

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
        completed_sessions = [s for s in sessions if s.status == SessionStatus.COMPLETED]

        if not completed_sessions:
            return {
                'avg_wpm': None,
                'avg_browser_start': None,
                'avg_memory_mb': None,
                'avg_cpu_percent': None,
                'avg_accuracy': None,
            }

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
        selenium_wpm = selenium_stats.get('avg_wpm')
        playwright_wpm = playwright_stats.get('avg_wpm')

        if selenium_wpm is None or playwright_wpm is None:
            return WinnerType.TIE

        diff = abs(selenium_wpm - playwright_wpm)
        threshold = 0.5

        if diff < threshold:
            return WinnerType.TIE
        elif selenium_wpm > playwright_wpm:
            return WinnerType.SELENIUM
        else:
            return WinnerType.PLAYWRIGHT

    def generate_summary(self, benchmark: BenchmarkRun) -> str:
        if benchmark.winner == WinnerType.TIE:
            return "Results are nearly identical"

        winner_name = "Playwright" if benchmark.winner == WinnerType.PLAYWRIGHT else "Selenium"

        summary_parts = []

        winner_start = (benchmark.playwright_avg_browser_start
                       if benchmark.winner == WinnerType.PLAYWRIGHT
                       else benchmark.selenium_avg_browser_start)
        loser_start = (benchmark.selenium_avg_browser_start
                      if benchmark.winner == WinnerType.PLAYWRIGHT
                      else benchmark.playwright_avg_browser_start)

        if winner_start and loser_start and loser_start > 0:
            ratio = loser_start / winner_start
            if ratio > 1.1:
                summary_parts.append(f"started {ratio:.1f}x faster")

        winner_mem = (benchmark.playwright_avg_memory_mb
                     if benchmark.winner == WinnerType.PLAYWRIGHT
                     else benchmark.selenium_avg_memory_mb)
        loser_mem = (benchmark.selenium_avg_memory_mb
                    if benchmark.winner == WinnerType.PLAYWRIGHT
                    else benchmark.playwright_avg_memory_mb)

        if winner_mem and loser_mem and loser_mem > 0:
            percent_diff = ((loser_mem - winner_mem) / loser_mem) * 100
            if percent_diff > 5:
                summary_parts.append(f"used {percent_diff:.0f}% less memory")

        winner_cpu = (benchmark.playwright_avg_cpu_percent
                     if benchmark.winner == WinnerType.PLAYWRIGHT
                     else benchmark.selenium_avg_cpu_percent)
        loser_cpu = (benchmark.selenium_avg_cpu_percent
                    if benchmark.winner == WinnerType.PLAYWRIGHT
                    else benchmark.playwright_avg_cpu_percent)

        if winner_cpu and loser_cpu and loser_cpu > 0:
            percent_diff = ((loser_cpu - winner_cpu) / loser_cpu) * 100
            if percent_diff > 10:
                summary_parts.append(f"used {percent_diff:.0f}% less CPU")

        if summary_parts:
            return f"{winner_name} " + ", ".join(summary_parts)
        else:
            return f"{winner_name} had better WPM"

    async def get_benchmark(self, benchmark_id: uuid.UUID) -> BenchmarkRun | None:
        result = await self.db.execute(
            select(BenchmarkRun).where(BenchmarkRun.id == benchmark_id)
        )
        return result.scalar_one_or_none()

    async def list_benchmarks(
        self,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[BenchmarkRun], int]:
        count_result = await self.db.execute(
            select(func.count(BenchmarkRun.id))
        )
        total = count_result.scalar()

        result = await self.db.execute(
            select(BenchmarkRun)
            .order_by(BenchmarkRun.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        benchmarks = list(result.scalars().all())

        return benchmarks, total
