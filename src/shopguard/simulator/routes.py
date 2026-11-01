"""Simulator REST API routes (Port 8002)."""

from fastapi import APIRouter, HTTPException, Body
from src.shopguard.database.connection import get_simulator_db
from src.shopguard.simulator.engine import inject_scenario, reset_simulator
from src.shopguard.schemas.requests import ScenarioInjectRequest, OrderCancelRequest, RefundCreateRequest
import uuid
from datetime import datetime, timezone

router = APIRouter()


# --------------------------------------------------------------------------- #
# Customers                                                                     #
# --------------------------------------------------------------------------- #

@router.get("/customers", tags=["Customers"])
def list_customers():
    """Return all simulated customer profiles."""
    with get_simulator_db() as conn:
        rows = conn.execute("SELECT customer_id, name, email FROM customers ORDER BY customer_id").fetchall()
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------- #
# Orders                                                                        #
# --------------------------------------------------------------------------- #

@router.get("/customers/{customer_id}/orders", tags=["Orders"])
def list_customer_orders(customer_id: str):
    """Return all orders belonging to a customer."""
    with get_simulator_db() as conn:
        cust = conn.execute("SELECT customer_id FROM customers WHERE customer_id = ?", (customer_id,)).fetchone()
        if not cust:
            raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found.")
        rows = conn.execute(
            """SELECT o.order_id, o.customer_id, o.product_id, p.name as product_name,
                      o.amount, o.order_date, o.order_status, o.payment_status, o.delivery_status
               FROM orders o JOIN products p ON o.product_id = p.product_id
               WHERE o.customer_id = ? ORDER BY o.order_date DESC""",
            (customer_id,),
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/orders/{order_id}", tags=["Orders"])
def get_order(order_id: str, customer_id: str | None = None):
    """Return order details. Optionally validate ownership."""
    with get_simulator_db() as conn:
        row = conn.execute(
            """SELECT o.order_id, o.customer_id, o.product_id, p.name as product_name,
                      o.amount, o.order_date, o.order_status, o.payment_status, o.delivery_status,
                      s.estimated_delivery, s.actual_delivery, s.current_location, s.carrier
               FROM orders o
               JOIN products p ON o.product_id = p.product_id
               LEFT JOIN shipments s ON s.order_id = o.order_id
               WHERE o.order_id = ?""",
            (order_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found.")
        if customer_id and row["customer_id"] != customer_id:
            raise HTTPException(status_code=403, detail="Access denied: order does not belong to this customer.")
    return dict(row)


@router.get("/orders/{order_id}/events", tags=["Orders"])
def get_order_events(order_id: str, customer_id: str | None = None):
    """Return chronological shipment events for an order."""
    with get_simulator_db() as conn:
        order = conn.execute("SELECT customer_id FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        if not order:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found.")
        if customer_id and order["customer_id"] != customer_id:
            raise HTTPException(status_code=403, detail="Access denied.")
        events = conn.execute(
            """SELECT event_id, timestamp, event_type, location, description
               FROM shipment_events WHERE order_id = ? ORDER BY timestamp ASC""",
            (order_id,),
        ).fetchall()
    return {"order_id": order_id, "events": [dict(e) for e in events]}


# --------------------------------------------------------------------------- #
# Mutations                                                                     #
# --------------------------------------------------------------------------- #

@router.post("/orders/{order_id}/cancel", tags=["Orders"])
def cancel_order(order_id: str, body: OrderCancelRequest):
    """Cancel an order if it is still in PLACED or PROCESSING state."""
    with get_simulator_db() as conn:
        row = conn.execute(
            "SELECT order_id, customer_id, order_status FROM orders WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found.")
        if row["customer_id"] != body.customer_id:
            raise HTTPException(status_code=403, detail="Access denied.")
        if row["order_status"] not in ("PLACED", "PROCESSING"):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel: order is in status '{row['order_status']}'.",
            )
        conn.execute("UPDATE orders SET order_status = 'CANCELLED' WHERE order_id = ?", (order_id,))
    return {
        "success": True,
        "order_id": order_id,
        "previous_status": row["order_status"],
        "new_status": "CANCELLED",
        "message": "Order successfully cancelled.",
    }


@router.post("/refunds/request", status_code=201, tags=["Refunds"])
def create_refund_request(body: RefundCreateRequest):
    """Create a simulated refund review record."""
    with get_simulator_db() as conn:
        order = conn.execute(
            "SELECT customer_id, order_status FROM orders WHERE order_id = ?",
            (body.order_id,),
        ).fetchone()
        if not order:
            raise HTTPException(status_code=404, detail=f"Order {body.order_id} not found.")
        if order["customer_id"] != body.customer_id:
            raise HTTPException(status_code=403, detail="Access denied.")
        # Check for existing open refund
        existing = conn.execute(
            "SELECT refund_id FROM simulated_refunds WHERE order_id = ? AND status = 'PENDING_REVIEW'",
            (body.order_id,),
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"An open refund review case already exists: {existing['refund_id']}.",
            )
        refund_id = f"REF-{uuid.uuid4().hex[:6].upper()}"
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            """INSERT INTO simulated_refunds
               (refund_id, order_id, customer_id, request_date, reason, status)
               VALUES (?, ?, ?, ?, ?, 'PENDING_REVIEW')""",
            (refund_id, body.order_id, body.customer_id, now, body.reason),
        )
    return {
        "refund_request_id": refund_id,
        "order_id": body.order_id,
        "status": "PENDING_REVIEW",
        "message": "Refund review case submitted.",
    }


@router.get("/orders/{order_id}/refunds", tags=["Refunds"])
def get_refunds_for_order(order_id: str):
    """Return all refund records for an order."""
    with get_simulator_db() as conn:
        rows = conn.execute(
            "SELECT * FROM simulated_refunds WHERE order_id = ?", (order_id,)
        ).fetchall()
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------- #
# Admin / Scenario Injection (local demo only)                                  #
# --------------------------------------------------------------------------- #

@router.get("/admin/scenarios", tags=["Admin"])
def list_scenarios():
    """List available scenario override types."""
    from src.shopguard.simulator.engine import OVERRIDE_TYPES
    return {"available_overrides": list(OVERRIDE_TYPES.keys())}


@router.post("/admin/scenarios/inject", tags=["Admin"])
def inject(body: ScenarioInjectRequest):
    """Inject a test scenario into a specific order."""
    result = inject_scenario(body.scenario_id, body.order_id, body.override_type, body.parameters)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/admin/reset", tags=["Admin"])
def reset():
    """Reset simulator database to fresh seed data."""
    return reset_simulator()
