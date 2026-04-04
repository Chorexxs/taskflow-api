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
    model_config = ConfigDict(env_file=".env", extra="allow", case_sensitive=False)

    DATABASE_URL: str = ""
    POOL_SIZE: int = 10
    MAX_OVERFLOW: int = 20
    POOL_PRE_PING: bool = True


settings = Settings()

DATABASE_URL = settings.DATABASE_URL or os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    warnings.warn("DATABASE_URL is not set, database functionality will be unavailable")


Base = declarative_base()

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        if not DATABASE_URL:
            warnings.warn("DATABASE_URL is not set, returning None engine")
            return None
        
        connect_args = {}
        if DATABASE_URL.startswith("postgresql"):
            @event.listens_for(Engine, "connect")
            def set_search_path(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("SET search_path TO public")
                cursor.close()
        
        _engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=settings.POOL_PRE_PING,
            pool_size=settings.POOL_SIZE,
            max_overflow=settings.MAX_OVERFLOW,
            connect_args=connect_args,
        )
    return _engine


def get_session_local():
    global _SessionLocal
    if _SessionLocal is None:
        if not DATABASE_URL:
            warnings.warn("DATABASE_URL is not set, returning None session")
            return None
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


def get_db() -> Generator:
    db = get_session_local()()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    db = get_session_local()()
    try:
        yield db
    finally:
        db.close()
