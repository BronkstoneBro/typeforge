import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.enums import SessionStatus
from app.schemas.session import (
    SessionRunRequest,
    SessionRunResponse,
    SessionDetailResponse,
    SessionListResponse,
    SessionListItem,
)
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/run", response_model=SessionRunResponse, status_code=201)
async def run_session(
    request: SessionRunRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> SessionRunResponse:
    logger.info(
        f"Running {request.runs} session(s) with {request.driver.value} driver "
        f"and {request.profile.value} profile"
    )

    service = SessionService(db)

    try:
        sessions = await service.run_session(
            driver=request.driver,
            profile=request.profile,
            runs=request.runs,
        )

        completed_sessions = [s for s in sessions if s.status == SessionStatus.COMPLETED]

        if not completed_sessions:
            return SessionRunResponse(
                session_ids=[s.id for s in sessions],
                status=SessionStatus.FAILED,
                avg_wpm=None,
                avg_accuracy=None,
            )

        avg_wpm = sum(s.wpm for s in completed_sessions if s.wpm) / len(completed_sessions)
        avg_accuracy = sum(s.accuracy for s in completed_sessions if s.accuracy) / len(completed_sessions)

        if len(completed_sessions) == len(sessions):
            overall_status = SessionStatus.COMPLETED
        elif completed_sessions:
            overall_status = SessionStatus.COMPLETED
        else:
            overall_status = SessionStatus.FAILED

        logger.info(
            f"Completed {len(completed_sessions)}/{len(sessions)} sessions. "
            f"Avg WPM: {avg_wpm:.1f}, Avg Accuracy: {avg_accuracy:.1f}%"
        )

        return SessionRunResponse(
            session_ids=[s.id for s in sessions],
            status=overall_status,
            avg_wpm=round(avg_wpm, 2),
            avg_accuracy=round(avg_accuracy, 2),
        )

    except Exception as e:
        logger.error(f"Error running session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to run session: {str(e)}")


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    db: Annotated[AsyncSession, Depends(get_session)],
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=50, ge=1, le=100, description="Items per page"),
) -> SessionListResponse:
    service = SessionService(db)

    skip = (page - 1) * page_size

    sessions, total = await service.list_sessions(skip=skip, limit=page_size)

    items = [SessionListItem.model_validate(s) for s in sessions]

    logger.info(f"Listing sessions: page {page}, {len(items)} items, {total} total")

    return SessionListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> SessionDetailResponse:
    service = SessionService(db)

    session = await service.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    logger.info(f"Retrieved session {session_id}: {session.status.value}")

    return SessionDetailResponse.model_validate(session)
