"""add attachment checksum

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-11-10

"""

import hashlib

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b8c9d0e1f2a3"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "attachments", sa.Column("checksum", sa.String(length=64), nullable=True)
    )

    # Backfill checksums for attachments stored in PostgreSQL. Local files are
    # left NULL; new uploads always compute the checksum.
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, content FROM attachments WHERE content IS NOT NULL")
    ).fetchall()
    for row in rows:
        content = row.content
        if content is None:
            continue
        if isinstance(content, memoryview):
            content = content.tobytes()
        checksum = hashlib.sha256(content).hexdigest()
        connection.execute(
            sa.text("UPDATE attachments SET checksum = :checksum WHERE id = :id"),
            {"checksum": checksum, "id": row.id},
        )


def downgrade() -> None:
    op.drop_column("attachments", "checksum")
