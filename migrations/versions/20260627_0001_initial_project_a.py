"""initial project a schema

Revision ID: 20260627_0001
Revises:
Create Date: 2026-06-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260627_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("job_id", sa.Text(), primary_key=True),
        sa.Column("job_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="PENDING"),
        sa.Column("payload", sa.Text(), server_default="{}"),
        sa.Column("result", sa.Text(), server_default="{}"),
        sa.Column("error", sa.Text()),
        sa.Column("retry_count", sa.Integer(), server_default="0"),
        sa.Column("max_retries", sa.Integer(), server_default="3"),
        sa.Column("locked_by", sa.Text()),
        sa.Column("locked_at", sa.Text()),
        sa.Column("heartbeat_at", sa.Text()),
        sa.Column("timeout_seconds", sa.Integer(), server_default="300"),
        sa.Column("cancel_requested", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column("started_at", sa.Text()),
        sa.Column("finished_at", sa.Text()),
        if_not_exists=True,
    )
    op.create_table(
        "documents",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        if_not_exists=True,
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("actor_role", sa.Text()),
        sa.Column("resource_type", sa.Text()),
        sa.Column("resource_id", sa.Text()),
        sa.Column("summary", sa.Text()),
        sa.Column("metadata", sa.Text(), server_default="{}"),
        sa.Column("timestamp", sa.Text(), nullable=False),
        if_not_exists=True,
    )
    op.create_table(
        "chat_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("citations", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        if_not_exists=True,
    )
    op.create_table(
        "tickets",
        sa.Column("ticket_id", sa.Text(), primary_key=True),
        sa.Column("idempotency_key", sa.Text(), nullable=False, unique=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("diagnosis", sa.Text(), nullable=False),
        sa.Column("citations", sa.Text(), nullable=False),
        sa.Column("device_model", sa.Text()),
        sa.Column("fault_code", sa.Text()),
        sa.Column("risk_level", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("required_parts", sa.Text(), nullable=False),
        sa.Column("human_required", sa.Integer(), nullable=False),
        sa.Column("human_decision", sa.Text()),
        sa.Column("human_reviewer", sa.Text()),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column("closed_by", sa.Text()),
        sa.Column("closed_at", sa.Text()),
        if_not_exists=True,
    )
    op.create_table(
        "token_usage",
        sa.Column("request_id", sa.Text(), primary_key=True),
        sa.Column("module", sa.Text(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("estimated_cost", sa.Float(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        if_not_exists=True,
    )


def downgrade() -> None:
    for table in ["token_usage", "tickets", "chat_records", "audit_events", "documents", "jobs"]:
        op.drop_table(table, if_exists=True)
