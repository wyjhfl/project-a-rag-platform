"""Audit event recording for Project A RAG Platform."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger("project_a")

def build_audit_event(
    action: str,
    actor_role: str,
    resource_type: str,
    resource_id: str,
    summary: str,
    metadata: dict | None = None,
) -> dict:
    return {
        "action": action,
        "actor_role": actor_role,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "summary": summary,
        "metadata": metadata or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

def record_audit_event(store, event: dict) -> None:
    try:
        if hasattr(store, "record_audit_event"):
            store.record_audit_event(event)
        else:
            logger.info("Audit event: %s %s %s", event["action"], event["resource_type"], event["resource_id"])
    except Exception as exc:
        logger.warning("Failed to record audit event: %s", exc)
