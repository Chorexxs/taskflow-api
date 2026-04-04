import os
import uuid
import warnings
from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from sqlalchemy.orm import Session

load_dotenv()

from app.database import get_db


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="allow", case_sensitive=False)

    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15


settings = Settings()

SECRET_KEY = settings.SECRET_KEY or os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    warnings.warn("SECRET_KEY is not set, using a temporary key for development")
    SECRET_KEY = "temp-dev-key-do-not-use-in-production"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    token_jti = str(uuid.uuid4())
    to_encode.update({"exp": expire, "type": "refresh", "jti": token_jti})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def is_token_revoked(db: Session, token: str) -> bool:
    from app.models import RevokedToken
    revoked = db.query(RevokedToken).filter(RevokedToken.token == token).first()
    return revoked is not None


def revoke_token(db: Session, token: str, token_type: str = "access") -> None:
    from app.models import RevokedToken
    payload = jwt.decode(token, SECRET_KEY, algorithms=[settings.ALGORITHM])
    exp = payload.get("exp")
    expires_at = datetime.fromtimestamp(exp, tz=timezone.utc) if exp else datetime.now(timezone.utc) + timedelta(days=7)
    revoked_token = RevokedToken(token=token, token_type=token_type, expires_at=expires_at)
    db.add(revoked_token)
    db.commit()


def clean_expired_tokens(db: Session) -> None:
    from app.models import RevokedToken
    db.query(RevokedToken).filter(RevokedToken.expires_at < datetime.now(timezone.utc)).delete()
    db.commit()


def check_user_locked(db: Session, user) -> bool:
    if user.is_blocked:
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            return True
        else:
            user.is_blocked = False
            user.failed_login_attempts = 0
            user.locked_until = None
            db.commit()
    return False


def record_failed_login(db: Session, user) -> None:
    user.failed_login_attempts += 1
    if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
        user.is_blocked = True
        user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES)
    db.commit()


def reset_failed_login(db: Session, user) -> None:
    user.failed_login_attempts = 0
    user.is_blocked = False
    user.locked_until = None
    db.commit()


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
) -> "User":
    from app.crud import get_user_by_email

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_type = payload.get("type")
        if token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if is_token_revoked(db, token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user


async def get_current_user_from_refresh(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
) -> "User":
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_type = payload.get("type")
        if token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if is_token_revoked(db, token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    from app.crud import get_user_by_email
    user = get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user
