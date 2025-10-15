
from sqlalchemy.orm import Session
from database import SessionLocal
import model as models

def update_plan(user_id: int, new_plan: str):
    db: Session = SessionLocal()
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        from utils.plan_features import sanitize_plan
        user.plan = sanitize_plan(new_plan)
        db.commit()
        print(f"✅ Updated user {user_id}'s plan to '{new_plan.lower()}'")
    else:
        print(f"❌ User with ID {user_id} not found.")
    db.close()

if __name__ == "__main__":
    update_plan(1, "prestige")
