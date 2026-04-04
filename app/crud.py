from datetime import datetime
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_password_hash, verify_password


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user_id: int, user_update: schemas.UserCreate):
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None
    if user_update.password:
        db_user.hashed_password = get_password_hash(user_update.password)
    if user_update.email:
        db_user.email = user_update.email
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_team(db: Session, team: schemas.TeamCreate, user_id: int):
    db_team = models.Team(
        name=team.name,
        slug=team.slug,
        description=team.description,
        created_by=user_id,
    )
    db.add(db_team)
    db.commit()
    db.refresh(db_team)

    member = models.TeamMember(
        team_id=db_team.id,
        user_id=user_id,
        role="admin",
    )
    db.add(member)
    db.commit()

    return db_team


def get_team_by_id(db: Session, team_id: int):
    return db.query(models.Team).filter(models.Team.id == team_id).first()


def get_team_by_slug(db: Session, slug: str):
    return db.query(models.Team).filter(models.Team.slug == slug).first()


def get_teams_by_user(db: Session, user_id: int):
    return (
        db.query(models.Team)
        .join(models.TeamMember)
        .filter(models.TeamMember.user_id == user_id)
        .all()
    )


def add_member(db: Session, team_id: int, user_id: int, role: str):
    member = models.TeamMember(
        team_id=team_id,
        user_id=user_id,
        role=role,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def remove_member(db: Session, team_id: int, user_id: int):
    member = (
        db.query(models.TeamMember)
        .filter(
            models.TeamMember.team_id == team_id,
            models.TeamMember.user_id == user_id,
        )
        .first()
    )
    if member:
        db.delete(member)
        db.commit()
    return member


def get_team_members(db: Session, team_id: int):
    return db.query(models.TeamMember).filter(models.TeamMember.team_id == team_id).all()


def get_team_member(db: Session, team_id: int, user_id: int):
    return (
        db.query(models.TeamMember)
        .filter(
            models.TeamMember.team_id == team_id,
            models.TeamMember.user_id == user_id,
        )
        .first()
    )


def update_member_role(db: Session, team_id: int, user_id: int, role: str):
    member = get_team_member(db, team_id, user_id)
    if member:
        member.role = role
        db.commit()
        db.refresh(member)
    return member


def create_project(db: Session, project: schemas.ProjectCreate, team_id: int, user_id: int):
    db_project = models.Project(
        team_id=team_id,
        name=project.name,
        description=project.description,
        created_by=user_id,
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


def get_project_by_id(db: Session, project_id: int):
    return db.query(models.Project).filter(models.Project.id == project_id).first()


def get_projects_by_team(db: Session, team_id: int, include_archived: bool = False):
    query = db.query(models.Project).filter(models.Project.team_id == team_id)
    if not include_archived:
        query = query.filter(models.Project.status == "active")
    return query.all()


def update_project(db: Session, project_id: int, project_update: schemas.ProjectUpdate):
    db_project = get_project_by_id(db, project_id)
    if not db_project:
        return None
    if project_update.name is not None:
        db_project.name = project_update.name
    if project_update.description is not None:
        db_project.description = project_update.description
    if project_update.status is not None:
        db_project.status = project_update.status.value
    db.commit()
    db.refresh(db_project)
    return db_project


def archive_project(db: Session, project_id: int):
    db_project = get_project_by_id(db, project_id)
    if db_project:
        db_project.status = "archived"
        db.commit()
        db.refresh(db_project)
    return db_project


def create_task(db: Session, task: schemas.TaskCreate, project_id: int, user_id: int):
    db_task = models.Task(
        project_id=project_id,
        title=task.title,
        description=task.description,
        priority=task.priority.value,
        due_date=task.due_date,
        created_by=user_id,
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def get_task_by_id(db: Session, task_id: int):
    return db.query(models.Task).filter(models.Task.id == task_id).first()


def get_tasks_by_project(
    db: Session,
    project_id: int,
    status: str = None,
    priority: str = None,
    assigned_to: int = None,
    due_before: datetime = None,
    due_after: datetime = None,
    sort_by: str = "created_at",
    order: str = "desc",
    page: int = 1,
    page_size: int = 20,
):
    query = db.query(models.Task).filter(models.Task.project_id == project_id)
    
    if status:
        query = query.filter(models.Task.status == status)
    if priority:
        query = query.filter(models.Task.priority == priority)
    if assigned_to is not None:
        query = query.filter(models.Task.assigned_to == assigned_to)
    if due_before:
        query = query.filter(models.Task.due_date <= due_before)
    if due_after:
        query = query.filter(models.Task.due_date >= due_after)
    
    if sort_by == "title":
        order_col = models.Task.title
    elif sort_by == "due_date":
        order_col = models.Task.due_date
    elif sort_by == "priority":
        order_col = models.Task.priority
    elif sort_by == "status":
        order_col = models.Task.status
    else:
        order_col = models.Task.created_at
    
    if order == "asc":
        query = query.order_by(order_col.asc())
    else:
        query = query.order_by(order_col.desc())
    
    total = query.count()
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()
    
    return {"items": items, "total": total, "page": page, "pages": (total + page_size - 1) // page_size}


def update_task(db: Session, task_id: int, task_update: schemas.TaskUpdate):
    db_task = get_task_by_id(db, task_id)
    if not db_task:
        return None
    if task_update.title is not None:
        db_task.title = task_update.title
    if task_update.description is not None:
        db_task.description = task_update.description
    if task_update.status is not None:
        db_task.status = task_update.status.value
    if task_update.priority is not None:
        db_task.priority = task_update.priority.value
    if task_update.due_date is not None:
        db_task.due_date = task_update.due_date
    db.commit()
    db.refresh(db_task)
    return db_task


def assign_task(db: Session, task_id: int, user_id: int | None):
    db_task = get_task_by_id(db, task_id)
    if db_task:
        db_task.assigned_to = user_id
        db.commit()
        db.refresh(db_task)
    return db_task


def delete_task(db: Session, task_id: int):
    db_task = get_task_by_id(db, task_id)
    if db_task:
        db.delete(db_task)
        db.commit()
    return db_task


def create_comment(db: Session, comment: schemas.CommentCreate, task_id: int, user_id: int):
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
    return db.query(models.Comment).filter(models.Comment.id == comment_id).first()


def get_comments_by_task(db: Session, task_id: int):
    return db.query(models.Comment).filter(models.Comment.task_id == task_id).order_by(models.Comment.created_at.desc()).all()


def update_comment(db: Session, comment_id: int, content: str):
    db_comment = get_comment_by_id(db, comment_id)
    if db_comment:
        db_comment.content = content
        db.commit()
        db.refresh(db_comment)
    return db_comment


def delete_comment(db: Session, comment_id: int):
    db_comment = get_comment_by_id(db, comment_id)
    if db_comment:
        db.delete(db_comment)
        db.commit()
    return db_comment


def log_activity(db: Session, entity_type: str, entity_id: int, action: str, user_id: int, old_value: str = None, new_value: str = None):
    db_activity = models.ActivityLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        changed_by=user_id,
        old_value=old_value,
        new_value=new_value,
    )
    db.add(db_activity)
    db.commit()
    db.refresh(db_activity)
    return db_activity


def get_activity_by_task(db: Session, task_id: int):
    return db.query(models.ActivityLog).filter(
        models.ActivityLog.entity_type == "task",
        models.ActivityLog.entity_id == task_id
    ).order_by(models.ActivityLog.created_at.desc()).all()


def get_activity_by_project(db: Session, project_id: int):
    return db.query(models.ActivityLog).filter(
        models.ActivityLog.entity_type == "project",
        models.ActivityLog.entity_id == project_id
    ).order_by(models.ActivityLog.created_at.desc()).all()


def search_in_team(db: Session, team_id: int, query: str):
    projects = db.query(models.Project).filter(
        models.Project.team_id == team_id,
        models.Project.status == "active",
        models.Project.name.ilike(f"%{query}%")
    ).all()
    
    project_ids = [p.id for p in projects]
    
    tasks = []
    if project_ids:
        tasks = db.query(models.Task).filter(
            models.Task.project_id.in_(project_ids),
            models.Task.title.ilike(f"%{query}%")
        ).all()
    
    return {"projects": projects, "tasks": tasks}


def create_attachment(db: Session, task_id: int, user_id: int, filename: str, file_path: str, file_size: int, mime_type: str):
    db_attachment = models.Attachment(
        task_id=task_id,
        uploaded_by=user_id,
        filename=filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=mime_type,
    )
    db.add(db_attachment)
    db.commit()
    db.refresh(db_attachment)
    return db_attachment


def get_attachment_by_id(db: Session, attachment_id: int):
    return db.query(models.Attachment).filter(models.Attachment.id == attachment_id).first()


def get_attachments_by_task(db: Session, task_id: int):
    return db.query(models.Attachment).filter(models.Attachment.task_id == task_id).all()


def delete_attachment(db: Session, attachment_id: int):
    db_attachment = get_attachment_by_id(db, attachment_id)
    if db_attachment:
        db.delete(db_attachment)
        db.commit()
    return db_attachment


def create_notification(db: Session, user_id: int, notification_type: str, entity_type: str, entity_id: int, message: str):
    db_notification = models.Notification(
        user_id=user_id,
        type=notification_type,
        entity_type=entity_type,
        entity_id=entity_id,
        message=message,
    )
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification


def get_notifications_by_user(db: Session, user_id: int, is_read: bool = None):
    query = db.query(models.Notification).filter(models.Notification.user_id == user_id)
    if is_read is not None:
        query = query.filter(models.Notification.is_read == is_read)
    return query.order_by(models.Notification.created_at.desc()).all()


def get_notification_by_id(db: Session, notification_id: int):
    return db.query(models.Notification).filter(models.Notification.id == notification_id).first()


def mark_notification_read(db: Session, notification_id: int):
    db_notification = get_notification_by_id(db, notification_id)
    if db_notification:
        db_notification.is_read = True
        db.commit()
        db.refresh(db_notification)
    return db_notification


def mark_all_notifications_read(db: Session, user_id: int):
    db.query(models.Notification).filter(
        models.Notification.user_id == user_id,
        models.Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
