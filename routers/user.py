from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import SessionLocal
import model as models, schemas

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/users/", response_model=schemas.UserCreate)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = models.User(name=user.name, email=user.email, plan="free")
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/spending/", response_model=schemas.SpendingLogOut)
def create_spending_log(log: schemas.SpendingLogCreate, db: Session = Depends(get_db)):
    db_log = models.SpendingLog(
        user_id=log.user_id,
        item_name=log.item_name,
        amount=log.amount,
        decision=log.decision,
        category=log.category,
        comment=log.comment
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

@router.get("/spending/{user_id}", response_model=list[schemas.SpendingLogOut])
def get_spending_logs(user_id: int, db: Session = Depends(get_db)):
    logs = db.query(models.SpendingLog).filter(models.SpendingLog.user_id == user_id).all()
    return logs
