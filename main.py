import os
os.environ["OMP_NUM_THREADS"] = "1"

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import model as models, schemas
from routers import user, spending, memory, report, plaid

# Create the DB tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(user.router)
app.include_router(spending.router)
app.include_router(memory.router)
app.include_router(report.router)
app.include_router(plaid.router, prefix="/plaid")

@app.get("/")
def read_root():
    return {"message": "Welcome to Finivo AI"}

# Dependency for getting DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ✅ Create a new user
@app.post("/users/")
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = models.User(name=user.name, email=user.email, plan="free")
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
