"""Team-scoped search."""

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app import models

from ._common import paginate_query

__all__ = [
    "search_in_team",
]


def _like_pattern(query: str) -> str:
    """Build a safe LIKE pattern by escaping user wildcards."""
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _paginate_query(query, page: int, page_size: int):
    items, total, pages = paginate_query(query, page, page_size)
    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": pages,
        "has_next": page < pages,
    }


def search_in_team(
    db: Session,
    team_id: int,
    query: str,
    page: int = 1,
    page_size: int = 10,
):
    """
    Search projects and tasks in a team by name/title/description.

    The search is case-insensitive, escapes LIKE wildcards and returns
    independent pagination envelopes for projects and tasks.
    """

    pattern = _like_pattern(query)

    project_query = db.query(models.Project).filter(
        models.Project.team_id == team_id,
        models.Project.status == "active",
        or_(
            models.Project.name.ilike(pattern, escape="\\"),
            models.Project.description.ilike(pattern, escape="\\"),
        ),
    )
    task_query = (
        db.query(models.Task)
        .options(joinedload(models.Task.assignee))
        .join(models.Project, models.Task.project_id == models.Project.id)
        .filter(
            models.Project.team_id == team_id,
            models.Project.status == "active",
            or_(
                models.Task.title.ilike(pattern, escape="\\"),
                models.Task.description.ilike(pattern, escape="\\"),
            ),
        )
    )

    return {
        "projects": _paginate_query(project_query, page, page_size),
        "tasks": _paginate_query(task_query, page, page_size),
    }
