"""Seed the AI model registry with initial free-tier models

Revision ID: 0002_seed_model_registry
Revises: 0001_initial_schema
Create Date: 2026-08-09

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_seed_model_registry"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ai_models_table = sa.table(
    "ai_models",
    sa.column("model_id", sa.String),
    sa.column("display_name", sa.String),
    sa.column("provider", sa.String),
    sa.column("context_length", sa.Integer),
    sa.column("multimodal", sa.Boolean),
    sa.column("vision_support", sa.Boolean),
    sa.column("document_support", sa.Boolean),
    sa.column("coding_support", sa.Boolean),
    sa.column("reasoning_support", sa.Boolean),
    sa.column("active", sa.Boolean),
    sa.column("priority", sa.Integer),
    sa.column("free_or_paid", sa.String),
    sa.column("rate_limit_info", sa.JSON),
)

SEED_MODELS = [
    {
        "model_id": "gemini-2.0-flash",
        "display_name": "ASE Fast (Gemini 2.0 Flash)",
        "provider": "gemini",
        "context_length": 1_000_000,
        "multimodal": True,
        "vision_support": True,
        "document_support": True,
        "coding_support": True,
        "reasoning_support": False,
        "active": True,
        "priority": 10,
        "free_or_paid": "free",
        "rate_limit_info": {"notes": "Gemini free tier — see Google AI Studio for current limits"},
    },
    {
        "model_id": "llama-3.3-70b-versatile",
        "display_name": "ASE Balanced (Llama 3.3 70B via Groq)",
        "provider": "groq",
        "context_length": 128_000,
        "multimodal": False,
        "vision_support": False,
        "document_support": False,
        "coding_support": True,
        "reasoning_support": True,
        "active": True,
        "priority": 20,
        "free_or_paid": "free",
        "rate_limit_info": {"notes": "Groq free tier — see console.groq.com for current limits"},
    },
    {
        # OpenRouter rotates which models are actually free fairly often — this one was
        # verified working directly against their API on 2026-08-09. If it starts failing,
        # check https://openrouter.ai/models?max_price=0 and update this row (or just edit
        # it directly in the ai_models table — no migration needed for that, see spec on
        # the model registry being admin-editable at runtime).
        "model_id": "openai/gpt-oss-20b:free",
        "display_name": "ASE Fallback (GPT-OSS 20B via OpenRouter)",
        "provider": "openrouter",
        "context_length": 131_072,
        "multimodal": False,
        "vision_support": False,
        "document_support": False,
        "coding_support": True,
        "reasoning_support": True,
        "active": True,
        "priority": 30,
        "free_or_paid": "free",
        "rate_limit_info": {"notes": "OpenRouter free model — subject to OpenRouter's shared free-tier limits"},
    },
]


def upgrade() -> None:
    op.bulk_insert(ai_models_table, SEED_MODELS)


def downgrade() -> None:
    conn = op.get_bind()
    for m in SEED_MODELS:
        conn.execute(ai_models_table.delete().where(ai_models_table.c.model_id == m["model_id"]))
