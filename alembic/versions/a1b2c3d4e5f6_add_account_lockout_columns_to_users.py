"""Add account lockout columns to users table

Revision ID: a1b2c3d4e5f6
Revises: 5fa676a88032
Create Date: 2026-04-06 10:00:00.000000

The initial migration already creates these columns in fresh databases.
This revision is kept for existing deployments and is intentionally
idempotent: it only adds/drops a column when it is missing/present.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '5fa676a88032'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _user_columns() -> set[str]:
    """Return the current column names for the users table."""
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns("users")}


def upgrade() -> None:
    """Add lockout columns only when they are missing."""
    columns = _user_columns()

    if "is_blocked" not in columns:
        op.add_column(
            'users',
            sa.Column('is_blocked', sa.Boolean(), nullable=True, server_default=sa.false()),
        )
    if "failed_login_attempts" not in columns:
        op.add_column(
            'users',
            sa.Column('failed_login_attempts', sa.Integer(), nullable=True, server_default=sa.text('0')),
        )
    if "locked_until" not in columns:
        op.add_column(
            'users',
            sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    """Drop lockout columns only when they exist."""
    columns = _user_columns()

    if "locked_until" in columns:
        op.drop_column('users', 'locked_until')
    if "failed_login_attempts" in columns:
        op.drop_column('users', 'failed_login_attempts')
    if "is_blocked" in columns:
        op.drop_column('users', 'is_blocked')
