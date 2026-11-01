# ShopGuard AI — REST API Specification

This document provides the complete API contracts for:
1. **E-commerce Simulator API** (`http://localhost:8002`)
2. **ShopGuard Co-Pilot Backend API** (`http://localhost:8010`)

---

## 1. General Principles & Error Standards

All endpoints adhere to JSON payloads, standard HTTP status codes, and unified error responses:

```json
{
  "error": {
    "code": "ORDER_NOT_FOUND",
    "message": "The requested order ORD-9999 does not exist.",
    "details": null,
    "timestamp": "2026-11-01T14:00:00Z"
  }
}
```

Common status codes:
- `200 OK`: Request succeeded.
- `201 Created`: Resource successfully created.
- `400 Bad Request`: Malformed payload or validation error.
- `401 Unauthorized`: Missing or invalid customer/actor context.
- `403 Forbidden`: Cross-customer access or action explicitly denied (`NEVER_PERMITTED`).
- `404 Not Found`: Resource does not exist.
- `429 Too Many Requests`: Rate limit reached; honors `Retry-After`.
- `500 Internal Server Error`: Server error (logged without leaking stack traces).

---

## 2. E-Commerce Simulator API (Port 8002)

### 2.1 Health Check
- **`GET /health`**
- **Response `200 OK`**:
```json
{
  "status": "healthy",
  "service": "ecommerce-simulator",
  "port": 8002,
  "database": "connected"
}
```

---

### 2.2 Customer & Order Queries

#### `GET /customers`
Returns a list of simulated customer identities (for demo switching).
- **Response `200 OK`**:
```json
[
  {
    "customer_id": "CUST-001",
    "name": "Aarav Sharma",
    "email": "aarav.sharma@example.com"
  },
  {
    "customer_id": "CUST-002",
    "name": "Priya Patel",
    "email": "priya.patel@example.com"
  }
]
```

#### `GET /customers/{customer_id}/orders`
Returns all orders associated with a customer.
- **Response `200 OK`**:
```json
[
  {
    "order_id": "ORD-1001",
    "customer_id": "CUST-001",
    "product_id": "PROD-101",
    "product_name": "Wireless Noise-Cancelling Headphones",
    "amount": 2999.00,
    "order_date": "2026-10-25T10:00:00Z",
    "order_status": "DELIVERED",
    "payment_status": "PAID",
    "delivery_status": "DELIVERED"
  }
]
```

#### `GET /orders/{order_id}`
Returns details of a specific order.
- **Query Params**: `customer_id` (optional, for ownership check).
- **Response `200 OK`**:
```json
{
  "order_id": "ORD-1004",
  "customer_id": "CUST-001",
  "product_id": "PROD-205",
  "product_name": "Mechanical Gaming Keyboard",
  "amount": 4499.00,
  "order_date": "2026-10-28T09:30:00Z",
  "order_status": "IN_TRANSIT",
  "payment_status": "PAID",
  "delivery_status": "DELAYED",
  "estimated_delivery": "2026-10-31T18:00:00Z",
  "actual_delivery": null
}
```

#### `GET /orders/{order_id}/events`
Returns chronological shipment and operational events.
- **Response `200 OK`**:
```json
{
  "order_id": "ORD-1004",
  "events": [
    {
      "event_id": "EVT-501",
      "timestamp": "2026-10-28T11:00:00Z",
      "status": "ORDER_PLACED",
      "location": "Warehouse Mumbai",
      "description": "Order received and packed."
    },
    {
      "event_id": "EVT-502",
      "timestamp": "2026-10-29T14:30:00Z",
      "status": "DISPATCHED",
      "location": "Central Distribution Hub",
      "description": "Package handed over to courier."
    },
    {
      "event_id": "EVT-503",
      "timestamp": "2026-10-30T08:15:00Z",
      "status": "DELAYED_HUB",
      "location": "Regional Sorting Hub Pune",
      "description": "Shipment delayed due to sorting equipment maintenance."
    }
  ]
}
```

---

### 2.3 Simulated Mutations

#### `POST /orders/{order_id}/cancel`
Cancels an order if eligible (status `PLACED` or `PROCESSING`).
- **Request Body**:
```json
{
  "customer_id": "CUST-001",
  "reason": "Customer requested pre-dispatch cancellation."
}
```
- **Response `200 OK`**:
```json
{
  "success": true,
  "order_id": "ORD-1005",
  "previous_status": "PROCESSING",
  "new_status": "CANCELLED",
  "message": "Order successfully cancelled."
}
```

#### `POST /refunds/request`
Creates a simulated refund review record.
- **Request Body**:
```json
{
  "customer_id": "CUST-001",
  "order_id": "ORD-1004",
  "reason": "Damaged goods upon arrival",
  "evidence_notes": "Customer reported package seal was torn."
}
```
- **Response `201 Created`**:
```json
{
  "refund_request_id": "REF-801",
  "order_id": "ORD-1004",
  "status": "PENDING_REVIEW",
  "created_at": "2026-11-01T14:15:00Z",
  "message": "Refund review case submitted for human operations review."
}
```

---

### 2.4 Admin Scenario Injection (Port 8002)

#### `POST /admin/scenarios/inject`
Injects dynamic scenario conditions for golden tests.
- **Request Body**:
```json
{
  "scenario_id": "SG-01",
  "order_id": "ORD-1004",
  "override_type": "HUB_DELAY",
  "parameters": {
    "hub_location": "Regional Sorting Hub Pune",
    "days_delayed": 3,
    "damaged_flag": false
  }
}
```
- **Response `200 OK`**:
```json
{
  "status": "injected",
  "scenario_id": "SG-01",
  "order_id": "ORD-1004"
}
```

#### `POST /admin/reset`
Resets the simulator database back to fresh synthetic seed data.
- **Response `200 OK`**:
```json
{
  "status": "reset_complete",
  "timestamp": "2026-11-01T14:20:00Z"
}
```

---

## 3. ShopGuard Co-Pilot Backend API (Port 8010)

### 3.1 Health & Telemetry

#### `GET /health`
- **Response `200 OK`**:
```json
{
  "status": "healthy",
  "service": "shopguard-backend",
  "port": 8010,
  "groq_status": "connected",
  "chromadb_status": "ready",
  "simulator_status": "reachable"
}
```

#### `GET /api/diagnostics`
Telemetry on cache, rate limiter, and LangGraph runs.
- **Response `200 OK`**:
```json
{
  "cache_stats": {
    "hits": 14,
    "misses": 38,
    "entries": 12,
    "hit_ratio": 0.269
  },
  "groq_stats": {
    "total_calls": 22,
    "fallback_invocations": 1,
    "rate_limit_hits": 0,
    "estimated_tokens_used": 6840
  },
  "router_distribution": {
    "knowledge": 25,
    "status": 18,
    "investigation": 14,
    "action": 9,
    "ambiguous": 2
  }
}
```

---

### 3.2 Main Chat & Orchestration

#### `POST /api/chat`
The primary endpoint invoked by the Streamlit frontend.
- **Request Body**:
```json
{
  "customer_id": "CUST-001",
  "message": "Why is my order ORD-1004 delayed?",
  "session_id": "sess-abc123xyz"
}
```
- **Response `200 OK`**:
```json
{
  "request_id": "REQ-77891",
  "session_id": "sess-abc123xyz",
  "category": "investigation",
  "router_metadata": {
    "rule_matched": "investigation_why_delay",
    "target_tool": "investigation_tool",
    "confidence": 0.95
  },
  "response": "Your order ORD-1004 is currently delayed at the Regional Sorting Hub Pune due to unexpected sorting equipment maintenance. The estimated delivery date was 2026-10-31, which is now overdue. We have logged this case and escalated it to our support team.",
  "evidence": [
    {
      "source": "simulator:shipment_events",
      "detail": "EVT-503: Delayed at Regional Sorting Hub Pune on 2026-10-30"
    },
    {
      "source": "policy:shipping_policy.md#delay-thresholds",
      "detail": "Delays exceeding 48 hours past estimated delivery require support escalation."
    }
  ],
  "investigation_result": {
    "investigation_id": "INV-1001",
    "order_id": "ORD-1004",
    "issue": "delivery_delay",
    "severity": "medium",
    "requires_human": true
  },
  "pending_action": null,
  "llm_used": true,
  "trace_id": "TRC-9921"
}
```

---

### 3.3 Action Confirmation & Execution

#### `POST /api/actions/confirm`
Executes a previously authorized `CONFIRMATION_REQUIRED` action using a valid confirmation token.
- **Request Body**:
```json
{
  "confirmation_token": "ACT-CONF-98218-XYZ",
  "customer_id": "CUST-001",
  "order_id": "ORD-1005",
  "confirmed": true
}
```
- **Response `200 OK`**:
```json
{
  "success": true,
  "action": "cancel_order",
  "order_id": "ORD-1005",
  "result_summary": "Order ORD-1005 has been successfully cancelled in the simulator.",
  "audit_event_id": "AUD-5521"
}
```
- **Response `403 Forbidden` (Token Expired or Invalid)**:
```json
{
  "error": {
    "code": "INVALID_CONFIRMATION_TOKEN",
    "message": "Confirmation token is invalid or has expired (TTL 5 minutes).",
    "details": null
  }
}
```

---

### 3.4 Audit Trail & Case Review

#### `GET /api/cases`
Returns investigation and refund-review cases for the Operator Dashboard.
- **Query Params**: `status` (e.g. `PENDING_REVIEW`, `RESOLVED`).
- **Response `200 OK`**:
```json
[
  {
    "case_id": "CASE-101",
    "order_id": "ORD-1004",
    "customer_id": "CUST-001",
    "case_type": "DELAYED_SHIPMENT_ESCALATION",
    "severity": "medium",
    "status": "OPEN",
    "created_at": "2026-11-01T14:15:00Z"
  }
]
```

#### `GET /api/audit`
Returns paginated, append-only operational audit records.
- **Query Params**: `limit=50`, `offset=0`.
- **Response `200 OK`**:
```json
[
  {
    "event_id": "AUD-5521",
    "request_id": "REQ-77891",
    "timestamp": "2026-11-01T14:15:02Z",
    "actor": "CUST-001",
    "operation": "INVESTIGATE_ORDER",
    "resource_id": "ORD-1004",
    "decision": "AUTO_ALLOWED",
    "status": "SUCCESS",
    "details": "Investigated delayed delivery: hub equipment failure detected."
  }
]
```
