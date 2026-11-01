"""Incident Investigation Tool — evidence-based order issue analysis."""

from __future__ import annotations
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
import httpx

from src.shopguard.config import settings
from src.shopguard.logging_config import logger
from src.shopguard.tools.status_tool import _get, _verify_ownership

# Delay threshold: shipment is "stuck" if no event in this many hours
HUB_STUCK_THRESHOLD_HOURS = 24
# ETA overdue threshold in hours
OVERDUE_THRESHOLD_HOURS = 48


def _parse_dt(ts_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO/SQLite datetime string to UTC datetime."""
    if not ts_str:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            dt = datetime.strptime(ts_str, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def investigate_order(order_id: str, customer_id: str) -> dict:
    """Run a full investigation pipeline on an order.

    Steps:
      1. Fetch order data.
      2. Verify customer ownership.
      3. Fetch shipment events.
      4. Detect delays, stuck shipments, damage, missing items.
      5. Return structured findings with evidence and severity.
    """
    now = datetime.now(timezone.utc)

    # --- Step 1 & 2: Fetch order + verify ownership ---
    order = _get(f"/orders/{order_id}")
    if order is None:
        return _error_result(order_id, "Simulator unavailable.")
    if not _verify_ownership(order, customer_id):
        return _error_result(order_id, "Access denied: order does not belong to this customer.")

    # --- Step 3: Fetch events ---
    events_resp = _get(f"/orders/{order_id}/events")
    events = events_resp.get("events", []) if events_resp else []

    # --- Step 4: Analysis ---
    findings = []
    evidence  = []
    severity  = "low"
    issue     = "unknown"
    recommendation = "no_action_required"
    requires_human = False

    delivery_status = order.get("delivery_status", "")
    order_status    = order.get("order_status", "")
    estimated_dt    = _parse_dt(order.get("estimated_delivery"))
    actual_dt       = _parse_dt(order.get("actual_delivery"))

    # --- Check: genuine delivery delay ---
    if delivery_status in ("DELAYED", "IN_TRANSIT") and estimated_dt:
        hours_overdue = (now - estimated_dt).total_seconds() / 3600
        if hours_overdue > OVERDUE_THRESHOLD_HOURS:
            findings.append(
                f"Estimated delivery was {estimated_dt.strftime('%Y-%m-%d %H:%M')} UTC; "
                f"package is {int(hours_overdue)} hours overdue."
            )
            evidence.append({"source": "simulator:order", "detail": f"estimated_delivery={order.get('estimated_delivery')}"})
            severity = "medium"
            issue    = "delivery_delay"
            recommendation = "escalate_to_support"
            requires_human = True
        elif hours_overdue > 0:
            # ETA passed but within 48h — monitor, no escalation yet
            findings.append(
                f"Package is slightly past its estimated delivery date "
                f"({int(hours_overdue):.0f} hours). Within monitoring threshold."
            )
            severity = "low"
            issue    = "minor_delay"
            recommendation = "monitor"

    # --- Check: stuck at hub ---
    if events:
        latest_event = sorted(events, key=lambda e: e["timestamp"])[-1]
        latest_ts    = _parse_dt(latest_event.get("timestamp"))
        if latest_ts:
            hours_since = (now - latest_ts).total_seconds() / 3600
            event_type  = latest_event.get("event_type", "")
            if event_type == "DELAYED_HUB" and hours_since > HUB_STUCK_THRESHOLD_HOURS:
                findings.append(
                    f"Shipment has been stuck at '{latest_event.get('location')}' "
                    f"for {int(hours_since)} hours (last event: {event_type})."
                )
                evidence.append({
                    "source": "simulator:shipment_events",
                    "detail": f"Last event: {event_type} @ {latest_event.get('location')} on {latest_event.get('timestamp')}",
                })
                severity = "high" if hours_since > 72 else "medium"
                issue    = "shipment_stuck_at_hub"
                recommendation = "escalate_to_support"
                requires_human = True
        # Append all events as evidence
        for e in events[-3:]:
            evidence.append({
                "source": "simulator:shipment_events",
                "detail": f"{e.get('timestamp')} — {e.get('event_type')} @ {e.get('location')}: {e.get('description')}",
            })

    # --- Check: damaged package ---
    damaged_events = [e for e in events if "DAMAGE" in e.get("event_type", "").upper()]
    if damaged_events:
        findings.append("Damage was reported at a sorting facility during transit.")
        evidence.append({
            "source": "simulator:shipment_events",
            "detail": damaged_events[0].get("description", ""),
        })
        severity = "high"
        issue    = "damaged_package"
        recommendation = "initiate_return_or_refund_review"
        requires_human = True

    # --- Check: missing product (delivered but MISSING event) ---
    missing_events = [e for e in events if "MISSING" in e.get("event_type", "").upper() or
                      "missing" in e.get("description", "").lower()]
    if missing_events:
        findings.append("Package was reported delivered, but item was missing from the box.")
        severity = "high"
        issue    = "missing_product"
        recommendation = "initiate_return_or_refund_review"
        requires_human = True

    # --- Check: false alarm (in transit, ETA not passed) ---
    if not findings:
        if delivery_status == "IN_TRANSIT" and estimated_dt and estimated_dt > now:
            hours_remaining = (estimated_dt - now).total_seconds() / 3600
            findings.append(
                f"Shipment is in transit. Estimated delivery is in "
                f"{int(hours_remaining)} hours. No delay detected."
            )
            issue          = "false_alarm_in_transit"
            recommendation = "no_action_required"
            requires_human = False
        elif delivery_status == "DELIVERED" and actual_dt:
            findings.append(f"Order was successfully delivered on {actual_dt.strftime('%Y-%m-%d')}.")
            issue          = "no_issue_delivered"
            recommendation = "no_action_required"
        else:
            findings.append("No anomalies detected with the available data.")
            issue = "no_issue"

    return {
        "investigation_id": f"INV-{uuid.uuid4().hex[:8].upper()}",
        "order_id":         order_id,
        "issue":            issue,
        "severity":         severity,
        "findings":         findings,
        "evidence":         evidence,
        "recommendation":   recommendation,
        "requires_human":   requires_human,
        "order_snapshot": {
            "order_status":    order_status,
            "delivery_status": delivery_status,
            "estimated_delivery": order.get("estimated_delivery"),
            "actual_delivery":    order.get("actual_delivery"),
        },
    }


def _error_result(order_id: str, message: str) -> dict:
    return {
        "investigation_id": f"INV-ERR-{uuid.uuid4().hex[:6].upper()}",
        "order_id":   order_id,
        "issue":      "error",
        "severity":   "unknown",
        "findings":   [message],
        "evidence":   [],
        "recommendation": "escalate_to_support",
        "requires_human": True,
    }
