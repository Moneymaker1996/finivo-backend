import os
os.environ["OMP_NUM_THREADS"] = "1"

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import model as models, schemas
from routers import user, spending, nudge_memory_logic, report, plaid, voice
from fastapi.staticfiles import StaticFiles
import threading
import time

# Create the DB tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Mount static directory for audio and other static files
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(user.router)
app.include_router(spending.router)
app.include_router(nudge_memory_logic.router, prefix="/memory")
app.include_router(report.router)
app.include_router(plaid.router, prefix="/plaid")
from routers.voice import router as voice_router
app.include_router(voice_router)
from routers.whatsapp import router as whatsapp_router
app.include_router(whatsapp_router)
from routers.whatsapp_webhook import router as whatsapp_webhook_router
app.include_router(whatsapp_webhook_router, prefix="/webhook", tags=["whatsapp"])

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

def cleanup_old_audio_files(directory="static/audio", max_age_hours=24):
    now = time.time()
    cutoff = now - max_age_hours * 3600
    if not os.path.exists(directory):
        return
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            file_mtime = os.path.getmtime(file_path)
            if file_mtime < cutoff:
                try:
                    os.remove(file_path)
                except Exception:
                    pass

def start_audio_cleanup_background_task():
    def run_cleanup():
        while True:
            cleanup_old_audio_files()
            time.sleep(3600)  # Run every hour
    thread = threading.Thread(target=run_cleanup, daemon=True)
    thread.start()

start_audio_cleanup_background_task()
