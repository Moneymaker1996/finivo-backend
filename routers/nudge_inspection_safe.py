from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from database import SessionLocal

from models import NudgeLog

import os

try:
    from loguru import logger
except Exception:
    import logging
    logger = logging.getLogger("nudge_inspection")
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())


router = APIRouter(prefix="/nudge", tags=["Nudge Inspection"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/earn/{user_id}")
def get_earn_sessions(user_id: int, limit: int = 5, db: Session = Depends(get_db)):
    """
    Returns the last few E.A.R.N. persuasion sessions for a given user.
    Accessible only when DEBUG or ADMIN_MODE is enabled.
    """
    debug = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")
    admin = os.getenv("ADMIN_MODE", "false").lower() in ("1", "true", "yes")

    if not (debug or admin):
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        sessions = (
            db.query(NudgeLog)
            .filter(NudgeLog.user_id == user_id)
            .filter(NudgeLog.source.in_(["earn_engine", "plaid_auto"]))
            .order_by(NudgeLog.timestamp.desc())
            .limit(limit)
            .all()
        )
    except Exception:
        # If the DB schema is out of date (missing column) or other DB error,
        # return a safe empty result rather than raising an internal server error.
        return {"user_id": user_id, "entries": [], "message": "E.A.R.N. sessions unavailable (DB schema may be out of date)"}

    if not sessions:
        return {"user_id": user_id, "entries": [], "message": "No E.A.R.N. sessions found"}

    result = []
    for s in sessions:
        data = s.response_script
        # Handle JSONB (dict) and TEXT fallback
        if isinstance(data, str):
            import json
            try:
                data = json.loads(data)
            except Exception:
                data = {"E": None, "A": None, "R": None, "N": None}

        result.append({
            "plan": s.plan,
            "timestamp": s.timestamp,
            "source": s.source,
            "intent": s.spending_intent,
            "earn_script": data,
        })

    # Operational log for diagnostics
    try:
        logger.info(f"[EARN] Retrieved={len(result)} for User={user_id}")
    except Exception:
        pass

    return {
        "user_id": user_id,
        "total": len(result),
        "entries": result,
    }
