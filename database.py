from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import create_engine
import os

# Only if not already present:
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")  # Or your actual default

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ✅ This is what I'm missing:
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Replace with your actual password and DB name
DATABASE_URL = "postgresql://postgres:FinivoAIsecure2025@localhost/FinivoAI_DB"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
