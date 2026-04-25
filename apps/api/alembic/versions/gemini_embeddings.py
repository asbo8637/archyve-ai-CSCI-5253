from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "20260424_0003"
down_revision: str | None = "20260328_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("document_chunks", "embedding")
    op.add_column(
        "document_chunks",
        sa.Column("embedding", Vector(768), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("document_chunks", "embedding")
    op.add_column(
        "document_chunks",
        sa.Column("embedding", Vector(1536), nullable=True),
    )
