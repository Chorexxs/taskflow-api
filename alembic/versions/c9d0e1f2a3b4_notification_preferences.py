"""notification preferences and dedupe keys

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-11-10

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c9d0e1f2a3b4"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "muted_notification_types",
                sa.String(length=200),
                nullable=False,
                server_default="",
            )
        )

    with op.batch_alter_table("notifications") as batch_op:
        batch_op.add_column(
            sa.Column("dedupe_key", sa.String(length=255), nullable=True)
        )
        batch_op.create_index(
            "ix_notifications_dedupe_key", ["dedupe_key"], unique=True
        )


def downgrade() -> None:
    with op.batch_alter_table("notifications") as batch_op:
        batch_op.drop_index("ix_notifications_dedupe_key")
        batch_op.drop_column("dedupe_key")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("muted_notification_types")
