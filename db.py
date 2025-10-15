from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# PostgreSQL connection string
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:FinivoAIsecure2025@localhost:5432/FinivoAI_DB"

# SQLAlchemy setup
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
