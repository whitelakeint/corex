"""
SQLAlchemy models for conversation history storage.
"""
import re
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()


class Conversation(Base):
    """Store conversation transcripts and metadata."""
    __tablename__ = 'conversations'

    id = Column(Integer, primary_key=True)
    conversation_id = Column(String(255), unique=True, nullable=False)
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    duration_seconds = Column(Integer)
    transcript = Column(Text)  # JSON string
    visitor_name = Column(String(255), nullable=True)
    recording_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def extract_visitor_name(transcript_text: str) -> Optional[str]:
    """
    Extract visitor name from transcript using regex patterns.

    Searches for common patterns like:
    - "I'm here to see John Smith"
    - "My name is Sarah Johnson"
    - "This is Michael Brown"
    - "I am David Wilson"

    Returns first match or None if not found.
    """
    patterns = [
        r"I'm here to see ([A-Z][a-z]+ [A-Z][a-z]+)",
        r"[Mm]y name is ([A-Z][a-z]+ [A-Z][a-z]+)",
        r"[Tt]his is ([A-Z][a-z]+ [A-Z][a-z]+)",
        r"I am ([A-Z][a-z]+ [A-Z][a-z]+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, transcript_text)
        if match:
            return match.group(1)

    return None


def init_db(database_url="sqlite:///conversations.db"):
    """
    Initialize database and create tables.

    Args:
        database_url: SQLAlchemy database URL

    Returns:
        SQLAlchemy engine instance
    """
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """
    Create database session.

    Args:
        engine: SQLAlchemy engine instance

    Returns:
        SQLAlchemy session instance
    """
    Session = sessionmaker(bind=engine)
    return Session()
