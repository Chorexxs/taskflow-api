"""User queries and password handling."""

from datetime import datetime, timezone

from sqlalchemy import exists
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_password_hash, verify_password

__all__ = [
    "get_user_by_email",
    "get_user_by_id",
    "get_user_with_revocation",
    "create_user",
    "update_user",
    "authenticate_user",
]


def get_user_by_email(db: Session, email: str):
    """
    Retrieve a user by their email address.

    Used for authentication and user lookup. Email lookups are
    case-sensitive in most databases, but could be adapted for
    case-insensitive matching.

    Args:
        db (Session): SQLAlchemy database session.
        email (str): The user's email address to search for.

    Returns:
        User | None: The user if found, None otherwise.

    Example:
        >>> user = get_user_by_email(db, "user@example.com")
        >>> if user:
        ...     print(f"Found: {user.email}")
    """
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_with_revocation(db: Session, email: str, token: str):
    """Fetch a user and the revocation status of a token in one round trip.

    ``get_current_user`` needs both pieces on every authenticated request.
    Combining them halves the fixed database cost of the auth check.
    """
    token_revoked = exists().where(models.RevokedToken.token == token)
    return (
        db.query(models.User, token_revoked.label("token_revoked"))
        .filter(models.User.email == email)
        .first()
    )


def get_user_by_id(db: Session, user_id: int):
    """
    Retrieve a user by their ID.

    Used when you have a user ID and need to fetch the full user object.

    Args:
        db (Session): SQLAlchemy database session.
        user_id (int): The user's unique identifier.

    Returns:
        User | None: The user if found, None otherwise.

    Example:
        >>> user = get_user_by_id(db, 123)
    """
    return db.query(models.User).filter(models.User.id == user_id).first()


def create_user(
    db: Session,
    user: schemas.UserCreate,
    *,
    email_verified: bool = True,
):
    """
    Create a new user in the database.

    Hashes the password using bcrypt before storing. The user is created
    with default values: is_active=True, is_blocked=False, failed_login_attempts=0.

    Args:
        db (Session): SQLAlchemy database session.
        user (UserCreate): Schema containing email and password.
        email_verified (bool): Initial verification state (T-113).

    Returns:
        User: The newly created user object with ID and timestamps.

    Raises:
        sqlalchemy.exc.IntegrityError: If email already exists (unique constraint).

    Example:
        >>> user_data = UserCreate(email="new@example.com", password="secure123")
        >>> new_user = create_user(db, user_data)
    """
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        email_verified=email_verified,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user_id: int, user_update: schemas.UserUpdate):
    """
    Update an existing user's email or password.

    Only updates fields that are provided (not None). If password is provided,
    it gets rehashed. Email updates are rare and should be validated.

    Args:
        db (Session): SQLAlchemy database session.
        user_id (int): ID of the user to update.
        user_update (UserUpdate): Schema with new email and/or password.

    Returns:
        User | None: Updated user object, or None if user not found.

    Example:
        >>> update = UserCreate(email="new@example.com", password="newpass")
        >>> updated = update_user(db, 123, update)
    """
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None
    if user_update.password:
        db_user.hashed_password = get_password_hash(user_update.password)
        db_user.password_changed_at = datetime.now(timezone.utc)
        # Invalidate every existing session (access and refresh tokens).
        db_user.token_version = (db_user.token_version or 0) + 1
    if user_update.email:
        db_user.email = user_update.email
        db_user.token_version = (db_user.token_version or 0) + 1
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, email: str, password: str):
    """
    Authenticate a user with email and password.

    This is a convenience function that checks both email existence
    and password validity. Used in the login endpoint.

    Args:
        db (Session): SQLAlchemy database session.
        email (str): User's email address.
        password (str): Plain text password to verify.

    Returns:
        User | bool: User object if authentication succeeds, False otherwise.

    Example:
        >>> result = authenticate_user(db, "user@example.com", "password123")
        >>> if result:
        ...     print("Authenticated!")
    """
    user = get_user_by_email(db, email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user
