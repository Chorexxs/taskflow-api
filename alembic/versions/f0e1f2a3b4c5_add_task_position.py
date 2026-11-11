"""add stable task position for Kanban columns

Revision ID: f0e1f2a3b4c5
Revises: d0e1f2a3b4c5
Create Date: 2026-11-11

Implements FR-TASK-08 / M-05: every task keeps a stable position inside its
(project, status) column. Existing tasks are backfilled in creation order with
gaps of 1024 so new cards can be inserted between them.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f0e1f2a3b4c5"
down_revision = "d0e1f2a3b4c5"
branch_labels = None
depends_on = None

POSITION_GAP = 1024


def upgrade() -> None:
    op.add_column("tasks", sa.Column("position", sa.Numeric(20, 10), nullable=True))

    connection = op.get_bind()
    tasks = connection.execute(
        sa.text(
            "SELECT id, project_id, status FROM tasks"
            " ORDER BY project_id, status, created_at, id"
        )
    ).fetchall()

    counters: dict[tuple[int, str], int] = {}
    for task in tasks:
        key = (task.project_id, task.status)
        counters[key] = counters.get(key, 0) + POSITION_GAP
        connection.execute(
            sa.text("UPDATE tasks SET position = :position WHERE id = :id"),
            {"position": counters[key], "id": task.id},
        )

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.alter_column(
            "position",
            existing_type=sa.Numeric(20, 10),
            nullable=False,
            server_default="0",
        )
        batch_op.create_index(
            "ix_tasks_project_status_position",
            ["project_id", "status", "position"],
        )


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_index("ix_tasks_project_status_position")
        batch_op.drop_column("position")
