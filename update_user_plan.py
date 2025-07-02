from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from model import User

# Correct PostgreSQL credentials
DATABASE_URL = "postgresql://postgres:FinivoAIsecure2025@localhost/FinivoAI_DB"


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

try:
    user = session.query(User).filter(User.id == 1).first()
    if user:
        user.plan = "ultra"
        session.commit()
        print("✅ User 1 plan updated to ultra.")
    else:
        print("❌ User with id=1 not found.")
finally:
    session.close()
