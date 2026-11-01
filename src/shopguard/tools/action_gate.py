"""Deterministic Action Gate — 3-tier permission enforcement.

NO LLM involvement. All decisions are hard-coded policy rules.
"""

from __future__ import annotations
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Literal, Optional

from src.shopguard.logging_config import logger

ActionDecision = Literal["AUTO_ALLOWED", "CONFIRMATION_REQUIRED", "NEVER_PERMITTED"]

# Confirmation token TTL in minutes
CONFIRMATION_TTL_MINUTES = 5

# Actions that are never permitted regardless of any context
NEVER_PERMITTED_ACTIONS = {
    "execute_financial_refund",
    "transfer_money",
    "charge_payment_method",
    "modify_bank_details",
    "modify_card_details",
    "delete_audit_log",
    "delete_audit_records",
    "bypass_ownership_check",
    "mark_refund_paid",
    "override_refund_eligibility",
    "direct_financial_payout",
}

# Actions always allowed without confirmation
AUTO_ALLOWED_ACTIONS = {
    "check_order_status",
    "retrieve_policy",
    "view_shipment_events",
    "create_investigation_record",
    "record_audit_event",
    "view_order_history",
}

# Actions requiring eligibility check + explicit confirmation
CONFIRMATION_REQUIRED_ACTIONS = {
    "cancel_order",
    "submit_refund_review_request",
    "submit_return_request",
    "escalate_to_support",
}


def evaluate_action(
    action_name: str,
    customer_id: str,
    order_id: Optional[str],
    order_state: dict,
) -> dict:
    """Evaluate whether an action is permitted for the given customer and order.

    Returns a decision dict containing:
      - decision: AUTO_ALLOWED | CONFIRMATION_REQUIRED | NEVER_PERMITTED
      - reason: human-readable explanation
      - confirmation_token: (only for CONFIRMATION_REQUIRED)
      - expires_at: (only for CONFIRMATION_REQUIRED)
    """
    action_lower = action_name.lower().strip().replace(" ", "_")

    # --- Hard block: NEVER_PERMITTED ---
    if action_lower in NEVER_PERMITTED_ACTIONS:
        logger.warning("NEVER_PERMITTED action attempted: %s by %s", action_name, customer_id)
        return {
            "decision": "NEVER_PERMITTED",
            "reason":   (
                f"'{action_name}' is a permanently forbidden operation. "
                "This system does not execute financial transactions or modify payment records."
            ),
            "action":   action_lower,
        }

    # Detect action from free-text (from routing) and map to known keys
    mapped = _map_action(action_lower)

    # --- AUTO_ALLOWED ---
    if mapped in AUTO_ALLOWED_ACTIONS:
        return {
            "decision": "AUTO_ALLOWED",
            "reason":   f"'{mapped}' is a read/info operation and is automatically permitted.",
            "action":   mapped,
        }

    # --- CONFIRMATION_REQUIRED: eligibility checks ---
    if mapped == "cancel_order":
        return _handle_cancel(mapped, customer_id, order_id, order_state)

    if mapped == "submit_refund_review_request":
        return _handle_refund_review(mapped, customer_id, order_id, order_state)

    if mapped == "submit_return_request":
        return _handle_return(mapped, customer_id, order_id, order_state)

    if mapped == "escalate_to_support":
        return _issue_confirmation(mapped, customer_id, order_id,
                                   "Complaint escalation requires your confirmation.")

    # --- Unknown action: deny safely ---
    logger.warning("Unknown action '%s' requested by %s — denying.", action_name, customer_id)
    return {
        "decision": "NEVER_PERMITTED",
        "reason":   f"Unknown action '{action_name}'. Please contact support.",
        "action":   action_lower,
    }


# --------------------------------------------------------------------------- #
# Eligibility Checks                                                            #
# --------------------------------------------------------------------------- #

def _handle_cancel(action, customer_id, order_id, order_state) -> dict:
    status = order_state.get("order_status", "")
    if status in ("PLACED", "PROCESSING"):
        return _issue_confirmation(
            action, customer_id, order_id,
            f"Your order is in '{status}' status and is eligible for cancellation. "
            "Please confirm to proceed.",
        )
    return {
        "decision": "NEVER_PERMITTED",
        "reason":   f"Order cannot be cancelled. Current status: '{status}'. "
                    "Only PLACED or PROCESSING orders can be cancelled.",
        "action":   action,
    }


def _handle_refund_review(action, customer_id, order_id, order_state) -> dict:
    """Check refund eligibility: order must be DELIVERED and within 30-day window."""
    delivery_status = order_state.get("delivery_status", "")
    if delivery_status != "DELIVERED":
        return {
            "decision": "NEVER_PERMITTED",
            "reason":   f"Refund review can only be requested for DELIVERED orders. "
                        f"Current delivery status: '{delivery_status}'.",
            "action":   action,
        }

    # Check 30-day refund window
    order_date_str = order_state.get("order_date") or order_state.get("actual_delivery")
    if order_date_str:
        order_dt = _parse_dt(order_date_str)
        if order_dt:
            days_since = (datetime.now(timezone.utc) - order_dt).days
            if days_since > 30:
                return {
                    "decision": "NEVER_PERMITTED",
                    "reason":   f"Refund window has expired. Order/delivery was {days_since} days ago. "
                                "The policy allows 30 days from delivery.",
                    "action":   action,
                }

    return _issue_confirmation(
        action, customer_id, order_id,
        "Your order is eligible for a refund review request. "
        "A review case will be created and assigned to the operations team. "
        "Please confirm to submit.",
    )


def _handle_return(action, customer_id, order_id, order_state) -> dict:
    delivery_status = order_state.get("delivery_status", "")
    if delivery_status != "DELIVERED":
        return {
            "decision": "NEVER_PERMITTED",
            "reason":   "Return requests are only accepted for delivered orders.",
            "action":   action,
        }
    return _issue_confirmation(
        action, customer_id, order_id,
        "Return request is eligible. Please confirm to submit.",
    )


# --------------------------------------------------------------------------- #
# Token Management                                                              #
# --------------------------------------------------------------------------- #

def _issue_confirmation(action, customer_id, order_id, description) -> dict:
    """Issue a server-side expiring confirmation token."""
    token = f"ACT-CONF-{uuid.uuid4().hex[:12].upper()}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=CONFIRMATION_TTL_MINUTES)

    # Persist token to shopguard.db
    _store_token(token, customer_id, order_id or "", action,
                 {"description": description}, expires_at)

    return {
        "decision":           "CONFIRMATION_REQUIRED",
        "reason":             description,
        "action":             action,
        "confirmation_token": token,
        "expires_at":         expires_at.isoformat(),
        "ttl_minutes":        CONFIRMATION_TTL_MINUTES,
    }


def _store_token(token, customer_id, order_id, action_name, payload, expires_at) -> None:
    """Persist confirmation token to action_confirmations table."""
    try:
        from src.shopguard.database.connection import get_shopguard_db
        with get_shopguard_db() as conn:
            conn.execute(
                """INSERT INTO action_confirmations
                   (token, customer_id, order_id, action_name, payload_json, expires_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (token, customer_id, order_id, action_name,
                 json.dumps(payload), expires_at.strftime("%Y-%m-%d %H:%M:%S")),
            )
    except Exception as exc:
        logger.error("Failed to store confirmation token: %s", exc)


def consume_confirmation_token(token: str, customer_id: str, order_id: str) -> dict:
    """Validate and consume a confirmation token.

    Returns {"valid": True, "action": ...} or {"valid": False, "reason": ...}.
    """
    try:
        from src.shopguard.database.connection import get_shopguard_db
        with get_shopguard_db() as conn:
            row = conn.execute(
                """SELECT token, customer_id, order_id, action_name, expires_at, consumed
                   FROM action_confirmations WHERE token = ?""",
                (token,),
            ).fetchone()

            if not row:
                return {"valid": False, "reason": "Token not found or already consumed."}
            if row["consumed"]:
                return {"valid": False, "reason": "Token has already been used."}
            if row["customer_id"] != customer_id:
                return {"valid": False, "reason": "Token customer mismatch."}
            if row["order_id"] != order_id:
                return {"valid": False, "reason": "Token order mismatch."}

            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            if row["expires_at"] < now:
                return {"valid": False, "reason": f"Token expired at {row['expires_at']} UTC."}

            # Mark consumed
            conn.execute(
                "UPDATE action_confirmations SET consumed = 1 WHERE token = ?", (token,)
            )
            return {"valid": True, "action": row["action_name"]}
    except Exception as exc:
        logger.error("Token validation error: %s", exc)
        return {"valid": False, "reason": "Internal error during token validation."}


# --------------------------------------------------------------------------- #
# Helpers                                                                       #
# --------------------------------------------------------------------------- #

def _map_action(action_lower: str) -> str:
    """Map free-text action strings to canonical action keys."""
    if any(k in action_lower for k in ("cancel", "cancell")):
        return "cancel_order"
    if any(k in action_lower for k in ("refund", "reimburs", "money_back")):
        return "submit_refund_review_request"
    if any(k in action_lower for k in ("return", "send_back")):
        return "submit_return_request"
    if any(k in action_lower for k in ("escalate", "complaint", "claim")):
        return "escalate_to_support"
    if any(k in action_lower for k in ("status", "check", "view", "retrieve", "get")):
        return "check_order_status"
    return action_lower


def _parse_dt(ts_str: str) -> Optional[datetime]:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(ts_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None
