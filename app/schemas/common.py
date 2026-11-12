"""Validation helpers and shared schemas."""

import re

from pydantic import BaseModel

CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x1f\x7f-\x9f]")
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128

__all__ = [
    "validate_password",
    "sanitize_text",
    "CursorPaginatedResponse",
]


def validate_password(password: str) -> str:
    """Validate password length without altering the secret."""
    if not isinstance(password, str):
        raise ValueError("password must be a string")
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"password must be at least {PASSWORD_MIN_LENGTH} characters")
    if len(password) > PASSWORD_MAX_LENGTH:
        raise ValueError(f"password must be at most {PASSWORD_MAX_LENGTH} characters")
    return password


def sanitize_text(text: str) -> str:
    """
    Remove control characters from text input for security.

    Prevents XSS and injection attacks by stripping control characters
    (ASCII 0-31 and 127-159) that could be used maliciously.

    Args:
        text (str): The input text to sanitize.

    Returns:
        str: The sanitized text with control characters removed.

    Example:
        >>> sanitize_text("Hello\x00World")
        'HelloWorld'
        >>> sanitize_text("Test\r\n")
        'Test'
    """
    return CONTROL_CHARS_PATTERN.sub("", text).strip()


class CursorPaginatedResponse(BaseModel):
    """
    Schema for cursor-based pagination.

    Alternative pagination strategy for large datasets.

    Attributes:
        items (list): List of items for the current page
        next_cursor (str | None): Cursor for next page
        has_more (bool): Whether there are more items
    """

    items: list
    next_cursor: str | None = None
    has_more: bool = False
