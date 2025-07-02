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
        orm_mode = True

class UserMemoryCreate(BaseModel):
    content: str
    timestamp: datetime

class UserMemoryResponse(BaseModel):
    id: int
    user_id: int
    content: str
    timestamp: datetime

    class Config:
        orm_mode = True

class NudgeLogCreate(BaseModel):
    user_id: int
    spending_intent: str
    nudge_message: str
    plan: str
    timestamp: datetime

class NudgeLogResponse(BaseModel):
    id: int
    user_id: int
    spending_intent: str
    nudge_message: str
    plan: str
    timestamp: datetime

    class Config:
        orm_mode = True
