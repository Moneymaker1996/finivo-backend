from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from schemas import UserMemoryCreate, UserMemoryResponse, NudgeLogResponse
from model import UserMemory, User, NudgeLog, SpendingLog
from memory import store_memory, search_memory, semantic_search_recent_memories  # Import embedding-powered functions
from pydantic import BaseModel
from nudge import smart_nudge
from datetime import datetime, timedelta
import re
from utils.plan_features import get_plan_features
from utils.impulse_engine import scan_impulse_triggers

router = APIRouter(prefix="/memory", tags=["Memory"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/store/{user_id}")
async def store_user_memory(user_id: int, data: UserMemoryCreate, db: Session = Depends(get_db)):
    print("/store/{user_id} endpoint called")
    # Store in relational DB (optional, for history)
    memory = UserMemory(
        user_id=user_id,
        content=data.content,
        timestamp=data.timestamp
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)
    # Store in ChromaDB with embedding
    store_memory(user_id, data.content)
    return memory

@router.get("/search", response_model=list[UserMemoryResponse])
def get_user_memory(user_id: int, db: Session = Depends(get_db)):
    memories = db.query(UserMemory).filter(UserMemory.user_id == user_id).all()
    if not memories:
        raise HTTPException(status_code=404, detail="No memory found")
    return memories

@router.post("/search/{user_id}")
def post_search_vector_memory(user_id: int, body: dict):
    print("/search/{user_id} endpoint called")
    query = body.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="Missing 'query' in request body")
    results = search_memory(query)
    return results

class NudgeRequest(BaseModel):
    spending_intent: str = None
    item_name: str = None
    mood: str = None
    pattern_match: bool = None
    urgency: bool = None
    last_purchase_days_ago: int = None
    situation: str = None
    explanation: str = None

@router.post("/nudge/{user_id}")
async def nudge_user(user_id: int, body: NudgeRequest, db: Session = Depends(get_db)):
    # 1. Fetch user and plan
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    plan = user.plan
    spending_intent = body.spending_intent
    # --- ULTRA PLAN BUDGET ENFORCEMENT ---
    if plan == "ultra":
        # Try to extract an amount from the spending_intent string
        match = re.search(r"\$?([0-9]+(?:\.[0-9]{1,2})?)", spending_intent.replace(",", ""))
        amount = float(match.group(1)) if match else None
        WEEKLY_BUDGET = 1000.0
        if amount:
            today = datetime.utcnow().date()
            start_of_week = today - timedelta(days=today.weekday())
            total_spent = db.query(SpendingLog).filter(
                SpendingLog.user_id == user_id,
                SpendingLog.timestamp >= datetime.combine(start_of_week, datetime.min.time()),
                SpendingLog.timestamp <= datetime.utcnow()
            ).with_entities(SpendingLog.amount).all()
            total_spent_sum = sum(x[0] for x in total_spent if x[0])
            if total_spent_sum + amount > WEEKLY_BUDGET:
                message = f"[ULTRA] Warning: This purchase will exceed your weekly budget of $1000."
                nudge_log = NudgeLog(
                    user_id=user_id,
                    spending_intent=spending_intent,
                    nudge_message=message,
                    plan=plan,
                    timestamp=datetime.utcnow()
                )
                db.add(nudge_log)
                db.commit()
                return {"message": message}
    # PLAN-BASED NUDGE LIMIT
    if plan == "free":
        today = datetime.utcnow().date()
        nudge_count = db.query(NudgeLog).filter(
            NudgeLog.user_id == user_id,
            NudgeLog.plan == "free",
            NudgeLog.timestamp >= datetime.combine(today, datetime.min.time()),
            NudgeLog.timestamp <= datetime.combine(today, datetime.max.time())
        ).count()
        if nudge_count >= 3:
            raise HTTPException(status_code=403, detail="Daily nudge limit reached for free plan. Upgrade to continue.")
    # 2. If explicit I.M.P.U.L.S.E. fields are provided, use them directly
    if body.item_name and body.mood is not None and body.pattern_match is not None and body.urgency is not None and body.last_purchase_days_ago is not None and body.situation is not None and body.explanation is not None:
        impulse_data = {
            "item_name": body.item_name,
            "mood": body.mood,
            "pattern_match": body.pattern_match,
            "urgency": body.urgency,
            "last_purchase_days_ago": body.last_purchase_days_ago,
            "situation": body.situation,
            "explanation": body.explanation
        }
        impulse_result = scan_impulse_triggers(impulse_data)
        if impulse_result["is_impulsive"]:
            message = f"🚨 IMPULSE WARNING: This action shows signs of impulsive spending! (Triggers: {','.join(impulse_result['triggered_flags'])})"
        else:
            message = "✅ You're good to go. No impulsive flags detected in your decision."
        nudge_log = NudgeLog(
            user_id=user_id,
            spending_intent=str(impulse_data),
            nudge_message=message,
            plan=plan,
            timestamp=datetime.utcnow()
        )
        db.add(nudge_log)
        db.commit()
        return {"message": message, "impulse": impulse_result}
    # 2. Improved semantic memory search (last 30 days, min similarity 0.8)
    matches = semantic_search_recent_memories(user_id, spending_intent, min_similarity=0.8, days=30, n_results=1)
    if matches:
        top_memory, similarity = matches[0]
        message = f"⚠️ Heads up! Based on your recent memory: '{top_memory}', you may regret this purchase. Want to think twice? (similarity: {similarity:.2f})"
    else:
        message = f"[{plan.upper()}] No strongly related memories found, but use your best judgment before spending."
    # --- IMPULSE DETECTION ---
    # Simple extraction for demo: treat first word as item_name, rest as explanation
    words = spending_intent.split()
    item_name = words[0] if words else "item"
    explanation = " ".join(words[1:]) if len(words) > 1 else ""
    impulse_data = {
        "item_name": item_name,
        "mood": "",  # Could be extended to accept from user
        "pattern_match": False,  # Could be inferred from user history
        "urgency": False,  # Could be inferred or asked
        "last_purchase_days_ago": 10,  # Placeholder
        "situation": "",  # Could be extended
        "explanation": explanation
    }
    impulse_result = scan_impulse_triggers(impulse_data)
    if impulse_result["is_impulsive"]:
        message = f"🚨 IMPULSE WARNING: This action shows signs of impulsive spending! (Triggers: {','.join(impulse_result['triggered_flags'])})\n" + message
    # --- IMPULSE DETECTION (IMPROVED NLP extraction) ---
    text = spending_intent.lower()
    # Mood detection
    mood = ""
    for m in ["sad", "down", "anxious", "bored", "excited", "stressful", "stressed"]:
        if m in text:
            mood = m
            break
    # Urgency detection (expanded)
    urgency = any(word in text for word in ["limited-time", "sale", "now", "last-minute", "urgent", "today only", "only 1 left", "last in stock", "left in stock", "scarcity", "only one left"])
    # Last purchase detection (expanded)
    last_purchase_days_ago = 10
    if any(phrase in text for phrase in ["already bought", "this week", "recently", "since friday", "since monday", "since yesterday"]):
        last_purchase_days_ago = 1
    # Situation detection (expanded)
    situation = ""
    for s in ["treat", "celebration", "peer pressure", "boredom", "stress", "deserve", "reward", "after this week"]:
        if s in text:
            situation = s
            break
    # Vague explanation detection (expanded)
    explanation = spending_intent
    for v in ["just felt like it", "i don’t know", "i don't know", "because i wanted to", "feels like a treat", "deserve", "reward", "earned it"]:
        if v in text:
            explanation = v
            break
    # Item name: try to extract a likely item (expanded)
    item_name = "item"
    for word in ["sneakers", "shoes", "iphone", "ticket", "trip", "sale", "purchase", "bag", "designer bag", "stock"]:
        if word in text:
            item_name = word
            break
    impulse_data = {
        "item_name": item_name,
        "mood": mood,
        "pattern_match": False,  # Could be inferred from user history
        "urgency": urgency,
        "last_purchase_days_ago": last_purchase_days_ago,
        "situation": situation,
        "explanation": explanation
    }
    impulse_result = scan_impulse_triggers(impulse_data)
    if impulse_result["is_impulsive"]:
        message = f"🚨 IMPULSE WARNING: This action shows signs of impulsive spending! (Triggers: {','.join(impulse_result['triggered_flags'])})\n" + message
    # 3. Log the nudge
    nudge_log = NudgeLog(
        user_id=user_id,
        spending_intent=spending_intent,
        nudge_message=message,
        plan=plan,
        timestamp=datetime.utcnow()
    )
    db.add(nudge_log)
    db.commit()
    # 4. Return the nudge message and impulse info
    return {"message": message, "impulse": impulse_result}

@router.get("/nudge/history/{user_id}", response_model=list[NudgeLogResponse])
def get_nudge_history(user_id: int, db: Session = Depends(get_db)):
    logs = db.query(NudgeLog).filter(NudgeLog.user_id == user_id).order_by(NudgeLog.timestamp.desc()).all()
    return logs

def get_user_by_id(user_id: int, db: Session):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user

def get_user_nudge_count(user_id: int, db: Session, period: str = "month"):
    now = datetime.utcnow()
    if period == "month":
        start = datetime(now.year, now.month, 1)
    else:
        start = datetime(now.year, now.month, now.day)
    return db.query(NudgeLog).filter(NudgeLog.user_id == user_id, NudgeLog.timestamp >= start).count()

def check_user_budget_status(user_id: int):
    # Placeholder: always not exceeded
    return {"exceeded": False, "limit": 1000, "spent": 500}

def generate_nudge_with_tone(user_id: int, tone: str):
    # Placeholder: returns a simple nudge
    return f"[{tone.capitalize()}] Consider your recent spending before making this purchase."

@router.get("/nudge/{user_id}")
def get_nudge(user_id: int, db: Session = Depends(get_db)):
    user = get_user_by_id(user_id, db)
    features = get_plan_features(user.plan)
    # Enforce monthly nudge limit (unless unlimited)
    if features["nudge_limit"] is not None:
        monthly_usage = get_user_nudge_count(user_id, db, period="month")
        if monthly_usage >= features["nudge_limit"]:
            raise HTTPException(status_code=403, detail="Monthly nudge limit reached. Upgrade for more.")
    else:
        monthly_usage = get_user_nudge_count(user_id, db, period="month")
    # Optional: Enforce real-time budget rules
    if features["budget_enforcement"]:
        budget_status = check_user_budget_status(user_id)
        if budget_status["exceeded"]:
            return {
                "warning": "You’ve exceeded your weekly budget limit.",
                "details": budget_status
            }
    # Generate personalized nudge using tone
    tone = features["ai_tone"]
    nudge = generate_nudge_with_tone(user_id, tone)
    return {
        "nudge": nudge,
        "tone": tone,
        "nudge_count_this_month": monthly_usage + 1
    }
