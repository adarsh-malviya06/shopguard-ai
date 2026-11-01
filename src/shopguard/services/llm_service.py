"""Groq LLM Service — grounded explanation generation.

Enforces zero-trust boundary:
- Groq ONLY generates natural language explanations from verified facts.
- Groq NEVER routes requests, authorizes actions, or changes database records.
- Deterministic fallback templates activate immediately on 429, timeout, or missing key.
- Strict Free-Tier compliance with bounded retries and token ceilings.
"""

from __future__ import annotations
import os
import time
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from src.shopguard.config import settings
from src.shopguard.logging_config import logger

# Diagnostic telemetry counters
_stats = {
    "calls": 0,
    "fallbacks": 0,
    "rate_limits_hit": 0,
    "errors": 0,
    "last_error": None,
}


def get_groq_stats() -> dict:
    """Return live Groq API usage telemetry."""
    return dict(_stats)


# --------------------------------------------------------------------------- #
# Pydantic Output Schemas for Structured LLM Responses                         #
# --------------------------------------------------------------------------- #

class GroundedExplanation(BaseModel):
    summary: str = Field(..., description="Customer-friendly concise explanation")
    key_points: List[str] = Field(default_factory=list, description="Bullet points of verified facts")
    recommended_next_step: Optional[str] = Field(None, description="Suggested next action or contact support")


# --------------------------------------------------------------------------- #
# Core Generation Engine with Bounded Retries & 429 Backoff                    #
# --------------------------------------------------------------------------- #

def generate_response(
    system_prompt: str,
    user_prompt: str,
    context: dict,
    max_retries: int = 2,
) -> tuple[str, bool]:
    """Generate grounded text using Groq SDK with deterministic fallback.

    Returns:
        (response_text, llm_used_boolean)
    """
    api_key = settings.GROQ_API_KEY.strip()
    if not api_key or api_key == "gsk_your_groq_api_key_here":
        _stats["fallbacks"] += 1
        logger.info("GROQ_API_KEY absent or dummy — using deterministic fallback.")
        return _deterministic_fallback(context), False

    for attempt in range(1, max_retries + 1):
        try:
            from groq import Groq, RateLimitError, APIConnectionError, APITimeoutError, AuthenticationError

            client = Groq(api_key=api_key)
            _stats["calls"] += 1

            completion = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=settings.GROQ_TEMPERATURE,
                max_tokens=settings.GROQ_MAX_TOKENS,
                timeout=8.0,
            )

            text = completion.choices[0].message.content.strip()
            logger.info("Groq API successfully generated explanation (model: %s).", settings.GROQ_MODEL)
            return text, True

        except RateLimitError as exc:
            _stats["rate_limits_hit"] += 1
            _stats["errors"] += 1
            _stats["last_error"] = "HTTP 429 Rate Limit Exceeded"
            logger.warning("Groq RateLimitError (attempt %d/%d): %s", attempt, max_retries, exc)
            retry_after = 2 ** attempt
            if hasattr(exc, "response") and exc.response is not None:
                retry_header = exc.response.headers.get("Retry-After")
                if retry_header and retry_header.isdigit():
                    retry_after = min(int(retry_header), 5)
            time.sleep(retry_after)

        except AuthenticationError as exc:
            _stats["errors"] += 1
            _stats["last_error"] = "Authentication Failed (Invalid Key)"
            logger.error("Groq AuthenticationError: %s. Falling back to deterministic engine.", exc)
            break

        except (APIConnectionError, APITimeoutError) as exc:
            _stats["errors"] += 1
            _stats["last_error"] = f"Connection/Timeout Error: {type(exc).__name__}"
            logger.warning("Groq transient error (attempt %d/%d): %s", attempt, max_retries, exc)
            time.sleep(1.0 * attempt)

        except Exception as exc:
            _stats["errors"] += 1
            _stats["last_error"] = str(exc)
            logger.error("Unexpected Groq API error: %s", exc)
            break

    _stats["fallbacks"] += 1
    logger.warning("Groq unavailable — deterministic fallback engine activated.")
    return _deterministic_fallback(context), False


# --------------------------------------------------------------------------- #
# Specialized Generator Wrappers (PRD Requirement)                            #
# --------------------------------------------------------------------------- #

POLICY_SYSTEM_PROMPT = (
    "You are ShopGuard AI's customer policy guide. "
    "Your objective is to answer customer questions accurately using ONLY the provided verified policy chunks. "
    "Do NOT fabricate time windows, fees, or exceptions. "
    "If the evidence does not state the answer, state that you do not have that specific policy and recommend contacting support. "
    "Keep answers under 4 sentences, polite, and professional."
)

INVESTIGATION_SYSTEM_PROMPT = (
    "You are ShopGuard AI's incident investigator explainer. "
    "Explain the findings and shipment timeline to the customer in empathetic, clear language. "
    "Rely STRICTLY on the verified facts, shipment events, and severity rating provided. "
    "Never guarantee a financial refund or change order records. "
    "Present a clear next step."
)


def generate_policy_explanation(query: str, policy_chunks: list[dict]) -> tuple[str, bool]:
    """Generate grounded policy explanation from ChromaDB chunks."""
    if not policy_chunks:
        return _deterministic_fallback({"category": "knowledge", "policy_chunks": []}), False

    context_lines = []
    for c in policy_chunks:
        context_lines.append(f"Document [{c.get('source')}]:\n{c.get('content')}")
    context_text = "\n\n".join(context_lines)

    user_prompt = (
        f"Customer Question: {query}\n\n"
        f"Verified Policy Documentation:\n{context_text}\n\n"
        "Provide a grounded, professional response based solely on the above documentation."
    )

    return generate_response(
        system_prompt=POLICY_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        context={"category": "knowledge", "policy_chunks": policy_chunks},
    )


def generate_investigation_summary(query: str, investigation_result: dict) -> tuple[str, bool]:
    """Generate grounded customer-friendly investigation summary from verified findings."""
    findings = investigation_result.get("findings", [])
    evidence = investigation_result.get("evidence", [])
    rec = investigation_result.get("recommendation", "escalate_to_support")

    findings_text = "\n".join(f"- {f}" for f in findings)
    evidence_text = "\n".join(f"- [{e.get('source')}] {e.get('detail')}" for e in evidence)

    user_prompt = (
        f"Customer Question: {query}\n\n"
        f"Order ID: {investigation_result.get('order_id')}\n"
        f"Issue Type: {investigation_result.get('issue')}\n"
        f"Severity: {investigation_result.get('severity')}\n"
        f"Verified Findings:\n{findings_text}\n\n"
        f"Shipment Evidence:\n{evidence_text}\n\n"
        f"Recommended Action: {rec}\n\n"
        "Summarize this issue clearly for the customer."
    )

    return generate_response(
        system_prompt=INVESTIGATION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        context={"category": "investigation", "investigation_result": investigation_result},
    )


# Backward compatibility aliases
explain_policy = generate_policy_explanation
explain_investigation = generate_investigation_summary


# --------------------------------------------------------------------------- #
# Deterministic Fallback Template Engine                                        #
# --------------------------------------------------------------------------- #

def _deterministic_fallback(context: dict) -> str:
    """Zero-dependency deterministic templates for when Groq is unavailable."""
    category = context.get("category", "unknown")

    if category == "knowledge":
        chunks = context.get("policy_chunks", [])
        if not chunks:
            return (
                "I am unable to locate the specific policy details in our documentation. "
                "Please reach out directly to customer support for confirmation."
            )
        sources = sorted(list({c.get("source", "knowledge_base") for c in chunks}))
        lead = chunks[0].get("content", "").strip()[:350]
        return (
            f"According to our verified policy records ({', '.join(sources)}):\n\n"
            f"> {lead}...\n\n"
            "If you need further clarification, our support team is available to assist."
        )

    if category == "status":
        order = context.get("order_data", {})
        if not order or "error" in order:
            return "Unable to retrieve order details. Please verify your order ID or try again shortly."
        return (
            f"**Order {order.get('order_id')}** is currently **{order.get('order_status')}**.\n"
            f"• Delivery Status: {order.get('delivery_status')}\n"
            f"• Payment Status: {order.get('payment_status')}\n"
            f"• Ordered Date: {order.get('order_date')}"
        )

    if category == "investigation":
        res = context.get("investigation_result", {})
        findings = res.get("findings", ["Investigation initiated."])
        rec = res.get("recommendation", "escalate_to_support").replace("_", " ").title()
        bullet_list = "\n".join(f"• {f}" for f in findings)
        return (
            f"**Investigation Update for Order {res.get('order_id', 'N/A')}:**\n\n"
            f"{bullet_list}\n\n"
            f"**Recommended Next Step:** {rec}"
        )

    if category == "action":
        decision = context.get("action_decision", "")
        reason = context.get("action_reason", "")
        if decision == "NEVER_PERMITTED":
            return f"⛔ Request Denied: {reason}"
        if decision == "CONFIRMATION_REQUIRED":
            return f"⚠️ Action Required: {reason}"
        return f"✅ Action Verified: {reason}"

    return "Thank you for reaching out. Please let us know how we can assist with your order."
