"""
TaskFlow API - Database Module

This module handles all database connection and session management.
It provides:
- SQLAlchemy engine configuration
- Connection pooling settings
- Session factory
- Dependency injection for FastAPI routes

The module supports:
- PostgreSQL (production)
- SQLite (development/testing)
- Connection pooling for production workloads
- Search path configuration for PostgreSQL
"""

import os
import warnings
from typing import Generator
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, declarative_base
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    """
    Database settings loaded from environment variables.
    
    Supports loading from .env file via pydantic-settings.
    All settings are case-insensitive for flexibility.
    """
    model_config = ConfigDict(env_file=".env", extra="allow", case_sensitive=False)

    DATABASE_URL: str = ""  # PostgreSQL connection string
    POOL_SIZE: int = 10  # Connection pool size
    MAX_OVERFLOW: int = 20  # Additional connections when pool is full
    POOL_PRE_PING: bool = True  # Verify connections before use


# Initialize settings singleton
settings = Settings()


# Get database URL from settings or environment
# Warns if not configured (database features will be unavailable)
DATABASE_URL = settings.DATABASE_URL or os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    warnings.warn("DATABASE_URL is not set, database functionality will be unavailable")


# Declarative base for SQLAlchemy models
# All models inherit from this base
Base = declarative_base()

# Global engine and session factory (singleton pattern)
_engine = None
_SessionLocal = None


def get_engine():
    """
    Get or create the SQLAlchemy database engine.
    
    Creates a singleton engine with the following features:
    - Connection pooling (size configurable)
    - Pre-ping to verify connections
    - PostgreSQL search path configuration
    
    The engine is created once and reused for all connections.
    
    Returns:
        Engine | None: SQLAlchemy engine instance, or None if DATABASE_URL not set.
    
    Example:
        >>> engine = get_engine()
        >>> with engine.connect() as conn:
        ...     conn.execute(text("SELECT 1"))
    """
    global _engine
    if _engine is None:
        if not DATABASE_URL:
            warnings.warn("DATABASE_URL is not set, returning None engine")
            return None
        
        # Configure PostgreSQL-specific settings
        connect_args = {}
        if DATABASE_URL.startswith("postgresql"):
            @event.listens_for(Engine, "connect")
            def set_search_path(dbapi_conn, connection_record):
                """
                Set PostgreSQL search path to 'public' schema.
                
                This prevents issues with tables being created in wrong schemas
                when using PostgreSQL with multiple schemas.
                """
                cursor = dbapi_conn.cursor()
                cursor.execute("SET search_path TO public")
                cursor.close()
        
        # Create engine with connection pooling
        _engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=settings.POOL_PRE_PING,  # Verify connections before use
            pool_size=settings.POOL_SIZE,  # Base pool size
            max_overflow=settings.MAX_OVERFLOW,  # Additional connections
            connect_args=connect_args,
        )
    return _engine


def get_session_local():
    """
    Get or create the SQLAlchemy session factory.
    
    Creates a singleton session factory bound to the engine.
    Sessions are created with:
    - autocommit=False: Explicit commit required
    - autoflush=False: Manual flush required
    
    Returns:
        sessionmaker | None: Session factory, or None if DATABASE_URL not set.
    
    Example:
        >>> SessionLocal = get_session_local()
        >>> with SessionLocal() as session:
        ...     session.query(User).all()
    """
    global _SessionLocal
    if _SessionLocal is None:
        if not DATABASE_URL:
            warnings.warn("DATABASE_URL is not set, returning None session")
            return None
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine()
        )
    return _SessionLocal


def get_db() -> Generator:
    """
    FastAPI dependency for database session injection.
    
    This is a generator function that FastAPI uses to inject
    a database session into route handlers. The session is
    automatically closed after the request completes.
    
    Yields:
        Session: SQLAlchemy database session.
    
    Returns:
        Generator: A generator that provides the session.
    
    Raises:
        Exception: Any exception from the database operation.
    
    Example:
        >>> @router.get("/users")
        ... def get_users(db: Session = Depends(get_db)):
        ...     return db.query(User).all()
    """
    db = get_session_local()()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions outside of FastAPI routes.
    
    Use this for background tasks, scripts, or other non-route code
    that needs database access.
    
    Yields:
        Session: SQLAlchemy database session.
    
    Example:
        >>> with get_db_context() as db:
        ...     user = db.query(User).first()
    """
    db = get_session_local()()
    try:
        yield db
    finally:
        db.close()
