from pathlib import Path

from app.db.database import Base, engine
from app.db import models  # noqa: F401 — registers models with metadata


def init_db():
    # Ensure the directory for the sqlite file exists when using a file-based URL
    try:
        db_path = engine.url.database
        if db_path:
            parent = Path(db_path).parent
            if not parent.exists():
                parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        # If we can't determine or create the directory, let SQLAlchemy raise the original error
        pass

    Base.metadata.create_all(bind=engine)
