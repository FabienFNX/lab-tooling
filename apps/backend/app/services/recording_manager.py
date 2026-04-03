"""Manages active recording sessions in-process using the recorder subpackage."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger
from sqlalchemy.orm import Session

from app.core.config import RECORDINGS_DIR
from app.db.models import Recording
from app.services.recorder.capture import LoopbackCapture, RecordingSession
from app.services.recorder.devices import DeviceManager
from app.services.recorder.util import get_iso_timestamp, get_timestamp
from app.services.recorder.writer import WavWriter

# Maps DB recording id → active RecordingSession
_active_sessions: dict[int, RecordingSession] = {}
# Maps DB recording id → session start ISO timestamp (for duration calc)
_session_start_times: dict[int, float] = {}


def _recordings_root() -> Path:
    root = Path(RECORDINGS_DIR)
    root.mkdir(parents=True, exist_ok=True)
    return root


def start_recording(db: Session, samplerate: int = 48000, channels: int = 2, blocksize: int = 2048) -> Recording:
    """
    Create a DB record, start the sounddevice capture session, and return the record.
    Raises RuntimeError if audio device is unavailable.
    """
    if sys.platform != "win32":
        raise RuntimeError("Backend-controlled recording is only supported on Windows (WASAPI).")

    session_id = get_timestamp()
    session_dir = _recordings_root() / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    audio_filename = "system.mp3"
    audio_path = session_dir / audio_filename

    # Create DB record first (so we have an id)
    now = datetime.now(timezone.utc)
    db_rec = Recording(
        session_id=session_id,
        status="recording",
        started_at=now,
        audio_file=audio_filename,
    )
    db.add(db_rec)
    db.commit()
    db.refresh(db_rec)

    try:
        device_idx, dev_channels = DeviceManager.get_speaker_loopback()
        actual_channels = min(channels, dev_channels)

        writer = WavWriter(
            path=audio_path,
            samplerate=samplerate,
            channels=actual_channels,
            file_format="MP3",
        )

        sys_capture = LoopbackCapture(
            device_idx=device_idx,
            channels=actual_channels,
            writer=writer,
            samplerate=samplerate,
            blocksize=blocksize,
        )

        session = RecordingSession(mic_capture=None, sys_capture=sys_capture)
        session.start()

        import time
        _active_sessions[db_rec.id] = session
        _session_start_times[db_rec.id] = time.perf_counter()

        logger.info(f"Recording started: session_id={session_id}, db_id={db_rec.id}")

    except Exception as e:
        db_rec.status = "error"
        db_rec.error_message = str(e)
        db.commit()
        raise

    return db_rec


def stop_recording(db: Session, db_id: int) -> Recording:
    """Stop the active recording session and update the DB record."""
    import time

    db_rec = db.get(Recording, db_id)
    if not db_rec:
        raise ValueError(f"Recording {db_id} not found")

    session = _active_sessions.pop(db_id, None)
    start_perf = _session_start_times.pop(db_id, None)

    if session is None:
        raise RuntimeError(f"No active recording session for id={db_id}")

    session.stop()

    duration = (time.perf_counter() - start_perf) if start_perf is not None else None

    db_rec.status = "stopped"
    db_rec.stopped_at = datetime.now(timezone.utc)
    if duration is not None:
        db_rec.duration_seconds = round(duration, 2)

    db.commit()
    db.refresh(db_rec)

    logger.info(f"Recording stopped: db_id={db_id}, duration={duration:.1f}s")
    return db_rec
