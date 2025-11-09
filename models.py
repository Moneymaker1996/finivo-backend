from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    # keep email + hashed password for existing auth flows
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)
    # add name (nullable to remain compatible with older code paths)
    name = Column(String, nullable=True)
    plan = Column(String, default="essential", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    voice_feature_enabled = Column(Boolean, default=False)

    spending_logs = relationship("SpendingLog", back_populates="user", cascade="all, delete-orphan")
    plaid_accounts = relationship("PlaidAccount", back_populates="user", cascade="all, delete-orphan")
    plaid_transactions = relationship("PlaidTransaction", back_populates="user", cascade="all, delete-orphan")


class SpendingLog(Base):
    __tablename__ = "spending_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    # merged fields from older and newer schemas
    item_name = Column(String, nullable=True)
    amount = Column(Float, nullable=False, default=0.0)
    decision = Column(String, nullable=True)  # e.g., "blocked", "allowed", "regret"
    category = Column(String, nullable=True)
    comment = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    regret = Column(Boolean, default=False)

    user = relationship("User", back_populates="spending_logs")


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
    spending_intent = Column(String, nullable=True)
    nudge_message = Column(Text, nullable=True)
    plan = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    voice_enabled = Column(Boolean, default=False)
    source = Column(String, default="text")


class UserPlaidToken(Base):
    __tablename__ = "user_plaid_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    access_token = Column(String(1024), nullable=False)
    item_id = Column(String(256), nullable=True)
    key_version = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        # Keep a uniqueness hint similar to Alembic migration
        {},
    )


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
