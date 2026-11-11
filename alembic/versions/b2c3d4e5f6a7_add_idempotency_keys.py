"""add idempotency keys

Revision ID: b2c3d4e5f6a7
Revises: f0e1f2a3b4c5
Create Date: 2026-11-11

Implements T-100: stored responses for retried POST requests.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "f0e1f2a3b4c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "idempotency_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("path", sa.String(length=500), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "key", name="uq_idempotency_keys_user_key"),
    )
    op.create_index("ix_idempotency_keys_id", "idempotency_keys", ["id"])
    op.create_index(
        "ix_idempotency_keys_user_id", "idempotency_keys", ["user_id"]
    )
    op.create_index(
        "ix_idempotency_keys_created_at", "idempotency_keys", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_idempotency_keys_created_at", table_name="idempotency_keys")
    op.drop_index("ix_idempotency_keys_user_id", table_name="idempotency_keys")
    op.drop_index("ix_idempotency_keys_id", table_name="idempotency_keys")
    op.drop_table("idempotency_keys")
