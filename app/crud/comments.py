"""Task comment queries."""

from sqlalchemy.orm import Session, selectinload

from app import models, schemas

__all__ = [
    "create_comment",
    "get_comment_by_id",
    "get_comments_by_task",
    "update_comment",
    "delete_comment",
]


def create_comment(db: Session, comment: schemas.CommentCreate, task_id: int, user_id: int):
    """
    Create a comment on a task.

    Args:
        db (Session): SQLAlchemy database session.
        comment (CommentCreate): Schema with comment content.
        task_id (int): ID of the task to comment on.
        user_id (int): ID of the user creating the comment.

    Returns:
        Comment: The newly created comment.

    Example:
        >>> comment_data = CommentCreate(content="This looks great!")
        >>> new_comment = create_comment(db, comment_data, task_id=1, user_id=1)
    """
    db_comment = models.Comment(
        task_id=task_id,
        author_id=user_id,
        content=comment.content,
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment


def get_comment_by_id(db: Session, comment_id: int):
    """
    Retrieve a comment by its ID.

    Args:
        db (Session): SQLAlchemy database session.
        comment_id (int): The comment's unique identifier.

    Returns:
        Comment | None: The comment if found, None otherwise.
    """
    return db.query(models.Comment).filter(models.Comment.id == comment_id).first()


def get_comments_by_task(
    db: Session,
    task_id: int,
    page: int = 1,
    page_size: int = 20,
    order: str = "desc",
):
    """
    Get a page of comments for a task, ordered newest first by default.

    Returns a pagination envelope compatible with the rest of the API.
    """

    query = db.query(models.Comment).filter(models.Comment.task_id == task_id)
    total = query.count()
    pages = (total + page_size - 1) // page_size if total else 0
    if order == "asc":
        order_columns = (models.Comment.created_at.asc(), models.Comment.id.asc())
    else:
        order_columns = (models.Comment.created_at.desc(), models.Comment.id.desc())
    items = (
        query.options(selectinload(models.Comment.author))
        .order_by(*order_columns)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": pages,
        "has_next": page < pages,
    }


def update_comment(db: Session, comment_id: int, content: str):
    """
    Update a comment's content.

    Args:
        db (Session): SQLAlchemy database session.
        comment_id (int): ID of the comment to update.
        content (str): New comment content.

    Returns:
        Comment | None: Updated comment, or None if not found.

    Example:
        >>> update_comment(db, comment_id=1, content="Updated content")
    """
    db_comment = get_comment_by_id(db, comment_id)
    if db_comment:
        db_comment.content = content
        db.commit()
        db.refresh(db_comment)
    return db_comment


def delete_comment(db: Session, comment_id: int):
    """
    Delete a comment.

    Args:
        db (Session): SQLAlchemy database session.
        comment_id (int): ID of the comment to delete.

    Returns:
        Comment | None: The deleted comment, or None if not found.
    """
    db_comment = get_comment_by_id(db, comment_id)
    if db_comment:
        db.delete(db_comment)
        db.commit()
    return db_comment
