"""add collections

Revision ID: 46a9e6d8e164
Revises: f64c241527bd
Create Date: 2026-07-03 15:19:32.785306

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "46a9e6d8e164"
down_revision: str | Sequence[str] | None = "f64c241527bd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "collections",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("external_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "collection_documents",
        sa.Column("collection_id", sa.BigInteger(), nullable=False),
        sa.Column("document_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["collections.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("collection_id", "document_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("collection_documents")
    op.drop_table("collections")
