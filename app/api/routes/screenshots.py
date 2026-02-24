import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/screenshots", tags=["screenshots"])


@router.get("/{filename}")
async def get_screenshot(filename: str) -> FileResponse:
    if ".." in filename or "/" in filename or "\\" in filename:
        logger.warning(f"Invalid filename requested: {filename}")
        raise HTTPException(status_code=400, detail="Invalid filename")

    screenshots_dir = Path(settings.SCREENSHOTS_DIR)
    file_path = screenshots_dir / filename

    if not file_path.exists() or not file_path.is_file():
        logger.warning(f"Screenshot not found: {file_path}")
        raise HTTPException(status_code=404, detail=f"Screenshot {filename} not found")

    try:
        file_path.resolve().relative_to(screenshots_dir.resolve())
    except ValueError:
        logger.error(f"Path traversal attempt detected: {filename}")
        raise HTTPException(status_code=403, detail="Access denied")

    logger.info(f"Serving screenshot: {filename}")

    return FileResponse(
        path=str(file_path),
        media_type="image/png",
        filename=filename,
    )
