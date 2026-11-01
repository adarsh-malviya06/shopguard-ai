"""Append-only audit service — writes to SQLite and logs/audit.jsonl."""

from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from src.shopguard.config import settings
from src.shopguard.logging_config import logger


def record_audit_event(
    request_id: str,
    actor: str,
    operation: str,
    decision: str,
    status: str,
    resource_id: str | None = None,
    details: dict | None = None,
) -> str:
    """Append an audit event to shopguard.db AND logs/audit.jsonl.

    Returns the generated event_id.
    """
    event_id  = f"AUD-{uuid.uuid4().hex[:10].upper()}"
    timestamp = datetime.now(timezone.utc).isoformat()

    # Strip sensitive keys from details
    safe_details = _sanitise(details or {})

    # Write to SQLite
    try:
        from src.shopguard.database.connection import get_shopguard_db
        with get_shopguard_db() as conn:
            conn.execute(
                """INSERT INTO audit_events
                   (event_id, request_id, timestamp, actor, operation,
                    resource_id, decision, status, details_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (event_id, request_id, timestamp, actor, operation,
                 resource_id, decision, status, json.dumps(safe_details)),
            )
    except Exception as exc:
        logger.error("Audit DB write failed: %s", exc)

    # Append to JSONL
    try:
        settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        entry = {
            "event_id":    event_id,
            "request_id":  request_id,
            "timestamp":   timestamp,
            "actor":       actor,
            "operation":   operation,
            "resource_id": resource_id,
            "decision":    decision,
            "status":      status,
            "details":     safe_details,
        }
        with open(settings.AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as exc:
        logger.error("Audit JSONL write failed: %s", exc)

    return event_id


def _sanitise(details: dict) -> dict:
    """Remove sensitive keys from audit details."""
    BLOCKED = {"password", "card_number", "api_key", "token", "secret", "cvv", "pin"}
    return {k: v for k, v in details.items() if k.lower() not in BLOCKED}
