from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON, func
from sqlalchemy.orm import relationship
from datetime import datetime
from utils.db_types import json_type_for
from database import engine, Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    # Optional display name
    name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    # Allow nullable hashed_password to support tests and scripts that create users
    # without credentials (e.g., bootstrap/test helpers).
    hashed_password = Column(String, nullable=True)
    plan = Column(String, default="essential", nullable=False)
    # Feature flag: whether voice features are enabled for the user
    voice_feature_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    spending_logs = relationship("SpendingLog", back_populates="user", cascade="all, delete-orphan")
    plaid_accounts = relationship("PlaidAccount", back_populates="user", cascade="all, delete-orphan")
    plaid_transactions = relationship("PlaidTransaction", back_populates="user", cascade="all, delete-orphan")
    # One-to-one relationship for the latest Plaid token for this user
    plaid_token = relationship("UserPlaidToken", back_populates="user", uselist=False, cascade="all, delete-orphan")


class SpendingLog(Base):
    __tablename__ = "spending_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    # Keep both 'item_name' and 'description' to be compatible with different
    # code paths in the codebase that reference either field.
    item_name = Column(String, nullable=True)
    amount = Column(Float, nullable=False)
    category = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    # Some modules use 'comment' to store metadata such as Plaid txn id
    comment = Column(String, nullable=True)
    # Some code paths expect a 'decision' column (e.g., 'impulsive' vs 'normal')
    decision = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    regret = Column(Boolean, default=False)

    user = relationship("User", back_populates="spending_logs")


class NudgeLog(Base):
    __tablename__ = "nudge_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    spending_intent = Column(String, nullable=False)
    nudge_message = Column(Text, nullable=False)
    plan = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    voice_enabled = Column(Boolean, default=False)
    source = Column(String, default="text")
    # Use JSONB on Postgres, fallback to Text on SQLite
    try:
        _json_type = json_type_for(engine)
    except Exception:
        _json_type = Text
    response_script = Column(_json_type, nullable=True)

    user = relationship("User")


class PlaidAccount(Base):
    __tablename__ = "plaid_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    account_id = Column(String, nullable=False)
    name = Column(String)
    type = Column(String)
    subtype = Column(String)
    mask = Column(String)
    institution = Column(String)

    user = relationship("User", back_populates="plaid_accounts")


class PlaidTransaction(Base):
    __tablename__ = "plaid_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    transaction_id = Column(String, nullable=False)
    name = Column(String)
    amount = Column(Float)
    category = Column(String)
    date = Column(DateTime)
    pending = Column(Boolean)

    user = relationship("User", back_populates="plaid_transactions")


class ImpulseAlert(Base):
    __tablename__ = "impulse_alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    transaction_id = Column(Integer, ForeignKey("spending_logs.id"))
    score = Column(Integer)
    triggers = Column(JSON)
    reasoning = Column(Text)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    # optional relationships
    user = relationship("User")
    transaction = relationship("SpendingLog")


class UserMemory(Base):
    __tablename__ = "user_memory"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


class UserPlaidToken(Base):
    """Persistent storage for Plaid access tokens per user.

    Note: access_token is stored in plain text for now. TODO: encrypt or move to a secrets vault.
    """
    __tablename__ = "user_plaid_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    access_token = Column(String, nullable=False)
    item_id = Column(String, nullable=True)
    key_version = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="plaid_token")
