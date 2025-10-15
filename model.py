from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime, Text, Boolean
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True)
    plan = Column(String, nullable=False)
    voice_feature_enabled = Column(Boolean, default=False)  # True if user has voice feature

class SpendingLog(Base):
    __tablename__ = "spending_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    item_name = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    decision = Column(String)  # e.g., "blocked", "allowed", "warned"
    timestamp = Column(DateTime, default=datetime.utcnow)
    category = Column(String, nullable=True)  # New field for category
    comment = Column(String, nullable=True)   # New field for comment

class UserMemory(Base):
    __tablename__ = "user_memory"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

class NudgeLog(Base):
    __tablename__ = "nudge_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    spending_intent = Column(String, nullable=False)
    nudge_message = Column(Text, nullable=False)
    plan = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    voice_enabled = Column(Boolean, default=False)  # True if voice nudge delivered
    source = Column(String, default="text")  # "text" or "voice"
