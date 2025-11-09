from pydantic import BaseModel, validator
from typing import Optional, Union, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from models import User, SpendingLog, NudgeLog
from schemas import NudgeRequest, UserMemoryCreate, UserMemoryResponse, NudgeLogResponse
from database import get_db
from datetime import datetime
import logging

router = APIRouter()  # ✅ This is the missing line that caused the crash

logger = logging.getLogger("nudge")

router = APIRouter(prefix="/memory", tags=["Memory"])

# NudgeRequest class moved here for visibility
class NudgeRequest(BaseModel):
    spending_intent: Optional[str] = None
    item_name: Optional[str] = None
    mood: Optional[str] = None
    pattern: Optional[str] = None
    urgency: Union[bool, str, None] = None
    last_purchase_days: Optional[int] = None
    situation: Optional[str] = None
    explanation: Optional[str] = None

    @validator('urgency', pre=True)
    def convert_urgency(cls, v):
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            urgency_keywords = ['urgent', 'flash sale', 'only today', 'running out', 'last chance']
            if any(kw in v.lower() for kw in urgency_keywords):
                return True
            return False
        return v

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/store/{user_id}")
async def store_user_memory(user_id: int, data: UserMemoryCreate, db: Session = Depends(get_db)):
    memory = UserMemory(
        user_id=user_id,
        content=data.content,
        timestamp=data.timestamp
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)
    from memory import store_memory  # safe lazy import
    store_memory(user_id, data.content)
    return memory

@router.get("/search", response_model=List[UserMemoryResponse])
def get_user_memory(user_id: int, db: Session = Depends(get_db)):
    memories = db.query(UserMemory).filter(UserMemory.user_id == user_id).all()
    if not memories:
        raise HTTPException(status_code=404, detail="No memory found")
    return memories



def run_impulse_analysis(body: NudgeRequest, user_id: int, db: Session) -> dict:
    triggered_flags = []
    debug_log = {}

    soft_trigger_count = sum([
        1 if word in (body.explanation or '').lower() else 0
        for word in ["just felt like", "don't need", "looks cool", "saw someone", "bored", "not sure"]
    ])
    if soft_trigger_count >= 3:
        triggered_flags.append("soft")

    # I - Item Type
    I_flag = any(w in (body.item or '').lower() for w in ["shoes", "watch", "luxury", "sneaker", "gucci", "iphone", "bag"])
    debug_log["I"] = f"[DEBUG] I: input = {body.item.lower()}, triggered = {I_flag}"
    if I_flag:
        triggered_flags.append("I")

    # M - Mood
    M_flag = any(w in (body.mood or '').lower() for w in ["bored", "lonely", "anxious", "frustrated"])
    debug_log["M"] = f"[DEBUG] M: input = {body.mood.lower()}, triggered = {M_flag}"
    if M_flag:
        triggered_flags.append("M")

    # P - Pattern
    past_regrets = db.query(SpendingLog).filter(SpendingLog.user_id == user_id, SpendingLog.regret == True).count()
    P_flag = past_regrets >= 3
    debug_log["P"] = f"[DEBUG] P: regrets = {past_regrets}, triggered = {P_flag}"
    if P_flag:
        triggered_flags.append("P")

    # U - Urgency
    U_flag = body.urgency is True
    debug_log["U"] = f"[DEBUG] U: input = {body.urgency}, triggered = {U_flag}"
    if U_flag:
        triggered_flags.append("U")

    # L - Last Purchase
    last_log = db.query(SpendingLog).filter(SpendingLog.user_id == user_id).order_by(SpendingLog.timestamp.desc()).first()
    L_flag = False
    if last_log:
        delta_days = (datetime.utcnow() - last_log.timestamp).days
        L_flag = delta_days < 5
    debug_log["L"] = f"[DEBUG] L: days since last spend = {delta_days if last_log else 'N/A'}, triggered = {L_flag}"
    if L_flag:
        triggered_flags.append("L")

    # S - Situation
    S_flag = any(w in (body.situation or '').lower() for w in ["party", "wedding", "friends", "instagram", "tiktok"])
    debug_log["S"] = f"[DEBUG] S: input = {body.situation.lower()}, triggered = {S_flag}"
    if S_flag:
        triggered_flags.append("S")

    # E - Explanation
    E_flag = any(w in (body.explanation or '').lower() for w in ["don’t need", "just want", "not sure", "looks cool"])
    debug_log["E"] = f"[DEBUG] E: input = {body.explanation.lower()}, triggered = {E_flag}"
    if E_flag:
        triggered_flags.append("E")

    is_impulsive = len(triggered_flags) >= 4 or soft_trigger_count >= 3

    debug_log["soft_trigger_count"] = soft_trigger_count
    debug_log["total_triggers"] = len(triggered_flags)
    debug_log["is_impulsive"] = is_impulsive

    return {
        "total_triggers": len(triggered_flags),
        "is_impulsive": is_impulsive,
        "triggered_flags": triggered_flags,
        "debug": debug_log
    }


def run_earn_persuasion(body: NudgeRequest, tone: str) -> dict:
    if tone == "smart":
        return {
            "empathize": "That sounds like something that caught your attention in the moment—totally valid.",
            "ask": "What’s driving this feeling of urgency today? Could this be a short-term emotion?",
            "reframe": "What if we paused for 24 hours and revisited this tomorrow with fresh eyes?",
            "nudge": "Want me to bookmark this for now and check in with you tomorrow?"
        }
    elif tone == "luxury":
        return {
            "empathize": "I understand the excitement and allure of owning a limited edition piece, especially when it speaks to your personal style.",
            "ask": "Let’s pause and reflect: What is making this purchase feel urgent to you right now? Are there deeper reasons behind it?",
            "reframe": "Considering your financial vision, it may be valuable to hold off for 48 hours and reflect.",
            "nudge": "I’ll save this for you to revisit tomorrow. If you’d like, I can set a reminder to review it together."
        }
    else:
        return {}

@router.post("/nudge/{user_id}")
async def nudge_user(user_id: int, body: NudgeRequest, db: Session = Depends(get_db), source: str = "text"):
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    from utils.plan_features import sanitize_plan, get_plan_features
    from nudge_memory_logic import search_memory
    plan = sanitize_plan(user.plan)
    plan_features = get_plan_features(plan)

    # Map item_name to item for memory logic
    payload = body.dict()
    payload["item"] = payload.get("item_name", "")

    # Output format
    output = {"persuasion": False, "message": ""}

    # Essential plan: legacy I.M.P.U.L.S.E. only
    if plan == "essential":
        impulse_result = run_impulse_analysis(body, user_id, db)
        if impulse_result["is_impulsive"]:
            # Enforce 20 nudges/month cap
            now = datetime.utcnow()
            start_of_month = datetime(now.year, now.month, 1)
            nudge_count = db.query(NudgeLog).filter(
                NudgeLog.user_id == user_id,
                NudgeLog.timestamp >= start_of_month
            ).count()
            if nudge_count >= 20:
                output["message"] = "Monthly nudge limit reached. Consider upgrading for more support."
                return output
            # Log the nudge
            nudge_log = NudgeLog(user_id=user_id, tone="basic", raw_input=str(body.dict()), result=str(impulse_result))
            db.add(nudge_log)
            db.commit()
            output["message"] = "This seems impulsive. You might want to wait before buying."
            return output
        output["message"] = "Purchase seems reasonable based on the current context."
        return output

    # Prestige/Elite: memory-aware logic
    regret_memories = []
    try:
        regret_memories = search_memory(payload.get("pattern", ""), n_results=1)[0]
    except Exception:
        regret_memories = []

    impulse_result = run_impulse_analysis(body, user_id, db)
    earn_result = run_earn_persuasion(body, plan_features.get("ai_tone", "basic"))

    # Persuasion mode: memory found & 4+ triggers
    if regret_memories and impulse_result["is_impulsive"] and len(impulse_result["triggered_flags"]) >= 4:
        output["persuasion"] = True
        output["message"] = earn_result.get("nudge") or "This seems impulsive. You might want to wait before buying."
        # Optionally log persuasion nudge
        nudge_log = NudgeLog(user_id=user_id, tone=plan_features.get("ai_tone", "basic"), raw_input=str(body.dict()), result=str(impulse_result))
        db.add(nudge_log)
        db.commit()
        return output

    # Fallback: no regret memory or not impulsive
    output["persuasion"] = False
    output["message"] = "Purchase seems reasonable based on the current context."
    return output
    # ...existing code for other plans...


@router.get("/nudge/history/{user_id}", response_model=List[NudgeLogResponse])
def get_nudge_history(
    user_id: int,
    start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    type: Optional[str] = Query(None, regex="^(impulsive|fallback)$", description="Nudge type: impulsive or fallback"),
    plan: Optional[str] = Query(None, description="Plan filter: essential, prestige, elite"),
    db: Session = Depends(get_db)
):
    try:
        start_dt = datetime.strptime(start, "%Y-%m-%d") if start else None
        end_dt = datetime.strptime(end, "%Y-%m-%d") if end else None
    except:
        raise HTTPException(status_code=422, detail="Invalid date format.")
    if plan and plan.lower() not in ["essential", "prestige", "elite"]:
        raise HTTPException(status_code=422, detail="Invalid plan.")
    q = db.query(NudgeLog).filter(NudgeLog.user_id == user_id)
    if start_dt:
        q = q.filter(NudgeLog.timestamp >= start_dt)
    if end_dt:
        q = q.filter(NudgeLog.timestamp <= end_dt)
    if plan:
        q = q.filter(NudgeLog.plan == plan)
    if type == "impulsive":
        q = q.filter(NudgeLog.nudge_message.ilike("%impulse%"))
    elif type == "fallback":
        q = q.filter(NudgeLog.nudge_message.ilike("%reconnect%") | NudgeLog.nudge_message.ilike("%pause%"))

# Helper functions
def get_user_by_id(user_id: int, db: Session):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user

def get_user_nudge_count(user_id: int, db: Session, period: str = "month"):
    now = datetime.utcnow()
    start = datetime(now.year, now.month, 1) if period == "month" else datetime(now.year, now.month, now.day)
    return db.query(NudgeLog).filter(NudgeLog.user_id == user_id, NudgeLog.timestamp >= start).count()

def check_user_budget_status(user_id: int):
    # Placeholder: Replace with actual budget tracking logic
    return {"exceeded": False, "limit": 1000, "spent": 500}

def generate_nudge_with_tone(user_id: int, tone: str):
    # Placeholder: Replace with actual tone logic if needed
    return f"[{tone.capitalize()}] Consider your recent spending before making this purchase."

# Nudge retrieval endpoint
@router.get("/nudge/{user_id}")
def get_nudge(user_id: int, db: Session = Depends(get_db)):
    user = get_user_by_id(user_id, db)
    features = get_plan_features(sanitize_plan(user.plan))

    # Enforce monthly nudge limit
    if features["nudge_limit"] is not None:
        monthly_usage = get_user_nudge_count(user_id, db, period="month")
        if monthly_usage >= features["nudge_limit"]:
            raise HTTPException(status_code=403, detail="Monthly nudge limit reached. Upgrade for more.")
    else:
        monthly_usage = get_user_nudge_count(user_id, db, period="month")

    # Enforce real-time budget enforcement if enabled
    if features.get("budget_enforcement"):
        budget_status = check_user_budget_status(user_id)
        if budget_status["exceeded"]:
            return {
                "warning": "You’ve exceeded your weekly budget limit.",
                "details": budget_status
            }

    # Generate nudge using plan-specific tone
    tone = features.get("ai_tone", "basic")
    nudge = generate_nudge_with_tone(user_id, tone)
    return {
        "nudge": nudge,
        "tone": tone,
        "nudge_count_this_month": monthly_usage + 1
    }
