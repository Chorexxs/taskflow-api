"""Shared CRUD helpers."""

import re
import unicodedata

__all__ = [
    "paginate_query",
    "slugify",
]


def paginate_query(query, page: int, page_size: int):
    """Return ``(items, total, pages)`` for a SQLAlchemy query.

    Callers are responsible for validating ``page``/``page_size``; keeping the
    helper small avoids duplicating the same count/offset logic in every list
    endpoint.
    """
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    pages = (total + page_size - 1) // page_size
    return items, total, pages


def slugify(value: str, fallback: str = "project") -> str:
    """Convert a display name into a URL-friendly slug."""
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug[:240].strip("-") or fallback
