from app.db.database import Base, engine
from app.db import models  # noqa: F401 — registers models with metadata


def init_db():
    Base.metadata.create_all(bind=engine)
