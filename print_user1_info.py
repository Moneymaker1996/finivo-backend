from sqlalchemy.orm import Session
from database import SessionLocal
import models

if __name__ == "__main__":
    db: Session = SessionLocal()
    user = db.query(models.User).filter(models.User.id == 1).first()
    if user:
        print(f"User ID: {user.id}\nName: {user.name}\nEmail: {user.email}\nPlan: {user.plan}")
    else:
        print("User with ID 1 not found.")
    db.close()
