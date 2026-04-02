from sqlalchemy import Column, Integer, String
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
