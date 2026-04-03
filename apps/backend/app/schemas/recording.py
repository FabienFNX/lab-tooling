from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

VALID_STATUSES = {
    "recording",
    "stopped",
    "transcribing",
    "transcribed",
    "processing",
    "processed",
    "error",
}


class RecordingRead(BaseModel):
    id: int
    session_id: str
    status: str
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    duration_seconds: float | None = None
    audio_file: str | None = None
    transcript_text: str | None = None
    processed_text: str | None = None
    notion_page_id: str | None = None
    notion_url: str | None = None
    error_message: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ProcessRequest(BaseModel):
    notion_page_id: str | None = None
