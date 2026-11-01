"""Tests for E-Commerce Simulator (Port 8002 endpoints & engine)."""

import pytest
from fastapi.testclient import TestClient
from src.shopguard.simulator.main import app
from src.shopguard.simulator.engine import reset_simulator

client = TestClient(app)


@pytest.fixture(autouse=True)
def run_around_tests():
    reset_simulator()
    yield


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_list_customers():
    res = client.get("/customers")
    assert res.status_code == 200
    customers = res.json()
    assert len(customers) >= 5
    ids = [c["customer_id"] for c in customers]
    assert "CUST-001" in ids


def test_get_customer_orders():
    res = client.get("/customers/CUST-001/orders")
    assert res.status_code == 200
    orders = res.json()
    assert len(orders) >= 2


def test_get_order_with_ownership():
    # Correct owner
    res = client.get("/orders/ORD-1001?customer_id=CUST-001")
    assert res.status_code == 200
    assert res.json()["order_id"] == "ORD-1001"

    # Cross-customer access attempt (Customer B trying to get Customer A's order)
    res_forbidden = client.get("/orders/ORD-1001?customer_id=CUST-002")
    assert res_forbidden.status_code == 403


def test_order_events():
    res = client.get("/orders/ORD-1001/events?customer_id=CUST-001")
    assert res.status_code == 200
    data = res.json()
    assert data["order_id"] == "ORD-1001"
    assert len(data["events"]) >= 4


def test_order_cancel_mutation():
    # ORD-1007 is CANCELLED already; let's check ORD-1002 (SHIPPED - cannot cancel)
    res = client.post("/orders/ORD-1002/cancel", json={
        "customer_id": "CUST-001",
        "reason": "Changed my mind"
    })
    assert res.status_code == 400

    # Test reset and scenario injection
    inject_res = client.post("/admin/scenarios/inject", json={
        "scenario_id": "TEST-01",
        "order_id": "ORD-1003",
        "override_type": "HUB_DELAY",
        "parameters": {"hub_location": "Custom Hub"}
    })
    assert inject_res.status_code == 200
    assert inject_res.json()["status"] == "injected"
