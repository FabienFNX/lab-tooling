"""API routes for audio recording management."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import RECORDINGS_DIR
from app.db.database import get_db
from app.db.models import Recording
from app.schemas.recording import ProcessRequest, RecordingRead
from app.services import recording_manager
from app.services.recorder.util import get_timestamp

router = APIRouter(prefix="/api/recordings", tags=["recordings"])

DbDep = Annotated[Session, Depends(get_db)]


def _get_recording_or_404(db: Session, recording_id: int) -> Recording:
    rec = db.get(Recording, recording_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recording {recording_id} not found")
    return rec


# ---------------------------------------------------------------------------
# List / detail
# ---------------------------------------------------------------------------

@router.get("/", response_model=list[RecordingRead])
def list_recordings(db: DbDep):
    return db.query(Recording).order_by(Recording.id.desc()).all()


@router.get("/{recording_id}", response_model=RecordingRead)
def get_recording(recording_id: int, db: DbDep):
    return _get_recording_or_404(db, recording_id)


# ---------------------------------------------------------------------------
# Start / stop (backend-controlled, Windows only)
# ---------------------------------------------------------------------------

@router.post("/start", response_model=RecordingRead, status_code=status.HTTP_201_CREATED)
def start_recording(db: DbDep):
    try:
        return recording_manager.start_recording(db)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start recording: {e}")


@router.post("/{recording_id}/stop", response_model=RecordingRead)
def stop_recording(recording_id: int, db: DbDep):
    rec = _get_recording_or_404(db, recording_id)
    if rec.status != "recording":
        raise HTTPException(status_code=409, detail=f"Recording is not active (status={rec.status})")
    try:
        return recording_manager.stop_recording(db, recording_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop recording: {e}")


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=RecordingRead, status_code=status.HTTP_201_CREATED)
async def upload_recording(db: DbDep, file: Annotated[UploadFile, File(description="Audio file (mp3, wav, m4a, …)")]):
    # Validate content type loosely
    allowed_prefixes = ("audio/", "video/")
    if file.content_type and not any(file.content_type.startswith(p) for p in allowed_prefixes):
        # Accept application/octet-stream as well (some clients send this)
        if file.content_type != "application/octet-stream":
            raise HTTPException(status_code=415, detail=f"Unsupported file type: {file.content_type}")

    session_id = get_timestamp()
    session_dir = Path(RECORDINGS_DIR) / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    safe_filename = f"uploaded_{Path(file.filename or 'audio').name}" if file.filename else "uploaded_audio"
    dest = session_dir / safe_filename

    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    now = datetime.now(timezone.utc)
    db_rec = Recording(
        session_id=session_id,
        status="stopped",
        started_at=now,
        stopped_at=now,
        audio_file=safe_filename,
    )
    db.add(db_rec)
    db.commit()
    db.refresh(db_rec)
    return db_rec


# ---------------------------------------------------------------------------
# Transcribe
# ---------------------------------------------------------------------------

@router.post("/{recording_id}/transcribe", response_model=RecordingRead)
def transcribe_recording(recording_id: int, db: DbDep, background_tasks: BackgroundTasks):
    from app.services.transcription import transcribe_recording as _transcribe

    rec = _get_recording_or_404(db, recording_id)
    if rec.status not in ("stopped", "transcribed", "error"):
        raise HTTPException(status_code=409, detail=f"Cannot transcribe from status={rec.status}")
    if not rec.audio_file:
        raise HTTPException(status_code=422, detail="No audio file associated with this recording")

    rec.status = "transcribing"
    rec.error_message = None
    db.commit()
    db.refresh(rec)

    background_tasks.add_task(_transcribe, recording_id)
    return rec


# ---------------------------------------------------------------------------
# Process (GPT summary + optional Notion push)
# ---------------------------------------------------------------------------

@router.post("/{recording_id}/process", response_model=RecordingRead)
def process_recording(recording_id: int, body: ProcessRequest, db: DbDep, background_tasks: BackgroundTasks):
    from app.services.processing import process_recording as _process

    rec = _get_recording_or_404(db, recording_id)
    if rec.status not in ("transcribed", "processed", "error"):
        raise HTTPException(status_code=409, detail=f"Cannot process from status={rec.status}")
    if not rec.transcript_text:
        raise HTTPException(status_code=422, detail="No transcript available. Transcribe first.")

    rec.status = "processing"
    rec.error_message = None
    if body.notion_page_id:
        rec.notion_page_id = body.notion_page_id
    db.commit()
    db.refresh(rec)

    background_tasks.add_task(_process, recording_id, body.notion_page_id)
    return rec


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@router.delete("/{recording_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recording(recording_id: int, db: DbDep):
    rec = _get_recording_or_404(db, recording_id)
    if rec.status == "recording":
        raise HTTPException(status_code=409, detail="Cannot delete an active recording. Stop it first.")
    db.delete(rec)
    db.commit()
