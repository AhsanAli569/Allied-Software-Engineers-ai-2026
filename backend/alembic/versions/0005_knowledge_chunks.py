"""Add knowledge_chunks table for RAG over business knowledge

Revision ID: 0005_knowledge_chunks
Revises: 0004_user_date_of_birth
Create Date: 2026-08-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.models.types import GUID

revision: str = "0005_knowledge_chunks"
down_revision: Union[str, None] = "0004_user_date_of_birth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("source", sa.String(255), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source", "chunk_index", name="uq_knowledge_chunk_source_index"),
    )
    op.create_index("ix_knowledge_chunks_source", "knowledge_chunks", ["source"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_chunks_source", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
