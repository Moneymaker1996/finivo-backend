
from sqlalchemy import create_engine, text
from models import Base
from db import SQLALCHEMY_DATABASE_URL

engine = create_engine(SQLALCHEMY_DATABASE_URL)

with engine.connect() as conn:
    conn.execute(text("DROP SCHEMA public CASCADE"))
    conn.execute(text("CREATE SCHEMA public"))

# Now re-create tables as per SQLAlchemy models
Base.metadata.create_all(bind=engine)

print("Database reset and tables recreated.")
