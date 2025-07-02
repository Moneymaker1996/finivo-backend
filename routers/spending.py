from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import SessionLocal
import model as models, schemas

router = APIRouter(prefix="/spending", tags=["Spending"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=schemas.SpendingLogOut)
def create_spending_log(spending: schemas.SpendingLogCreate, db: Session = Depends(get_db)):
    new_log = models.SpendingLog(
        user_id=spending.user_id,
        item_name=spending.item_name,
        amount=spending.amount,
        decision=spending.decision,
        category=spending.category,
        comment=spending.comment
    )
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    return new_log

@router.get("/{user_id}", response_model=list[schemas.SpendingLogOut])
def get_user_spending(user_id: int, db: Session = Depends(get_db)):
    logs = db.query(models.SpendingLog).filter(models.SpendingLog.user_id == user_id).all()
    if not logs:
        raise HTTPException(status_code=404, detail="No spending logs found for this user")
    return logs
