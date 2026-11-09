"""Add database-backed attachment content

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-11-09 21:30:00.000000

Render's filesystem is ephemeral. Storing small attachments in PostgreSQL
keeps them available across deploys without requiring object-storage keys.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # batch_alter_table keeps this migration portable to SQLite (dev/CI).
    with op.batch_alter_table('attachments') as batch_op:
        batch_op.add_column(sa.Column('content', sa.LargeBinary(), nullable=True))
        batch_op.alter_column(
            'file_path',
            existing_type=sa.String(length=500),
            nullable=True,
        )


def downgrade() -> None:
    # Rows without a local path cannot be restored to the old NOT NULL schema.
    op.execute("UPDATE attachments SET file_path = '' WHERE file_path IS NULL")
    with op.batch_alter_table('attachments') as batch_op:
        batch_op.alter_column(
            'file_path',
            existing_type=sa.String(length=500),
            nullable=False,
        )
        batch_op.drop_column('content')
