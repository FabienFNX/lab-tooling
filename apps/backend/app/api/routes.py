from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Item
from app.schemas.item import ItemCreate, ItemRead

router = APIRouter(prefix="/api")


@router.get("/items", response_model=list[ItemRead])
def get_items(db: Session = Depends(get_db)):
    return db.query(Item).all()


@router.post("/items", response_model=ItemRead, status_code=201)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    db_item = Item(name=item.name, description=item.description)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item
