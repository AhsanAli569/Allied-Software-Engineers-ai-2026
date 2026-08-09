"""Initial schema: users, sessions, ai_models, conversations, messages, audit_logs

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-09

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.models.types import GUID

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("user", "admin", "super_admin", name="userrole", native_enum=False), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "ai_models",
        sa.Column("model_id", sa.String(100), primary_key=True),
        sa.Column("display_name", sa.String(150), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("context_length", sa.Integer(), nullable=False, server_default="8192"),
        sa.Column("multimodal", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("vision_support", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("document_support", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("coding_support", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("reasoning_support", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("free_or_paid", sa.String(10), nullable=False, server_default="free"),
        sa.Column("rate_limit_info", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_ai_models_provider", "ai_models", ["provider"])
    op.create_index("ix_ai_models_active", "ai_models", ["active"])

    op.create_table(
        "sessions",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("refresh_token_hash", sa.String(64), nullable=False),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_refresh_token_hash", "sessions", ["refresh_token_hash"], unique=True)

    op.create_table(
        "conversations",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False, server_default="New chat"),
        sa.Column("model_id", sa.String(100), sa.ForeignKey("ai_models.model_id"), nullable=True),
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])

    op.create_table(
        "messages",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("conversation_id", GUID(), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.Enum("system", "user", "assistant", "tool", name="messagerole", native_enum=False), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("provider", sa.String(50), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "streaming", "complete", "cancelled", "failed", name="messagestatus", native_enum=False),
            nullable=False,
            server_default="complete",
        ),
        sa.Column("parent_message_id", GUID(), sa.ForeignKey("messages.id"), nullable=True),
        sa.Column("edited", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("regeneration_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("actor_user_id", GUID(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("target", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("result", sa.String(20), nullable=False, server_default="success"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("sessions")
    op.drop_table("ai_models")
    op.drop_table("users")
