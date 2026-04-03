"""Transcription service using OpenAI Whisper API."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from loguru import logger

from app.core.config import OPENAI_API_KEY, RECORDINGS_DIR
from app.db.database import SessionLocal
from app.db.models import Recording

_MAX_SIZE_MB = 24


def _get_openai_client():
    from openai import OpenAI
    key = OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=key)


def _check_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _get_duration(file_path: Path) -> float:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)],
            capture_output=True, text=True, check=True,
        )
        return float(result.stdout.strip())
    except Exception as e:
        logger.warning(f"Could not determine duration: {e}")
        return 0.0


def _split_audio(audio_path: Path, temp_dir: Path) -> list[Path]:
    """Split an audio file into <24MB chunks using ffmpeg. Returns list of chunk paths."""
    file_size_mb = audio_path.stat().st_size / (1024 * 1024)
    if file_size_mb <= _MAX_SIZE_MB:
        return [audio_path]

    if not _check_ffmpeg():
        raise RuntimeError("ffmpeg not found. Install ffmpeg to handle files >24MB.")

    logger.info(f"Splitting {audio_path.name} ({file_size_mb:.1f}MB) into chunks…")
    duration = _get_duration(audio_path)
    if duration == 0:
        raise RuntimeError("Could not determine audio duration for splitting")

    num_chunks = int(file_size_mb / _MAX_SIZE_MB) + 1
    chunk_duration = duration / num_chunks
    chunks: list[Path] = []

    for i in range(num_chunks):
        chunk_path = temp_dir / f"chunk_{i + 1}{audio_path.suffix}"
        subprocess.run(
            ["ffmpeg", "-i", str(audio_path),
             "-ss", str(i * chunk_duration),
             "-t", str(chunk_duration),
             "-c", "copy", "-avoid_negative_ts", "1", str(chunk_path)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
        )
        chunks.append(chunk_path)
        logger.debug(f"  chunk {i + 1}/{num_chunks} ready")

    return chunks


def _transcribe_chunks(client, chunks: list[Path]) -> str:
    parts: list[str] = []
    for i, chunk in enumerate(chunks):
        logger.info(f"  Transcribing chunk {i + 1}/{len(chunks)}: {chunk.name}")
        with chunk.open("rb") as f:
            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="text",
            )
        parts.append(result if isinstance(result, str) else result.text)
    return "\n\n".join(parts)


def transcribe_recording(recording_id: int) -> None:
    """Background task: transcribe the audio file for a recording and update the DB."""
    db = SessionLocal()
    temp_dir: Path | None = None

    try:
        rec = db.get(Recording, recording_id)
        if not rec:
            logger.error(f"transcribe_recording: recording {recording_id} not found")
            return

        audio_path = Path(RECORDINGS_DIR) / rec.session_id / rec.audio_file
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        client = _get_openai_client()

        temp_dir = Path(tempfile.mkdtemp(prefix="rec_chunks_"))
        chunks = _split_audio(audio_path, temp_dir)

        logger.info(f"Transcribing {audio_path.name} ({len(chunks)} chunk(s)) …")
        transcript = _transcribe_chunks(client, chunks)

        # Write transcript to session directory
        transcript_path = audio_path.parent / "system_transcript.txt"
        transcript_path.write_text(transcript, encoding="utf-8")

        # Update DB
        rec.status = "transcribed"
        rec.transcript_text = transcript
        rec.error_message = None
        db.commit()
        logger.info(f"Transcription done for recording {recording_id} ({len(transcript)} chars)")

    except Exception as e:
        logger.error(f"Transcription failed for recording {recording_id}: {e}")
        try:
            rec = db.get(Recording, recording_id)
            if rec:
                rec.status = "error"
                rec.error_message = str(e)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
