from sqlalchemy.orm import Session
from database import SessionLocal
from models import User

# Create a new user for testing
def add_test_user():
    db: Session = SessionLocal()

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
    db: Session = SessionLocal()
    user = db.query(User).filter_by(id=1).first()
    if not user:
        # Create user if not exists
        user = User(id=1, name="Test User", email="testuser@example.com", plan="free")
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"User created: {user.id} - {user.name} - Plan: {user.plan}")
    else:
        print("User with ID 1 already exists. Updating name, email, and plan for all scenarios...")

    # Update name, email, and plan for each plan
    for plan in ["free", "essential", "prestige", "elite"]:
        user = db.query(User).filter_by(id=1).first()
        user.name = "Test User"
        user.email = "testuser@example.com"
        user.plan = plan
        db.commit()
        db.refresh(user)
        print(f"User updated: {user.id} - {user.name} - {user.email} - Plan: {user.plan}")

    # Finally, set user to 'free' plan for default
    user = db.query(User).filter_by(id=1).first()
    user.name = "Test User"
    user.email = "testuser@example.com"
    user.plan = "free"
    db.commit()
    db.refresh(user)
    print(f"User finalized: {user.id} - {user.name} - {user.email} - Plan: {user.plan}")
    db.close()
    # Remove user if exists, then recreate for clean test
    existing_user = db.query(User).filter_by(id=1).first()
    if existing_user:
        db.delete(existing_user)
        db.commit()
        print("Old user with ID 1 deleted.")

    # Create user for all plans
    for plan in ["free", "essential", "prestige"]:
        user = User(id=1, name=f"Test User ({plan})", email=f"testuser_{plan}@example.com", plan=plan)
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"User created: {user.id} - {user.name} - Plan: {user.plan}")
        db.delete(user)
        db.commit()
    # Finally, create user with 'free' plan for default
    user = User(id=1, name="Test User", email="testuser@example.com", plan="free")
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    print(f"User created: {user.id} - {user.name} - Plan: {user.plan}")
