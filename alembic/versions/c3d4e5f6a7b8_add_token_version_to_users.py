"""Add token_version to users

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-11-09 20:30:00.000000

Token versioning lets the API revoke every session for a user without
tracking individual refresh tokens. Changing the password increments the
version; old tokens carry the previous value and stop validating.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the token_version column with a safe default for existing rows."""
    op.add_column(
        'users',
        sa.Column('token_version', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade() -> None:
    """Remove the token version column."""
    op.drop_column('users', 'token_version')
