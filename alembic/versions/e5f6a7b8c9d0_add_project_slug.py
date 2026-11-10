"""add team-scoped project slug

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-11-10

"""

import re
import unicodedata

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def _slugify(value: str) -> str:
    normalized = (
        unicodedata.normalize("NFKD", value or "")
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")[:240] or "project"


def upgrade() -> None:
    op.add_column("projects", sa.Column("slug", sa.String(length=255), nullable=True))

    connection = op.get_bind()
    projects = connection.execute(
        sa.text("SELECT id, team_id, name FROM projects ORDER BY id")
    ).fetchall()

    used: dict[tuple[int, str], int] = {}
    for project in projects:
        base = _slugify(project.name)
        candidate = base
        suffix = 2
        while (project.team_id, candidate) in used:
            candidate = f"{base}-{suffix}"
            suffix += 1
        used[(project.team_id, candidate)] = project.id
        connection.execute(
            sa.text("UPDATE projects SET slug = :slug WHERE id = :id"),
            {"slug": candidate, "id": project.id},
        )

    with op.batch_alter_table("projects") as batch_op:
        batch_op.alter_column(
            "slug", existing_type=sa.String(length=255), nullable=False
        )
        batch_op.create_unique_constraint(
            "uq_projects_team_slug", ["team_id", "slug"]
        )
        batch_op.create_index("ix_projects_slug", ["slug"])


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_index("ix_projects_slug")
        batch_op.drop_constraint("uq_projects_team_slug", type_="unique")
        batch_op.drop_column("slug")
