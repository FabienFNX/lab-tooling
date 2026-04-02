import io
from typing import Any

import openpyxl
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Training
from app.schemas.training import TrainingCreate, TrainingRead, TrainingStats

router = APIRouter(prefix="/api/trainings", tags=["trainings"])

# Accepted column names (case-insensitive, with alias support)
_COL_MAP = {
    "trainee_name": "trainee_name",
    "trainee name": "trainee_name",
    "name": "trainee_name",
    "trainee_email": "trainee_email",
    "trainee email": "trainee_email",
    "email": "trainee_email",
    "training_title": "training_title",
    "training title": "training_title",
    "title": "training_title",
    "training_type": "training_type",
    "training type": "training_type",
    "type": "training_type",
    "status": "status",
    "start_date": "start_date",
    "start date": "start_date",
    "end_date": "end_date",
    "end date": "end_date",
    "score": "score",
    "notes": "notes",
    "comment": "notes",
    "comments": "notes",
}


@router.get("", response_model=list[TrainingRead])
def list_trainings(
    trainee_name: str | None = None,
    training_type: str | None = None,
    status: str | None = None,
    start_date_from: str | None = None,
    start_date_to: str | None = None,
    db: Session = Depends(get_db),
) -> list[Any]:
    q = db.query(Training)
    if trainee_name:
        q = q.filter(Training.trainee_name.ilike(f"%{trainee_name}%"))
    if training_type:
        q = q.filter(Training.training_type == training_type)
    if status:
        q = q.filter(Training.status == status)
    if start_date_from:
        q = q.filter(Training.start_date >= start_date_from)
    if start_date_to:
        q = q.filter(Training.start_date <= start_date_to)
    return q.order_by(Training.id.desc()).all()


@router.get("/stats", response_model=TrainingStats)
def get_stats(db: Session = Depends(get_db)) -> TrainingStats:
    rows = db.query(Training).all()
    total = len(rows)
    by_status: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for r in rows:
        by_status[r.status] = by_status.get(r.status, 0) + 1
        by_type[r.training_type] = by_type.get(r.training_type, 0) + 1

    completed = by_status.get("completed", 0)
    return TrainingStats(
        total=total,
        completed=completed,
        in_progress=by_status.get("in-progress", 0),
        planned=by_status.get("planned", 0),
        cancelled=by_status.get("cancelled", 0),
        completion_rate=round(completed / total * 100, 1) if total else 0.0,
        by_type=by_type,
        by_status=by_status,
    )


@router.post("", response_model=TrainingRead, status_code=201)
def create_training(payload: TrainingCreate, db: Session = Depends(get_db)) -> Training:
    record = Training(**payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/{training_id}", status_code=204)
def delete_training(training_id: int, db: Session = Depends(get_db)) -> None:
    record = db.query(Training).filter(Training.id == training_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Training record not found")
    db.delete(record)
    db.commit()


@router.post("/import-excel", response_model=list[TrainingRead], status_code=201)
async def import_excel(file: UploadFile, db: Session = Depends(get_db)) -> list[Training]:
    """Import training records from an Excel file (.xlsx).

    The first row must contain column headers (case-insensitive). Required columns:
    trainee_name, training_title, training_type. All other columns are optional.
    """
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only .xlsx and .xls files are supported")

    contents = await file.read()
    try:
        wb = openpyxl.load_workbook(io.BytesIO(contents), read_only=True, data_only=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Cannot parse Excel file: {exc}") from exc

    ws = wb.active
    if ws is None:
        raise HTTPException(status_code=400, detail="Excel file has no active worksheet")

    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        raise HTTPException(status_code=400, detail="Excel file must have a header row and at least one data row")

    # Map header names to field names
    raw_headers = [str(h).strip().lower() if h is not None else "" for h in rows[0]]
    field_index: dict[str, int] = {}
    for idx, raw in enumerate(raw_headers):
        mapped = _COL_MAP.get(raw)
        if mapped and mapped not in field_index:
            field_index[mapped] = idx

    required = {"trainee_name", "training_title", "training_type"}
    missing = required - field_index.keys()
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns: {', '.join(sorted(missing))}",
        )

    created: list[Training] = []
    for row_num, row in enumerate(rows[1:], start=2):
        def _cell(field: str) -> str | None:
            idx = field_index.get(field)
            if idx is None:
                return None
            val = row[idx] if idx < len(row) else None
            return str(val).strip() if val is not None else None

        trainee_name = _cell("trainee_name")
        training_title = _cell("training_title")
        training_type = _cell("training_type")

        # Skip blank rows
        if not trainee_name and not training_title and not training_type:
            continue
        if not trainee_name or not training_title or not training_type:
            raise HTTPException(
                status_code=400,
                detail=f"Row {row_num}: trainee_name, training_title and training_type are required",
            )

        score_raw = _cell("score")
        score: float | None = None
        if score_raw is not None:
            try:
                score = float(score_raw)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Row {row_num}: score '{score_raw}' is not a valid number",
                ) from None

        record = Training(
            trainee_name=trainee_name,
            trainee_email=_cell("trainee_email"),
            training_title=training_title,
            training_type=training_type,
            status=_cell("status") or "planned",
            start_date=_cell("start_date"),
            end_date=_cell("end_date"),
            score=score,
            notes=_cell("notes"),
        )
        db.add(record)
        created.append(record)

    db.commit()
    for r in created:
        db.refresh(r)
    return created
