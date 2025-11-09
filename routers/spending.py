from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import SessionLocal
import models, schemas
from utils.impulse import is_impulsive_purchase
import json
from utils.earn_engine import generate_earn_script
from utils.db_types import assign_response_script
from loguru import logger

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

    # Determine last purchase timestamp from DB if client did not provide one
    last_purchase_row = (
        db.query(models.SpendingLog)
        .filter(models.SpendingLog.user_id == spending.user_id, models.SpendingLog.id != new_log.id)
        .order_by(models.SpendingLog.timestamp.desc())
        .first()
    )
    last_purchase_ts = last_purchase_row.timestamp if last_purchase_row else None

    # Prefer explicit I.M.P.U.L.S.E. fields from the payload, fall back to proxies
    item_type = getattr(spending, "item_type", None) or new_log.category or new_log.item_name
    mood = getattr(spending, "mood", None)
    pattern = getattr(spending, "pattern", None)
    urgency = getattr(spending, "urgency", None) or False
    situation = getattr(spending, "situation", None)
    explanation = getattr(spending, "explanation", None) or new_log.comment

    # If client provided an explicit last_purchase, prefer it
    client_last = getattr(spending, "last_purchase", None)
    last_purchase_value = client_last or last_purchase_ts

    try:
        impulsive = is_impulsive_purchase(
            user_id=new_log.user_id,
            item_type=item_type,
            mood=mood,
            pattern=pattern,
            urgency=urgency,
            last_purchase=last_purchase_value,
            situation=situation,
            explanation=explanation,
        )
    except Exception:
        impulsive = False

    if impulsive:
        new_log.decision = "impulsive"
        db.add(new_log)
        db.commit()
        db.refresh(new_log)

        # Operational log for structured tracing
        try:
            logger.info(f"[Spending] User={new_log.user_id} Decision={new_log.decision}")
        except Exception:
            pass

        user = db.query(models.User).filter(models.User.id == new_log.user_id).first()
        plan = user.plan if user and hasattr(user, "plan") else "free"
        # Generate internal E.A.R.N. persuasion script and store it in the nudge log (internal only)
        user_name = user.name if user and hasattr(user, "name") else getattr(user, "email", "user")
        purchase_name = new_log.item_name or "this item"
        earn_script = generate_earn_script(user_name=user_name, purchase=purchase_name, plan=plan)

        # Note E.A.R.N. generation for observability
        try:
            logger.info(f"[EARN] Generated persuasion script for User={new_log.user_id}")
        except Exception:
            pass

        nudge = models.NudgeLog(
            user_id=new_log.user_id,
            spending_intent=new_log.item_name or "",
            nudge_message=f"Impulsive purchase detected for {new_log.item_name}",
            plan=plan,
            source="auto",
        )
        # Dialect-aware assignment: JSONB on Postgres, JSON string on SQLite
        assign_response_script(db, nudge, earn_script)
        db.add(nudge)
        db.commit()

    return new_log

@router.get("/{user_id}", response_model=list[schemas.SpendingLogOut])
def get_user_spending(user_id: int, db: Session = Depends(get_db)):
    logs = db.query(models.SpendingLog).filter(models.SpendingLog.user_id == user_id).all()
    if not logs:
        raise HTTPException(status_code=404, detail="No spending logs found for this user")
    return logs
