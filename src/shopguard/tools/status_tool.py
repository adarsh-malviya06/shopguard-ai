"""Status Tool — retrieves live order/shipment data from the Simulator."""

from __future__ import annotations
import httpx
from src.shopguard.config import settings
from src.shopguard.logging_config import logger

_BASE = settings.SIMULATOR_URL
_TIMEOUT = 5.0


def _get(path: str) -> dict | None:
    """HTTP GET helper; returns None on failure (fail-closed)."""
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.get(f"{_BASE}{path}")
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as exc:
        logger.warning("Simulator %s returned %d: %s", path, exc.response.status_code, exc.response.text[:200])
        return None
    except Exception as exc:
        logger.error("Simulator connection error for %s: %s", path, exc)
        return None


def _verify_ownership(order_data: dict, customer_id: str) -> bool:
    """Return True only if order belongs to customer_id."""
    return order_data.get("customer_id") == customer_id


# --------------------------------------------------------------------------- #
# Public Status Tool Functions                                                  #
# --------------------------------------------------------------------------- #

def get_order_status(order_id: str, customer_id: str) -> dict:
    """Fetch full order record and verify ownership.

    Returns a structured result dict with status or an error.
    """
    data = _get(f"/orders/{order_id}")
    if data is None:
        return {"error": "simulator_unavailable", "message": "Could not reach the simulator."}

    if "detail" in data:
        return {"error": "not_found", "message": f"Order {order_id} not found."}

    if not _verify_ownership(data, customer_id):
        logger.warning("Ownership check failed: customer %s attempted to access %s", customer_id, order_id)
        return {"error": "access_denied", "message": "This order does not belong to your account."}

    return {
        "order_id":        data.get("order_id"),
        "order_status":    data.get("order_status"),
        "payment_status":  data.get("payment_status"),
        "delivery_status": data.get("delivery_status"),
        "product_name":    data.get("product_name"),
        "amount":          data.get("amount"),
        "order_date":      data.get("order_date"),
    }


def get_delivery_status(order_id: str, customer_id: str) -> dict:
    """Fetch delivery and shipment summary for an order."""
    data = _get(f"/orders/{order_id}")
    if data is None:
        return {"error": "simulator_unavailable"}
    if not _verify_ownership(data, customer_id):
        return {"error": "access_denied"}

    return {
        "order_id":           data.get("order_id"),
        "delivery_status":    data.get("delivery_status"),
        "current_location":   data.get("current_location"),
        "carrier":            data.get("carrier"),
        "estimated_delivery": data.get("estimated_delivery"),
        "actual_delivery":    data.get("actual_delivery"),
    }


def get_payment_status(order_id: str, customer_id: str) -> dict:
    """Fetch payment status for an order."""
    data = _get(f"/orders/{order_id}")
    if data is None:
        return {"error": "simulator_unavailable"}
    if not _verify_ownership(data, customer_id):
        return {"error": "access_denied"}

    return {
        "order_id":       data.get("order_id"),
        "payment_status": data.get("payment_status"),
        "amount":         data.get("amount"),
    }


def get_shipment_events(order_id: str, customer_id: str) -> dict:
    """Fetch chronological shipment events for an order."""
    # Verify ownership first
    order_data = _get(f"/orders/{order_id}")
    if order_data is None:
        return {"error": "simulator_unavailable"}
    if not _verify_ownership(order_data, customer_id):
        return {"error": "access_denied"}

    events_data = _get(f"/orders/{order_id}/events")
    if events_data is None:
        return {"error": "simulator_unavailable"}

    return {"order_id": order_id, "events": events_data.get("events", [])}
