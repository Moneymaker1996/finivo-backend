import os
os.environ["OMP_NUM_THREADS"] = "1"

from fastapi import FastAPI, Depends
import logging
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models, schemas
from routers import user, spending, nudge_memory_logic, report, plaid, voice
from fastapi.staticfiles import StaticFiles
import threading
import time

# app instance
app = FastAPI()


# Create DB tables on startup instead of at import time to avoid test ordering side-effects
@app.on_event("startup")
def create_tables_on_startup():
    try:
        # Resolve the runtime engine from the database module so any test-time
        # monkeypatches (that replace database.engine) are respected.
        import database as _db

        # Test-only bootstrap: creates tables only when running in test/mock mode.
        try:
            from app.startup.test_db_bootstrap import maybe_create_all_for_tests

            maybe_create_all_for_tests(_db.engine)
            logging.getLogger(__name__).info("Test DB bootstrap completed (if applicable)")
        except Exception:
            # If the test bootstrap helper cannot run, log a warning but do not
            # prevent app startup from proceeding.
            logging.getLogger(__name__).warning("Test DB bootstrap could not run", exc_info=True)
    except Exception:
        # Avoid startup failure if resolving the runtime DB engine fails in
        # certain test setups.
        logging.getLogger(__name__).warning("Failed to resolve runtime DB engine during startup", exc_info=True)

# Mount static directory for audio and other static files
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(user.router)
app.include_router(spending.router)
app.include_router(nudge_memory_logic.router, prefix="/memory")
app.include_router(report.router)
app.include_router(plaid.router, prefix="/plaid")
# Include diagnostics router only in debug/dev mode
try:
    DEBUG = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")
    if DEBUG:
        from routers.plaid_diagnostics import router as plaid_diag_router
        app.include_router(plaid_diag_router, prefix="/plaid")
except Exception:
    # don't block startup if diagnostics router cannot be loaded
    pass
from routers.voice import router as voice_router
app.include_router(voice_router)
from routers.whatsapp import router as whatsapp_router
app.include_router(whatsapp_router)
from routers.whatsapp_webhook import router as whatsapp_webhook_router
app.include_router(whatsapp_webhook_router, prefix="/webhook", tags=["whatsapp"])
from routers.nudge_inspection import router as nudge_inspection_router
app.include_router(nudge_inspection_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Finivo AI"}


# Health endpoint: checks DB connectivity and returns status + timestamp
@app.get("/health")
def health():
    from datetime import datetime
    from sqlalchemy import text
    status = "ok"
    db_ok = False
    err = None
    try:
        sess = SessionLocal()
        try:
            res = sess.execute(text("SELECT 1"))
            # scalar() works with newer SQLAlchemy, fallback safe check
            try:
                val = res.scalar()
            except Exception:
                val = None
            db_ok = (val == 1) or (val is not None)
        finally:
            sess.close()
    except Exception as e:
        status = "error"
        err = str(e)

    return {
        "status": status,
        "db_ok": bool(db_ok),
        "error": err,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

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


# Startup tasks: ensure sandbox Plaid token is available for local/dev runs
try:
    # import lazily so imports don't break tests that patch DB
    from app.startup.plaid_bootstrap import ensure_sandbox_token

    @app.on_event("startup")
    async def startup_tasks():
        try:
            await ensure_sandbox_token()
        except Exception:
            import logging
            logging.exception("ensure_sandbox_token failed during startup")
except Exception:
    # Do not let startup fail if the bootstrap module cannot be imported or runs into issues
    pass
