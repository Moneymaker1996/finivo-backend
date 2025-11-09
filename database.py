import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Read the database URL from environment (set DATABASE_URL in Render or your env)
# If DATABASE_URL is not provided, fall back to a local SQLite file so the app
# can start for local testing (useful for webhook verification and dev).
DATABASE_URL = os.getenv("DATABASE_URL")
USE_SQLITE_FALLBACK = False

# If DATABASE_URL isn't provided, allow constructing it from individual
# environment variables that we set at deploy time. This makes it easy to
# wire Cloud Run to Cloud SQL via --add-cloudsql-instances and a Secret
# Manager secret for the DB password (we map the secret to
# FINIVO_DB_PASSWORD). Example deployed envs:
#   FINIVO_DB_PASSWORD (secret)
#   CLOUD_SQL_CONNECTION_NAME=jovial-acronym-476213-q0:asia-south1:finivo-db
#   DB_USER (optional, default: postgres)
#   DB_NAME (optional, default: finivo)
if not DATABASE_URL:
    db_pass = os.getenv("FINIVO_DB_PASSWORD")
    cloudsql_conn = os.getenv("CLOUD_SQL_CONNECTION_NAME")
    db_user = os.getenv("DB_USER", "postgres")
    db_name = os.getenv("DB_NAME", "finivo")

    if db_pass and cloudsql_conn:
        # Use unix socket connection string format understood by psycopg2
        # and SQLAlchemy when running in Cloud Run with --add-cloudsql-instances.
        DATABASE_URL = f"postgresql+psycopg2://{db_user}:{db_pass}@/{db_name}?host=/cloudsql/{cloudsql_conn}"
    else:
        # Fallback to a lightweight local sqlite DB for development/testing
        DATABASE_URL = "sqlite:///./finivo_local.db"
        USE_SQLITE_FALLBACK = True

# Create the SQLAlchemy engine and session factory
# For SQLite we must pass connect_args to allow usage from multiple threads
engine_kwargs = {}
connect_args = {}
# Allow SQLite URLs (including test/explicit DATABASE_URL) to opt into the
# thread-safe connect arg so tests using FastAPI TestClient (which runs the
# app in another thread) won't hit SQLite thread checks.
if DATABASE_URL and DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args) if connect_args else create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Dependency to get DB session for FastAPI endpoints."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
