from datetime import timedelta
import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from functools import wraps

from app import crud, schemas
from app.database import get_db
from app.auth import (
    settings,
    create_access_token,
    create_refresh_token,
    verify_password,
    revoke_token,
    check_user_locked,
    record_failed_login,
    reset_failed_login,
)

router = APIRouter()

limiter = Limiter(key_func=get_remote_address)


def rate_limit_decorator(limit_str: str):
    if os.environ.get("TESTING"):
        def decorator(func):
            return func
        return decorator
    return limiter.limit(limit_str)


@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
@rate_limit_decorator("5/minute")
def register(request: Request, user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)


@router.post("/login", response_model=schemas.Token)
@rate_limit_decorator("10/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, email=form_data.username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if check_user_locked(db, user):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account temporarily locked due to too many failed login attempts",
        )
    
    if not verify_password(form_data.password, user.hashed_password):
        record_failed_login(db, user)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    reset_failed_login(db, user)
    
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=schemas.Token)
def refresh(refresh_token: str, db: Session = Depends(get_db)):
    from app.auth import get_current_user_from_refresh
    
    user = get_current_user_from_refresh(refresh_token, db)
    
    revoke_token(db, refresh_token, "refresh")
    
    new_access_token = create_access_token(data={"sub": user.email})
    new_refresh_token = create_refresh_token(data={"sub": user.email})
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db), current_user: schemas.UserOut = Depends(crud.get_current_user_from_token)):
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            revoke_token(db, token, "access")
        except Exception:
            pass
    return {"message": "Successfully logged out"}
