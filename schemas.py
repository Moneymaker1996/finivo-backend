
from pydantic import BaseModel, validator
from typing import Optional, Union
from datetime import date

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
from pydantic import BaseModel

class SpendingIntent(BaseModel):
    item_name: str                # was 'item' before, fix to match input
    mood: str
    pattern: Optional[str] = None
    urgency: Optional[str] = None   # accept string like "only one left"
    last_purchase: Optional[date] = None
    situation: Optional[str] = None
    explanation: Optional[str] = None
    user_id: Optional[int] = None
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    name: str
    email: str

class SpendingLogCreate(BaseModel):
    user_id: int
    item_name: str
    amount: float
    decision: Optional[str] = "undecided"
    category: Optional[str] = None  # New field for category
    comment: Optional[str] = None   # New field for comment

class SpendingLogOut(BaseModel):
    id: int
    user_id: int
    item_name: str
    amount: float
    decision: str
    timestamp: datetime
    category: Optional[str] = None  # New field for category
    comment: Optional[str] = None   # New field for comment

    class Config:
        from_attributes = True

class SpendingLogCreate(BaseModel):
    user_id: int
    amount: float
    category: str
    description: str
    timestamp: datetime

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
