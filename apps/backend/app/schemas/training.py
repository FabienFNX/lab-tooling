from pydantic import BaseModel, ConfigDict, Field, field_validator

VALID_STATUSES = {"planned", "in-progress", "completed", "cancelled"}
VALID_TRAINING_TYPES = {"onboarding", "security", "technical", "soft-skills", "compliance", "other"}


class TrainingBase(BaseModel):
    trainee_name: str
    trainee_email: str | None = None
    training_title: str
    training_type: str
    status: str = "planned"
    start_date: str | None = None  # ISO date string YYYY-MM-DD
    end_date: str | None = None    # ISO date string YYYY-MM-DD
    score: float | None = Field(default=None, ge=0, le=100)
    notes: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_STATUSES)}")
        return v

    @field_validator("training_type")
    @classmethod
    def validate_training_type(cls, v: str) -> str:
        if v not in VALID_TRAINING_TYPES:
            raise ValueError(f"training_type must be one of {sorted(VALID_TRAINING_TYPES)}")
        return v


class TrainingCreate(TrainingBase):
    pass


class TrainingRead(TrainingBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class TrainingStats(BaseModel):
    total: int
    completed: int
    in_progress: int
    planned: int
    cancelled: int
    completion_rate: float
    by_type: dict[str, int]
    by_status: dict[str, int]
