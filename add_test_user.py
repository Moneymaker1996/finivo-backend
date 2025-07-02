from sqlalchemy.orm import Session
from database import SessionLocal
from model import User  # Fixed import

# Create a new user for testing
def add_test_user():
    db: Session = SessionLocal()

    # Check if user already exists
    existing_user = db.query(User).filter_by(id=1).first()
    if existing_user:
        print("User with ID 1 already exists.")
        db.close()
        return

    user = User(id=1, name="Test User", email="testuser@example.com", plan="free")  # Added plan
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    print(f"User created: {user.id} - {user.name}")

if __name__ == "__main__":
    add_test_user()
