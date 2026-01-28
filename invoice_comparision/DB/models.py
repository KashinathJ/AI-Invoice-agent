from sqlalchemy import create_engine, ForeignKey, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime, Boolean, CheckConstraint, TIMESTAMP, BigInteger,
    func, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID
import uuid
from DB.config import settings

# Create base class for models
Base = declarative_base()


class MismatchReport(Base):
    __tablename__ = "mismatch_contract"

    id = Column(Integer, primary_key=True, autoincrement=True)
    issue_category = Column(String)
    field = Column(String)
    contract_value = Column(Text)
    invoice_value = Column(Text)


# Engine and session will be created when needed
engine = None
SessionLocal = None


def get_engine():
    """Get or create the database engine with schema configuration"""
    global engine
    if engine is None:

        # Create the engine with schema configuration posed o r
        if 'postgresql' in settings.database_url.lower():
            # For PostgreSQL, create engine with schema in the URL
            db_url = settings.database_url
            if '?' in db_url:
                db_url += '&options=-csearch_path%3Dhkms,public'
            else:
                db_url += '?options=-csearch_path%3Dhkms,public'

            engine = create_engine(db_url)
        else:
            engine = create_engine(settings.database_url)

    return engine


def get_session_local():
    """Get or create the session local"""
    global SessionLocal
    if SessionLocal is None:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return SessionLocal


def get_db_session():
    """Get a database session with schema configuration"""

    SessionLocal = get_session_local()
    db = SessionLocal()

    # For PostgreSQL, ensure schema is set for this session
    if 'postgresql' in settings.database_url.lower():
        try:
            db.execute(text("SET search_path TO hkms, public"))
            db.commit()
        except Exception as e:
            # Schema setting is optional, continue if it fails
            pass

    return db
