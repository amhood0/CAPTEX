"""
Database configuration and session management
"""
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlite3 import Connection as SQLiteConnection
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from app.config import settings

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
    echo=settings.DEBUG
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="The change conflicts with existing records") from error
    finally:
        db.close()

@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(connection, connection_record):
    """Enforce declared relationships on every SQLite connection."""
    if isinstance(connection, SQLiteConnection):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
