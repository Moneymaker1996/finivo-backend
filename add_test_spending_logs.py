from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from model import SpendingLog
from datetime import datetime

DATABASE_URL = "postgresql://postgres:FinivoAIsecure2025@localhost/FinivoAI_DB"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

try:
    logs = [
        SpendingLog(user_id=1, item_name="Smartphone", amount=300, decision="no_regret", timestamp=datetime.utcnow()),
        SpendingLog(user_id=1, item_name="Luxury Dinner", amount=200, decision="regret", timestamp=datetime.utcnow()),
        SpendingLog(user_id=1, item_name="Flight Booking", amount=350, decision="no_regret", timestamp=datetime.utcnow()),
        SpendingLog(user_id=1, item_name="Tech Gadget", amount=180, decision="regret", timestamp=datetime.utcnow()),
    ]
    session.add_all(logs)
    session.commit()
    print("✅ Sample spending logs added.")
except Exception as e:
    print(f"❌ Error: {e}")
finally:
    session.close()
