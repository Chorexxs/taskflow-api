"""harden schema: audit columns, enum checks and read indexes

Revision ID: a7b8c9d0e1f2
Revises: e5f6a7b8c9d0
Create Date: 2026-11-10

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a7b8c9d0e1f2"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True)
        )

    with op.batch_alter_table("teams") as batch_op:
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            )
        )

    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            )
        )

    with op.batch_alter_table("team_members") as batch_op:
        batch_op.create_check_constraint(
            "ck_team_members_role", "role IN ('admin', 'member')"
        )

    with op.batch_alter_table("projects") as batch_op:
        batch_op.create_check_constraint(
            "ck_projects_status", "status IN ('active', 'archived')"
        )

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.create_check_constraint(
            "ck_tasks_status", "status IN ('todo', 'in_progress', 'done')"
        )
        batch_op.create_check_constraint(
            "ck_tasks_priority", "priority IN ('low', 'medium', 'high')"
        )

    with op.batch_alter_table("revoked_tokens") as batch_op:
        batch_op.create_check_constraint(
            "ck_revoked_tokens_type", "token_type IN ('access', 'refresh')"
        )

    with op.batch_alter_table("notifications") as batch_op:
        batch_op.create_check_constraint(
            "ck_notifications_type",
            "type IN ('assigned', 'commented', 'mentioned')",
        )

    op.create_index("ix_team_members_user_id", "team_members", ["user_id"])
    op.create_index(
        "ix_team_members_team_role", "team_members", ["team_id", "role"]
    )
    op.create_index(
        "ix_projects_team_status_created",
        "projects",
        ["team_id", "status", "created_at"],
    )
    op.create_index(
        "ix_tasks_project_assignee_status",
        "tasks",
        ["project_id", "assigned_to", "status"],
    )
    op.create_index(
        "ix_tasks_project_due_date", "tasks", ["project_id", "due_date"]
    )
    op.create_index(
        "ix_comments_task_created", "comments", ["task_id", "created_at"]
    )
    op.create_index(
        "ix_attachments_task_created", "attachments", ["task_id", "created_at"]
    )
    op.create_index(
        "ix_notifications_user_read_created",
        "notifications",
        ["user_id", "is_read", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_user_read_created", table_name="notifications")
    op.drop_index("ix_attachments_task_created", table_name="attachments")
    op.drop_index("ix_comments_task_created", table_name="comments")
    op.drop_index("ix_tasks_project_due_date", table_name="tasks")
    op.drop_index("ix_tasks_project_assignee_status", table_name="tasks")
    op.drop_index("ix_projects_team_status_created", table_name="projects")
    op.drop_index("ix_team_members_team_role", table_name="team_members")
    op.drop_index("ix_team_members_user_id", table_name="team_members")

    with op.batch_alter_table("notifications") as batch_op:
        batch_op.drop_constraint("ck_notifications_type", type_="check")

    with op.batch_alter_table("revoked_tokens") as batch_op:
        batch_op.drop_constraint("ck_revoked_tokens_type", type_="check")

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_constraint("ck_tasks_priority", type_="check")
        batch_op.drop_constraint("ck_tasks_status", type_="check")

    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_constraint("ck_projects_status", type_="check")

    with op.batch_alter_table("team_members") as batch_op:
        batch_op.drop_constraint("ck_team_members_role", type_="check")

    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("updated_at")

    with op.batch_alter_table("teams") as batch_op:
        batch_op.drop_column("updated_at")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("password_changed_at")
        batch_op.drop_column("last_login_at")
        batch_op.drop_column("updated_at")
