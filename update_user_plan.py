import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from model import User

# Correct PostgreSQL credentials
DATABASE_URL = "postgresql://postgres:FinivoAIsecure2025@localhost/FinivoAI_DB"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

if len(sys.argv) != 3:
    print("Usage: python update_user_plan.py <user_id> <plan>")
    sys.exit(1)

user_id = int(sys.argv[1])
new_plan = sys.argv[2].lower()

try:
    user = session.query(User).filter(User.id == user_id).first()
    if user:
        from utils.plan_features import sanitize_plan
        user.plan = sanitize_plan(new_plan)
        session.commit()
        print(f"✅ User {user_id} plan updated to {new_plan}.")
    else:
        print(f"❌ User with id={user_id} not found.")
finally:
    session.close()
