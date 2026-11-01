"""Simulator scenario engine — persists scenario overrides to simulator.db."""

import uuid
from datetime import datetime, timezone
from src.shopguard.database.connection import get_simulator_db
from src.shopguard.logging_config import logger

# Allowed override types and their effects
OVERRIDE_TYPES = {
    "HUB_DELAY": "DELAYED_HUB",
    "DAMAGED_ITEM": "DAMAGED_REPORTED",
    "MISSING_PRODUCT": "MISSING_REPORTED",
    "NORMAL_TRANSIT": "IN_TRANSIT",
    "CANCEL_ORDER": "CANCELLED",
}


def inject_scenario(scenario_id: str, order_id: str, override_type: str, parameters: dict) -> dict:
    """Inject a dynamic test scenario into an existing order.

    Adds a synthetic shipment event and updates order/delivery status.
    """
    if override_type not in OVERRIDE_TYPES:
        return {"error": f"Unknown override_type: {override_type}. Allowed: {list(OVERRIDE_TYPES)}"}

    event_type = OVERRIDE_TYPES[override_type]
    hub_location = parameters.get("hub_location", "Test Hub")
    description = parameters.get("description", f"Scenario {scenario_id}: {override_type}")

    with get_simulator_db() as conn:
        # Verify order exists
        row = conn.execute("SELECT order_id, order_status FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        if not row:
            return {"error": f"Order {order_id} not found."}

        # Add a synthetic shipment event
        event_id = f"EVT-INJECT-{uuid.uuid4().hex[:8].upper()}"
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        # Get shipment_id for this order
        shipment = conn.execute("SELECT shipment_id FROM shipments WHERE order_id = ?", (order_id,)).fetchone()
        if not shipment:
            return {"error": f"No shipment record for order {order_id}."}

        conn.execute(
            """INSERT INTO shipment_events (event_id, shipment_id, order_id, timestamp, event_type, location, description)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (event_id, shipment["shipment_id"], order_id, ts, event_type, hub_location, description),
        )

        # Update delivery_status on order
        status_map = {
            "HUB_DELAY": "DELAYED",
            "DAMAGED_ITEM": "DELIVERED",
            "MISSING_PRODUCT": "DELIVERED",
            "NORMAL_TRANSIT": "IN_TRANSIT",
            "CANCEL_ORDER": "PENDING",
        }
        new_delivery_status = status_map[override_type]
        conn.execute(
            "UPDATE orders SET delivery_status = ? WHERE order_id = ?",
            (new_delivery_status, order_id),
        )
        if override_type == "CANCEL_ORDER":
            conn.execute(
                "UPDATE orders SET order_status = ? WHERE order_id = ?",
                ("CANCELLED", order_id),
            )

        logger.info("Scenario %s injected for order %s (type=%s)", scenario_id, order_id, override_type)
        return {"status": "injected", "scenario_id": scenario_id, "order_id": order_id, "event_id": event_id}


def reset_simulator() -> dict:
    """Drop and re-seed the simulator database."""
    from src.shopguard.database.models import init_simulator_db
    init_simulator_db()
    from src.shopguard.database.seed import (
        CUSTOMERS, PRODUCTS, ORDERS, SHIPMENTS, SHIPMENT_EVENTS, REFUNDS
    )

    with get_simulator_db() as conn:
        # Clear tables in dependency order
        for table in ["simulated_refunds", "shipment_events", "shipments", "orders", "products", "customers"]:
            conn.execute(f"DELETE FROM {table}")

    # Re-seed
    _seed_simulator()
    logger.info("Simulator database reset and re-seeded.")
    return {"status": "reset_complete", "timestamp": datetime.now(timezone.utc).isoformat()}


def _seed_simulator() -> None:
    """Internal seed function — idempotent."""
    from src.shopguard.database.seed import (
        CUSTOMERS, PRODUCTS, ORDERS, SHIPMENTS, SHIPMENT_EVENTS, REFUNDS
    )
    with get_simulator_db() as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO customers (customer_id, name, email, phone) VALUES (?,?,?,?)",
            CUSTOMERS,
        )
        conn.executemany(
            """INSERT OR IGNORE INTO products
               (product_id, name, category, price, return_eligible, return_window_days)
               VALUES (?,?,?,?,?,?)""",
            PRODUCTS,
        )
        conn.executemany(
            """INSERT OR IGNORE INTO orders
               (order_id, customer_id, product_id, amount, order_date,
                order_status, payment_status, delivery_status)
               VALUES (?,?,?,?,?,?,?,?)""",
            ORDERS,
        )
        conn.executemany(
            """INSERT OR IGNORE INTO shipments
               (shipment_id, order_id, carrier, tracking_number,
                current_location, estimated_delivery, actual_delivery)
               VALUES (?,?,?,?,?,?,?)""",
            SHIPMENTS,
        )
        conn.executemany(
            """INSERT OR IGNORE INTO shipment_events
               (event_id, shipment_id, order_id, timestamp, event_type, location, description)
               VALUES (?,?,?,?,?,?,?)""",
            SHIPMENT_EVENTS,
        )
        conn.executemany(
            """INSERT OR IGNORE INTO simulated_refunds
               (refund_id, order_id, customer_id, request_date, reason, status, decision_reason)
               VALUES (?,?,?,?,?,?,?)""",
            REFUNDS,
        )
    logger.info("Simulator seeded successfully.")
