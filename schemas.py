from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date


class NudgeRequest(BaseModel):
    # Simple sentence-style input
    spending_intent: Optional[str] = None

    # I.M.P.U.L.S.E. breakdown (structured form)
    item_name: Optional[str] = None
    mood: Optional[str] = None
    pattern: Optional[str] = None
    urgency: Optional[bool] = None
    last_purchase_days: Optional[int] = None
    situation: Optional[str] = None
    explanation: Optional[str] = None


class SpendingIntent(BaseModel):
    item_name: str
    mood: Optional[str] = None
    pattern: Optional[str] = None
    urgency: Optional[str] = None
    last_purchase: Optional[date] = None
    situation: Optional[str] = None
    explanation: Optional[str] = None
    user_id: Optional[int] = None


class UserCreate(BaseModel):
    name: str
    email: str


class SpendingLogCreate(BaseModel):
    user_id: int
    item_name: str
    amount: float
    decision: Optional[str] = "undecided"

    # I.M.P.U.L.S.E. explicit fields (optional; clients should supply if available)
    item_type: Optional[str] = None    # e.g., "need", "want", "luxury"
    mood: Optional[str] = None
    pattern: Optional[str] = None
    urgency: Optional[bool] = None
    last_purchase: Optional[datetime] = None
    situation: Optional[str] = None
    explanation: Optional[str] = None

    # Backward-compatible proxies
    category: Optional[str] = None
    comment: Optional[str] = None


class SpendingLogOut(BaseModel):
    id: int
    user_id: int
    item_name: str
    amount: float
    decision: str
    timestamp: datetime

    # Expose the I.M.P.U.L.S.E. fields so clients can see what was evaluated
    item_type: Optional[str] = None
    mood: Optional[str] = None
    pattern: Optional[str] = None
    urgency: Optional[bool] = None
    last_purchase: Optional[datetime] = None
    situation: Optional[str] = None
    explanation: Optional[str] = None

    category: Optional[str] = None
    comment: Optional[str] = None

    class Config:
        from_attributes = True


class SpendingLogResponse(SpendingLogCreate):
    id: int

    class Config:
        from_attributes = True


class UserMemoryCreate(BaseModel):
    content: str
    timestamp: datetime


class UserMemoryResponse(BaseModel):
    id: int
    user_id: int
    content: str
    timestamp: datetime

    class Config:
        from_attributes = True


class NudgeLogCreate(BaseModel):
    user_id: int
    spending_intent: str
    nudge_message: str
    plan: str
    timestamp: datetime
    source: str = "text"  # "text" or "voice"


class NudgeLogResponse(BaseModel):
    id: int
    user_id: int
    spending_intent: str
    nudge_message: str
    plan: str
    timestamp: datetime
    source: str = "text"

    class Config:
        from_attributes = True


class PlanUpdateRequest(BaseModel):
    plan: str
