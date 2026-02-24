import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.enums import DriverType
from app.schemas.benchmark import (
    BenchmarkRequest,
    BenchmarkResponse,
    BenchmarkDetailResponse,
    BenchmarkListResponse,
    BenchmarkListItem,
    DriverStats,
)
from app.services.benchmark_service import BenchmarkService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/benchmark", tags=["benchmark"])


@router.post("/compare", response_model=BenchmarkResponse, status_code=201)
async def run_benchmark(
    request: BenchmarkRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> BenchmarkResponse:
    logger.info(
        f"Running comparative benchmark with {request.profile.value} profile, "
        f"{request.runs_per_driver} runs per driver"
    )

    service = BenchmarkService(db)

    try:
        benchmark = await service.run_benchmark(
            profile=request.profile,
            runs_per_driver=request.runs_per_driver,
        )

        selenium_stats = DriverStats(
            avg_wpm=benchmark.selenium_avg_wpm,
            avg_browser_start_ms=benchmark.selenium_avg_browser_start,
            avg_memory_mb=benchmark.selenium_avg_memory_mb,
            avg_cpu_percent=benchmark.selenium_avg_cpu_percent,
            avg_accuracy=benchmark.selenium_avg_accuracy,
        )

        playwright_stats = DriverStats(
            avg_wpm=benchmark.playwright_avg_wpm,
            avg_browser_start_ms=benchmark.playwright_avg_browser_start,
            avg_memory_mb=benchmark.playwright_avg_memory_mb,
            avg_cpu_percent=benchmark.playwright_avg_cpu_percent,
            avg_accuracy=benchmark.playwright_avg_accuracy,
        )

        summary = service.generate_summary(benchmark)

        logger.info(
            f"Benchmark {benchmark.id} completed. Winner: {benchmark.winner.value if benchmark.winner else 'N/A'}. "
            f"Summary: {summary}"
        )

        return BenchmarkResponse(
            benchmark_id=benchmark.id,
            profile=benchmark.profile,
            status=benchmark.status,
            selenium=selenium_stats,
            playwright=playwright_stats,
            winner=benchmark.winner,
            summary=summary,
        )

    except Exception as e:
        logger.error(f"Error running benchmark: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to run benchmark: {str(e)}")


@router.get("", response_model=BenchmarkListResponse)
async def list_benchmarks(
    db: Annotated[AsyncSession, Depends(get_session)],
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=50, ge=1, le=100, description="Items per page"),
) -> BenchmarkListResponse:
    service = BenchmarkService(db)

    skip = (page - 1) * page_size

    benchmarks, total = await service.list_benchmarks(skip=skip, limit=page_size)

    items = [BenchmarkListItem.model_validate(b) for b in benchmarks]

    logger.info(f"Listing benchmarks: page {page}, {len(items)} items, {total} total")

    return BenchmarkListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{benchmark_id}", response_model=BenchmarkDetailResponse)
async def get_benchmark(
    benchmark_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> BenchmarkDetailResponse:
    service = BenchmarkService(db)

    benchmark = await service.get_benchmark(benchmark_id)

    if not benchmark:
        raise HTTPException(status_code=404, detail=f"Benchmark {benchmark_id} not found")

    selenium_session_ids = [
        s.id for s in benchmark.sessions if s.driver == DriverType.SELENIUM
    ]
    playwright_session_ids = [
        s.id for s in benchmark.sessions if s.driver == DriverType.PLAYWRIGHT
    ]

    logger.info(
        f"Retrieved benchmark {benchmark_id}: {benchmark.status.value}, "
        f"{len(selenium_session_ids)} Selenium + {len(playwright_session_ids)} Playwright sessions"
    )

    return BenchmarkDetailResponse(
        id=benchmark.id,
        profile=benchmark.profile,
        runs_per_driver=benchmark.runs_per_driver,
        status=benchmark.status,
        selenium_avg_wpm=benchmark.selenium_avg_wpm,
        selenium_avg_browser_start=benchmark.selenium_avg_browser_start,
        selenium_avg_memory_mb=benchmark.selenium_avg_memory_mb,
        selenium_avg_cpu_percent=benchmark.selenium_avg_cpu_percent,
        selenium_avg_accuracy=benchmark.selenium_avg_accuracy,
        playwright_avg_wpm=benchmark.playwright_avg_wpm,
        playwright_avg_browser_start=benchmark.playwright_avg_browser_start,
        playwright_avg_memory_mb=benchmark.playwright_avg_memory_mb,
        playwright_avg_cpu_percent=benchmark.playwright_avg_cpu_percent,
        playwright_avg_accuracy=benchmark.playwright_avg_accuracy,
        winner=benchmark.winner,
        selenium_session_ids=selenium_session_ids,
        playwright_session_ids=playwright_session_ids,
        created_at=benchmark.created_at,
        completed_at=benchmark.completed_at,
    )
