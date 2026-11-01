"""Synthetic seed data for the E-commerce Simulator.

Covers all 10 required order scenarios.
"""

from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Reference datetime: "today" for the seed script
# ---------------------------------------------------------------------------
NOW = datetime.now(timezone.utc)


def _dt(days_offset: int, hours_offset: int = 0) -> str:
    """Return UTC ISO timestamp offset from NOW."""
    return (NOW + timedelta(days=days_offset, hours=hours_offset)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------
CUSTOMERS = [
    ("CUST-001", "Aarav Sharma",   "aarav.sharma@example.com",   "+91-9001001001"),
    ("CUST-002", "Priya Patel",    "priya.patel@example.com",    "+91-9002002002"),
    ("CUST-003", "Rahul Mehta",    "rahul.mehta@example.com",    "+91-9003003003"),
    ("CUST-004", "Sneha Iyer",     "sneha.iyer@example.com",     "+91-9004004004"),
    ("CUST-005", "Vikram Nair",    "vikram.nair@example.com",    "+91-9005005005"),
]

# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------
PRODUCTS = [
    ("PROD-101", "Wireless Noise-Cancelling Headphones", "Electronics",   2999.00, 1, 30),
    ("PROD-102", "Mechanical Gaming Keyboard",           "Electronics",   4499.00, 1, 30),
    ("PROD-103", "Running Shoes (Size 10)",              "Footwear",       1899.00, 1, 15),
    ("PROD-104", "Cotton Casual Shirt",                  "Clothing",        899.00, 1, 15),
    ("PROD-105", "Stainless Steel Water Bottle",         "Kitchen",         699.00, 1, 30),
    ("PROD-106", "Novel: The Midnight Library",          "Books",           299.00, 0,  0),
    ("PROD-107", "Smart LED Desk Lamp",                  "Electronics",    1499.00, 1, 30),
    ("PROD-108", "Yoga Mat (6mm)",                       "Sports",          799.00, 1, 15),
    ("PROD-109", "Premium Coffee Maker",                 "Kitchen",        3499.00, 1, 30),
    ("PROD-110", "Leather Laptop Bag",                   "Accessories",    2199.00, 1, 30),
]

# ---------------------------------------------------------------------------
# Orders — 10 scenarios
# ---------------------------------------------------------------------------
# Scenario 1: Normal delivered order (CUST-001, within refund window)
# Scenario 2: Order currently in transit (CUST-001)
# Scenario 3: Delayed shipment — ETA passed (CUST-002)
# Scenario 4: Shipment stuck at distribution hub (CUST-002)
# Scenario 5: Damaged package (CUST-003)
# Scenario 6: Missing product — delivered but item absent (CUST-003)
# Scenario 7: Cancelled order (CUST-004)
# Scenario 8: Refund already under processing (CUST-004)
# Scenario 9: Duplicate refund request order (CUST-005)
# Scenario 10: Order outside refund window (CUST-005)

ORDERS = [
    # (order_id, customer_id, product_id, amount, order_date, order_status, payment_status, delivery_status)
    ("ORD-1001", "CUST-001", "PROD-101", 2999.00, _dt(-15), "DELIVERED",   "PAID",   "DELIVERED"),   # Scenario 1
    ("ORD-1002", "CUST-001", "PROD-103", 1899.00, _dt(-3),  "SHIPPED",     "PAID",   "IN_TRANSIT"),   # Scenario 2
    ("ORD-1003", "CUST-002", "PROD-102", 4499.00, _dt(-10), "SHIPPED",     "PAID",   "DELAYED"),      # Scenario 3
    ("ORD-1004", "CUST-002", "PROD-107", 1499.00, _dt(-8),  "SHIPPED",     "PAID",   "DELAYED"),      # Scenario 4
    ("ORD-1005", "CUST-003", "PROD-105", 699.00,  _dt(-12), "DELIVERED",   "PAID",   "DELIVERED"),   # Scenario 5
    ("ORD-1006", "CUST-003", "PROD-109", 3499.00, _dt(-9),  "DELIVERED",   "PAID",   "DELIVERED"),   # Scenario 6
    ("ORD-1007", "CUST-004", "PROD-104", 899.00,  _dt(-1),  "CANCELLED",   "PAID",   "PENDING"),      # Scenario 7
    ("ORD-1008", "CUST-004", "PROD-108", 799.00,  _dt(-20), "DELIVERED",   "PAID",   "DELIVERED"),   # Scenario 8
    ("ORD-1009", "CUST-005", "PROD-110", 2199.00, _dt(-18), "DELIVERED",   "PAID",   "DELIVERED"),   # Scenario 9
    ("ORD-1010", "CUST-005", "PROD-106", 299.00,  _dt(-65), "DELIVERED",   "PAID",   "DELIVERED"),   # Scenario 10
]

# ---------------------------------------------------------------------------
# Shipments
# ---------------------------------------------------------------------------
SHIPMENTS = [
    # (shipment_id, order_id, carrier, tracking_number, current_location, estimated_delivery, actual_delivery)
    ("SHP-001", "ORD-1001", "BlueDart",   "BD10010001", "Delivered to customer", _dt(-10), _dt(-12)),
    ("SHP-002", "ORD-1002", "DTDC",       "DT10020002", "Regional Hub Bangalore", _dt(1),  None),
    ("SHP-003", "ORD-1003", "Delhivery",  "DL10030003", "Sorting Hub Mumbai",     _dt(-3),  None),   # ETA passed
    ("SHP-004", "ORD-1004", "Xpressbees", "XB10040004", "Distribution Hub Pune",  _dt(-2),  None),   # ETA passed
    ("SHP-005", "ORD-1005", "BlueDart",   "BD10050005", "Delivered to customer",  _dt(-8),  _dt(-9)),
    ("SHP-006", "ORD-1006", "DTDC",       "DT10060006", "Delivered to customer",  _dt(-5),  _dt(-6)),
    # ORD-1007 cancelled — no shipment
    ("SHP-007", "ORD-1008", "BlueDart",   "BD10080008", "Delivered to customer",  _dt(-14), _dt(-15)),
    ("SHP-008", "ORD-1009", "Delhivery",  "DL10090009", "Delivered to customer",  _dt(-12), _dt(-13)),
    ("SHP-009", "ORD-1010", "DTDC",       "DT10100010", "Delivered to customer",  _dt(-59), _dt(-60)),
]

# ---------------------------------------------------------------------------
# Shipment Events
# ---------------------------------------------------------------------------
SHIPMENT_EVENTS = [
    # ORD-1001 — Normal delivered
    ("EVT-1001-01", "SHP-001", "ORD-1001", _dt(-15, 10), "ORDER_PLACED",     "Warehouse Mumbai",               "Order packed and ready to dispatch."),
    ("EVT-1001-02", "SHP-001", "ORD-1001", _dt(-14, 8),  "DISPATCHED",       "Central Hub Mumbai",             "Shipped via BlueDart."),
    ("EVT-1001-03", "SHP-001", "ORD-1001", _dt(-13),     "IN_TRANSIT",       "Sorting Hub Pune",               "Package arrived at sorting hub."),
    ("EVT-1001-04", "SHP-001", "ORD-1001", _dt(-12, 10), "DELIVERED",        "Customer Doorstep",              "Package delivered successfully."),

    # ORD-1002 — In transit
    ("EVT-1002-01", "SHP-002", "ORD-1002", _dt(-3, 9),   "ORDER_PLACED",     "Warehouse Delhi",                "Order packed and dispatched."),
    ("EVT-1002-02", "SHP-002", "ORD-1002", _dt(-2, 14),  "IN_TRANSIT",       "Sorting Hub Hyderabad",          "Package in transit to Bangalore."),
    ("EVT-1002-03", "SHP-002", "ORD-1002", _dt(-1, 8),   "IN_TRANSIT",       "Regional Hub Bangalore",         "Package arrived at regional hub."),

    # ORD-1003 — Delayed: ETA passed, last event 5 days ago
    ("EVT-1003-01", "SHP-003", "ORD-1003", _dt(-10, 9),  "ORDER_PLACED",     "Warehouse Chennai",              "Order packed."),
    ("EVT-1003-02", "SHP-003", "ORD-1003", _dt(-9, 12),  "DISPATCHED",       "Hub Chennai",                    "Shipped via Delhivery."),
    ("EVT-1003-03", "SHP-003", "ORD-1003", _dt(-5, 7),   "DELAYED",          "Sorting Hub Mumbai",             "Delayed: high volume backlog at hub."),

    # ORD-1004 — Stuck at hub: no movement for 6 days
    ("EVT-1004-01", "SHP-004", "ORD-1004", _dt(-8, 10),  "ORDER_PLACED",     "Warehouse Kolkata",              "Order packed."),
    ("EVT-1004-02", "SHP-004", "ORD-1004", _dt(-7, 8),   "DISPATCHED",       "Hub Kolkata",                    "Shipped via Xpressbees."),
    ("EVT-1004-03", "SHP-004", "ORD-1004", _dt(-6, 15),  "DELAYED_HUB",      "Distribution Hub Pune",          "Package stalled — equipment maintenance at hub."),

    # ORD-1005 — Damaged package
    ("EVT-1005-01", "SHP-005", "ORD-1005", _dt(-12, 9),  "ORDER_PLACED",     "Warehouse Bangalore",            "Order packed."),
    ("EVT-1005-02", "SHP-005", "ORD-1005", _dt(-11, 7),  "DISPATCHED",       "Hub Bangalore",                  "Shipped via BlueDart."),
    ("EVT-1005-03", "SHP-005", "ORD-1005", _dt(-9, 14),  "DAMAGED_REPORTED", "Sorting Hub Ahmedabad",          "Package exterior damage reported at sorting hub."),
    ("EVT-1005-04", "SHP-005", "ORD-1005", _dt(-9, 17),  "DELIVERED",        "Customer Doorstep",              "Package delivered with noted exterior damage."),

    # ORD-1006 — Missing product (delivered but item absent)
    ("EVT-1006-01", "SHP-006", "ORD-1006", _dt(-9, 9),   "ORDER_PLACED",     "Warehouse Mumbai",               "Order packed."),
    ("EVT-1006-02", "SHP-006", "ORD-1006", _dt(-8, 8),   "DISPATCHED",       "Hub Mumbai",                     "Shipped."),
    ("EVT-1006-03", "SHP-006", "ORD-1006", _dt(-6, 12),  "DELIVERED",        "Customer Doorstep",              "Delivered. Customer later reported item missing from box."),

    # ORD-1008 — Refund under processing (was delivered 20 days ago)
    ("EVT-1008-01", "SHP-007", "ORD-1008", _dt(-20, 9),  "ORDER_PLACED",     "Warehouse Pune",                 "Order packed."),
    ("EVT-1008-02", "SHP-007", "ORD-1008", _dt(-19, 8),  "DISPATCHED",       "Hub Pune",                       "Shipped via BlueDart."),
    ("EVT-1008-03", "SHP-007", "ORD-1008", _dt(-15, 11), "DELIVERED",        "Customer Doorstep",              "Package delivered."),

    # ORD-1009 — Duplicate refund scenario
    ("EVT-1009-01", "SHP-008", "ORD-1009", _dt(-18, 9),  "ORDER_PLACED",     "Warehouse Hyderabad",            "Order packed."),
    ("EVT-1009-02", "SHP-008", "ORD-1009", _dt(-17, 8),  "DISPATCHED",       "Hub Hyderabad",                  "Shipped via Delhivery."),
    ("EVT-1009-03", "SHP-008", "ORD-1009", _dt(-13, 14), "DELIVERED",        "Customer Doorstep",              "Package delivered."),

    # ORD-1010 — Outside refund window (65 days ago)
    ("EVT-1010-01", "SHP-009", "ORD-1010", _dt(-65, 9),  "ORDER_PLACED",     "Warehouse Chennai",              "Order packed."),
    ("EVT-1010-02", "SHP-009", "ORD-1010", _dt(-64, 8),  "DISPATCHED",       "Hub Chennai",                    "Shipped via DTDC."),
    ("EVT-1010-03", "SHP-009", "ORD-1010", _dt(-60, 12), "DELIVERED",        "Customer Doorstep",              "Package delivered."),
]

# ---------------------------------------------------------------------------
# Simulated Refunds
# ---------------------------------------------------------------------------
REFUNDS = [
    # Scenario 8: Refund under processing for ORD-1008
    ("REF-001", "ORD-1008", "CUST-004", _dt(-5), "Defective product received",
     "PENDING_REVIEW", None),

    # Scenario 9: Duplicate refund — an open case already exists for ORD-1009
    ("REF-002", "ORD-1009", "CUST-005", _dt(-7), "Wrong item delivered",
     "PENDING_REVIEW", None),
]
