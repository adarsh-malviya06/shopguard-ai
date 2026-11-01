"""Unit tests for Groq LLM service & deterministic fallback engine."""

import pytest
from src.shopguard.services.llm_service import (
    generate_response,
    generate_policy_explanation,
    generate_investigation_summary,
    get_groq_stats,
    _deterministic_fallback,
)


def test_deterministic_fallback_when_key_empty(monkeypatch):
    """Ensure system falls back deterministically when GROQ_API_KEY is empty."""
    from src.shopguard.config import settings
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")

    resp, used = generate_policy_explanation(
        query="What is the refund policy?",
        policy_chunks=[{
            "source": "refund_policy.md",
            "content": "Refunds are processed within 30 days of delivery for unused items.",
        }]
    )
    assert used is False
    assert "refund_policy.md" in resp
    assert "30 days" in resp


def test_deterministic_investigation_fallback(monkeypatch):
    from src.shopguard.config import settings
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")

    resp, used = generate_investigation_summary(
        query="Why is my order delayed?",
        investigation_result={
            "order_id": "ORD-1003",
            "issue": "delivery_delay",
            "severity": "medium",
            "findings": ["Package held at Sorting Hub Mumbai due to volume backlog."],
            "recommendation": "escalate_to_support",
            "evidence": [{"source": "simulator:shipment_events", "detail": "Volume backlog reported"}],
        }
    )
    assert used is False
    assert "ORD-1003" in resp
    assert "Sorting Hub Mumbai" in resp
    assert "Escalate To Support" in resp


def test_groq_stats_tracking():
    stats = get_groq_stats()
    assert "calls" in stats
    assert "fallbacks" in stats
    assert "rate_limits_hit" in stats
