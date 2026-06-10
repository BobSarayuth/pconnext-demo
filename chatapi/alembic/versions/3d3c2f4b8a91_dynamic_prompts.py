"""dynamic prompts

Revision ID: 3d3c2f4b8a91
Revises: 85371096002f
Create Date: 2026-06-09 17:20:00.000000

"""

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3d3c2f4b8a91"
down_revision: str | None = "85371096002f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PROMPT_FILE_SUFFIXES = {".md", ".txt"}


def _default_prompt_root() -> Path:
    return Path(__file__).resolve().parents[3] / "agentic" / "prompts"


def _default_prompt_rows() -> list[dict[str, object]]:
    root = _default_prompt_root()
    if not root.exists():
        return []

    now = datetime.now(UTC)
    rows: list[dict[str, object]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in PROMPT_FILE_SUFFIXES:
            continue
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "content": path.read_text(encoding="utf-8"),
                "createdDate": now,
                "updatedDate": now,
            }
        )
    return rows


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "dynamic_prompts",
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("createdDate", sa.TIMESTAMP(), nullable=False),
        sa.Column("updatedDate", sa.TIMESTAMP(), nullable=False),
        sa.PrimaryKeyConstraint("path"),
    )

    rows = _default_prompt_rows()
    if rows:
        dynamic_prompts = sa.table(
            "dynamic_prompts",
            sa.column("path", sa.String()),
            sa.column("content", sa.Text()),
            sa.column("createdDate", sa.TIMESTAMP()),
            sa.column("updatedDate", sa.TIMESTAMP()),
        )
        op.bulk_insert(dynamic_prompts, rows)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("dynamic_prompts")
