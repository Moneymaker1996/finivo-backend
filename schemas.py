from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date


class NudgeRequest(BaseModel):
    spending_intent: Optional[str] = None
    item_name: Optional[str] = None
    mood: Optional[str] = None
    pattern: Optional[str] = None
    urgency: Optional[bool] = None
    last_purchase_days: Optional[int] = None
    situation: Optional[str] = None
    explanation: Optional[str] = None


class SpendingIntent(BaseModel):
    item_name: str
    mood: str
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
    category: Optional[str] = None
    comment: Optional[str] = None
    description: Optional[str] = None
    timestamp: Optional[datetime] = None
    # Optional fields used by impulse detection
    item_type: Optional[str] = None
    mood: Optional[str] = None
    pattern: Optional[str] = None
    urgency: Optional[bool] = None
    last_purchase: Optional[datetime] = None
    last_purchase_days: Optional[int] = None
    situation: Optional[str] = None
    explanation: Optional[str] = None


class SpendingLogOut(BaseModel):
    id: int
    user_id: int
    item_name: str
    amount: float
    decision: Optional[str]
    timestamp: Optional[datetime]
    category: Optional[str] = None
    comment: Optional[str] = None

    class Config:
        from_attributes = True


class UserMemoryCreate(BaseModel):
    content: str
    timestamp: Optional[datetime] = None


class UserMemoryResponse(BaseModel):
    id: int
    user_id: int
    content: str
    timestamp: datetime

    class Config:
        from_attributes = True


class NudgeLogCreate(BaseModel):
    user_id: int
    spending_intent: Optional[str] = None
    nudge_message: Optional[str] = None
    plan: Optional[str] = None
    timestamp: Optional[datetime] = None
    source: str = "text"


class NudgeLogResponse(BaseModel):
    id: int
    user_id: int
    spending_intent: Optional[str]
    nudge_message: Optional[str]
    plan: Optional[str]
    timestamp: Optional[datetime]
    source: str = "text"

    class Config:
        from_attributes = True


class PlanUpdateRequest(BaseModel):
    plan: str
