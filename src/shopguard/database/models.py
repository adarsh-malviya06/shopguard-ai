"""SQLite DDL for simulator.db and shopguard.db.

All tables use parameterized queries throughout the codebase.
Foreign keys are enforced at connection level.
"""

SIMULATOR_DDL = """
-- Enable FK enforcement (done at connection level, listed here for clarity)

CREATE TABLE IF NOT EXISTS customers (
    customer_id   TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    phone         TEXT,
    created_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS products (
    product_id          TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    category            TEXT NOT NULL,
    price               REAL NOT NULL CHECK(price >= 0),
    return_eligible     INTEGER NOT NULL DEFAULT 1 CHECK(return_eligible IN (0,1)),
    return_window_days  INTEGER NOT NULL DEFAULT 30
);

CREATE TABLE IF NOT EXISTS orders (
    order_id        TEXT PRIMARY KEY,
    customer_id     TEXT NOT NULL REFERENCES customers(customer_id),
    product_id      TEXT NOT NULL REFERENCES products(product_id),
    amount          REAL NOT NULL CHECK(amount >= 0),
    order_date      TEXT NOT NULL DEFAULT (datetime('now')),
    order_status    TEXT NOT NULL CHECK(order_status IN
                        ('PLACED','PROCESSING','SHIPPED','DELIVERED','CANCELLED')),
    payment_status  TEXT NOT NULL CHECK(payment_status IN
                        ('PENDING','PAID','FAILED','REFUNDED')),
    delivery_status TEXT NOT NULL CHECK(delivery_status IN
                        ('PENDING','IN_TRANSIT','OUT_FOR_DELIVERY',
                         'DELIVERED','DELAYED','RETURNED'))
);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);

CREATE TABLE IF NOT EXISTS shipments (
    shipment_id         TEXT PRIMARY KEY,
    order_id            TEXT NOT NULL UNIQUE REFERENCES orders(order_id),
    carrier             TEXT NOT NULL,
    tracking_number     TEXT NOT NULL UNIQUE,
    current_location    TEXT NOT NULL,
    estimated_delivery  TEXT NOT NULL,
    actual_delivery     TEXT
);

CREATE TABLE IF NOT EXISTS shipment_events (
    event_id     TEXT PRIMARY KEY,
    shipment_id  TEXT NOT NULL REFERENCES shipments(shipment_id),
    order_id     TEXT NOT NULL REFERENCES orders(order_id),
    timestamp    TEXT NOT NULL DEFAULT (datetime('now')),
    event_type   TEXT NOT NULL,
    location     TEXT NOT NULL,
    description  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_order_time ON shipment_events(order_id, timestamp);

CREATE TABLE IF NOT EXISTS simulated_refunds (
    refund_id       TEXT PRIMARY KEY,
    order_id        TEXT NOT NULL REFERENCES orders(order_id),
    customer_id     TEXT NOT NULL REFERENCES customers(customer_id),
    request_date    TEXT NOT NULL DEFAULT (datetime('now')),
    reason          TEXT NOT NULL,
    status          TEXT NOT NULL CHECK(status IN
                        ('PENDING_REVIEW','APPROVED_SIMULATED','REJECTED_SIMULATED')),
    decision_reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_refunds_order ON simulated_refunds(order_id);
"""

SHOPGUARD_DDL = """
CREATE TABLE IF NOT EXISTS conversation_sessions (
    session_id      TEXT PRIMARY KEY,
    customer_id     TEXT NOT NULL,
    started_at      TEXT DEFAULT (datetime('now')),
    last_active_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS investigation_cases (
    case_id          TEXT PRIMARY KEY,
    order_id         TEXT NOT NULL,
    customer_id      TEXT NOT NULL,
    issue_type       TEXT NOT NULL,
    severity         TEXT NOT NULL CHECK(severity IN ('low','medium','high','critical')),
    findings_json    TEXT NOT NULL,
    recommendation   TEXT NOT NULL,
    requires_human   INTEGER NOT NULL DEFAULT 0 CHECK(requires_human IN (0,1)),
    status           TEXT NOT NULL DEFAULT 'OPEN'
                         CHECK(status IN ('OPEN','IN_REVIEW','RESOLVED','DISMISSED')),
    created_at       TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_cases_order ON investigation_cases(order_id);

CREATE TABLE IF NOT EXISTS action_confirmations (
    token        TEXT PRIMARY KEY,
    customer_id  TEXT NOT NULL,
    order_id     TEXT NOT NULL,
    action_name  TEXT NOT NULL,
    payload_json TEXT,
    created_at   TEXT DEFAULT (datetime('now')),
    expires_at   TEXT NOT NULL,
    consumed     INTEGER NOT NULL DEFAULT 0 CHECK(consumed IN (0,1))
);
CREATE INDEX IF NOT EXISTS idx_token_expiry ON action_confirmations(expires_at, consumed);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id     TEXT PRIMARY KEY,
    request_id   TEXT NOT NULL,
    timestamp    TEXT DEFAULT (datetime('now')),
    actor        TEXT NOT NULL,
    operation    TEXT NOT NULL,
    resource_id  TEXT,
    decision     TEXT NOT NULL CHECK(decision IN
                     ('AUTO_ALLOWED','CONFIRMATION_REQUIRED',
                      'NEVER_PERMITTED','INFO_ONLY')),
    status       TEXT NOT NULL CHECK(status IN
                     ('SUCCESS','DENIED','FAILED','ESCALATED')),
    details_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_events(timestamp);

CREATE TABLE IF NOT EXISTS metrics_daily (
    date                TEXT PRIMARY KEY,
    total_requests      INTEGER DEFAULT 0,
    knowledge_count     INTEGER DEFAULT 0,
    status_count        INTEGER DEFAULT 0,
    investigation_count INTEGER DEFAULT 0,
    action_count        INTEGER DEFAULT 0,
    groq_calls          INTEGER DEFAULT 0,
    groq_fallbacks      INTEGER DEFAULT 0
);
"""


def init_simulator_db() -> None:
    """Create all simulator tables if they don't exist."""
    from src.shopguard.database.connection import get_simulator_db
    with get_simulator_db() as conn:
        conn.executescript(SIMULATOR_DDL)
    print("[DB] simulator.db initialised.")


def init_shopguard_db() -> None:
    """Create all shopguard tables if they don't exist."""
    from src.shopguard.database.connection import get_shopguard_db
    with get_shopguard_db() as conn:
        conn.executescript(SHOPGUARD_DDL)
    print("[DB] shopguard.db initialised.")


def init_all() -> None:
    """Initialise both databases."""
    init_simulator_db()
    init_shopguard_db()
