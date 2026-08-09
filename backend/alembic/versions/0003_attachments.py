"""Add attachments table (image/document uploads)

Revision ID: 0003_attachments
Revises: 0002_seed_model_registry
Create Date: 2026-08-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.models.types import GUID

revision: str = "0003_attachments"
down_revision: Union[str, None] = "0002_seed_model_registry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "attachments",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conversation_id", GUID(), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message_id", GUID(), sa.ForeignKey("messages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.Enum("image", "document", name="attachmentkind", native_enum=False), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("uploading", "processing", "ready", "failed", name="attachmentstatus", native_enum=False),
            nullable=False,
            server_default="uploading",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_attachments_user_id", "attachments", ["user_id"])
    op.create_index("ix_attachments_conversation_id", "attachments", ["conversation_id"])
    op.create_index("ix_attachments_message_id", "attachments", ["message_id"])
    op.create_index("ix_attachments_storage_key", "attachments", ["storage_key"], unique=True)


def downgrade() -> None:
    op.drop_table("attachments")
