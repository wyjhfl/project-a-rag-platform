"""add rag traces

Revision ID: 20260627_0002
Revises: 20260627_0001
Create Date: 2026-06-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260627_0002"
down_revision = "20260627_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rag_traces",
        sa.Column("trace_id", sa.Text(), primary_key=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("route", sa.Text(), server_default=""),
        sa.Column("rewritten_query", sa.Text(), server_default=""),
        sa.Column("retrieved_chunks", sa.Text(), server_default="[]"),
        sa.Column("selected_chunks", sa.Text(), server_default="[]"),
        sa.Column("citations", sa.Text(), server_default="[]"),
        sa.Column("tool_calls", sa.Text(), server_default="[]"),
        sa.Column("latency_ms", sa.Float(), server_default="0"),
        sa.Column("token_usage", sa.Text(), server_default="{}"),
        sa.Column("safety_warning", sa.Integer(), server_default="0"),
        sa.Column("insufficient", sa.Integer(), server_default="0"),
        sa.Column("raw_trace", sa.Text(), server_default="{}"),
        sa.Column("created_at", sa.Text(), nullable=False),
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_table("rag_traces", if_exists=True)
