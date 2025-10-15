from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    plan = Column(String, default="essential", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    spending_logs = relationship("SpendingLog", back_populates="user", cascade="all, delete-orphan")
    plaid_accounts = relationship("PlaidAccount", back_populates="user", cascade="all, delete-orphan")
    plaid_transactions = relationship("PlaidTransaction", back_populates="user", cascade="all, delete-orphan")


class SpendingLog(Base):
    __tablename__ = "spending_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float, nullable=False)
    category = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    regret = Column(Boolean, default=False)

    user = relationship("User", back_populates="spending_logs")


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
