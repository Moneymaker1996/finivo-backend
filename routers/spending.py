from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import SessionLocal
import models, schemas
from utils.impulse_engine import scan_impulse_triggers

router = APIRouter(prefix="/spending", tags=["Spending"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=schemas.SpendingLogOut)
def create_spending_log(spending: schemas.SpendingLogCreate, db: Session = Depends(get_db)):
    # Run impulse detection using available fields
    try:
        scan_input = {
            "item_name": spending.item_name,
            "mood": getattr(spending, "mood", None),
            "pattern": getattr(spending, "pattern", None),
            "urgency": getattr(spending, "urgency", None),
            "last_purchase_days": getattr(spending, "last_purchase_days", None),
            "situation": getattr(spending, "situation", None),
            "explanation": getattr(spending, "explanation", None),
        }
        impulse_result = scan_impulse_triggers(scan_input)
        is_impulsive = impulse_result.get("is_impulsive", False)
    except Exception:
        is_impulsive = False

    decision_value = "impulsive" if is_impulsive else (spending.decision or "undecided")

    new_log = models.SpendingLog(
        user_id=spending.user_id,
        item_name=spending.item_name,
        amount=spending.amount,
        decision=decision_value,
        category=spending.category,
        comment=spending.comment
    )
    db.add(new_log)
    db.commit()
    db.refresh(new_log)

    # If impulsive, create a NudgeLog entry for inspection/history
    if is_impulsive:
        try:
            n = models.NudgeLog(user_id=spending.user_id, spending_intent=spending.item_name, nudge_message="impulse_detected", plan=None, source="spending_route")
            db.add(n)
            db.commit()
        except Exception:
            pass
    return new_log

@router.get("/{user_id}", response_model=list[schemas.SpendingLogOut])
def get_user_spending(user_id: int, db: Session = Depends(get_db)):
    logs = db.query(models.SpendingLog).filter(models.SpendingLog.user_id == user_id).all()
    if not logs:
        raise HTTPException(status_code=404, detail="No spending logs found for this user")
    return logs
