import os
import warnings
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="allow", case_sensitive=False)

    DATABASE_URL: str = ""


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
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True)
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
