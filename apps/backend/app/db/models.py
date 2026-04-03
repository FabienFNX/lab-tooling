from sqlalchemy import CheckConstraint, Column, DateTime, Float, Integer, String, Text
from app.db.database import Base


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)


class BulkAddSelection(Base):
    """Single-row config table: stores which group/project IDs to target in bulk-add."""

    __tablename__ = "bulk_add_selection"

    id = Column(Integer, primary_key=True, default=1)
    group_ids = Column(String, nullable=False, default="[]")    # JSON array of ints
    project_ids = Column(String, nullable=False, default="[]")  # JSON array of ints


class Training(Base):
    """Stores individual training records for trainees."""

    __tablename__ = "trainings"
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 100", name="ck_training_score_range"),
    )

    id = Column(Integer, primary_key=True, index=True)
    trainee_name = Column(String, nullable=False)
    trainee_email = Column(String, nullable=True)
    training_title = Column(String, nullable=False)
    training_type = Column(String, nullable=False)          # e.g. onboarding, security, technical
    status = Column(String, nullable=False, default="planned")  # planned/in-progress/completed/cancelled
    start_date = Column(String, nullable=True)              # ISO date string YYYY-MM-DD (lexicographic sort works)
    end_date = Column(String, nullable=True)                # ISO date string YYYY-MM-DD
    score = Column(Float, nullable=True)                    # 0-100 enforced by CheckConstraint + Pydantic
    notes = Column(String, nullable=True)


class Recording(Base):
    """Stores audio recording sessions with their processing state."""

    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, nullable=False, index=True)   # YYYYMMDD_HHMMSS
    status = Column(String, nullable=False, default="recording")           # recording/stopped/transcribing/transcribed/processing/processed/error
    started_at = Column(DateTime, nullable=True)
    stopped_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    audio_file = Column(String, nullable=True)                             # filename within session dir
    transcript_text = Column(Text, nullable=True)
    processed_text = Column(Text, nullable=True)
    notion_page_id = Column(String, nullable=True)
    notion_url = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
