"""add attachment storage key

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-11-10

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d0e1f2a3b4c5"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "attachments", sa.Column("storage_key", sa.String(length=500), nullable=True)
    )
    op.create_index("ix_attachments_storage_key", "attachments", ["storage_key"])


def downgrade() -> None:
    op.drop_index("ix_attachments_storage_key", table_name="attachments")
    op.drop_column("attachments", "storage_key")
