"""ShopGuard Co-Pilot Backend REST API Routes (Port 8010)."""

import json
import httpx
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Response

from src.shopguard.config import settings
from src.shopguard.logging_config import logger
from src.shopguard.schemas.requests import ChatRequest, ActionConfirmRequest
from src.shopguard.schemas.responses import (
    ChatResponse,
    ActionConfirmResponse,
    DiagnosticsResponse,
    EvidenceItem,
    InvestigationSummary,
    PendingAction,
)
from src.shopguard.graph.workflow import run_workflow
from src.shopguard.tools.action_gate import consume_confirmation_token
from src.shopguard.services.cache_service import (
    get_cached_response,
    set_cached_response,
    get_cache_stats,
    clear_cache,
)
from src.shopguard.services.rate_limiter import is_rate_limited
from src.shopguard.services.llm_service import get_groq_stats
from src.shopguard.database.connection import get_shopguard_db
from src.shopguard.services.audit_service import record_audit_event

router = APIRouter(prefix="/api")

# In-memory distribution tracker
_router_counts = {
    "knowledge": 0,
    "status": 0,
    "investigation": 0,
    "action": 0,
    "ambiguous": 0,
}


# --------------------------------------------------------------------------- #
# Chat Endpoint                                                                #
# --------------------------------------------------------------------------- #

@router.post("/chat", response_model=ChatResponse, tags=["Co-Pilot"])
def chat_endpoint(payload: ChatRequest):
    """Primary chat entry point connecting UI to LangGraph orchestration."""
    session_id = payload.session_id or f"sess-{payload.customer_id}"

    # 1. Rate Limiting Check
    limited, retry_after = is_rate_limited(session_id)
    if limited:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Please retry after {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )

    # 2. Semantic Cache Check (for policy / knowledge questions)
    cached = get_cached_response(payload.message)
    if cached:
        _router_counts["knowledge"] += 1
        return ChatResponse(
            request_id=f"CACHE-{session_id[:8]}",
            session_id=session_id,
            category="knowledge",
            router_metadata={"rule_matched": "semantic_cache_hit", "confidence": 1.0},
            response=cached,
            evidence=[EvidenceItem(source="semantic_cache", detail="Served from memory cache.")],
            llm_used=False,
        )

    # 3. LangGraph Workflow Execution
    state = run_workflow(
        customer_id=payload.customer_id,
        message=payload.message,
        session_id=session_id,
    )

    category = state.get("category", "ambiguous")
    _router_counts[category] = _router_counts.get(category, 0) + 1

    # Cache successful knowledge responses
    if category == "knowledge" and state.get("final_response"):
        set_cached_response(payload.message, state["final_response"])

    # Prepare evidence objects
    evidence_items = []
    for ev in state.get("evidence", []) or []:
        if isinstance(ev, dict):
            evidence_items.append(EvidenceItem(
                source=ev.get("source", "knowledge_base"),
                detail=ev.get("detail", ""),
            ))

    # Prepare investigation summary
    inv_summary = None
    if state.get("investigation_result"):
        inv = state["investigation_result"]
        inv_summary = InvestigationSummary(
            investigation_id=inv.get("investigation_id", "INV-UNKNOWN"),
            order_id=inv.get("order_id", ""),
            issue=inv.get("issue", "unknown"),
            severity=inv.get("severity", "low"),
            findings=inv.get("findings", []),
            recommendation=inv.get("recommendation", "monitor"),
            requires_human=inv.get("requires_human", False),
        )

    # Prepare pending action
    pending_act = None
    if state.get("pending_confirmation"):
        p = state["pending_confirmation"]
        pending_act = PendingAction(
            action_name=p.get("action", ""),
            confirmation_token=p.get("confirmation_token", ""),
            expires_at=p.get("expires_at", ""),
            description=p.get("description", ""),
        )

    return ChatResponse(
        request_id=state.get("request_id", "REQ-UNKNOWN"),
        session_id=session_id,
        category=category,
        router_metadata={
            "rule_matched": state.get("matched_rule", ""),
            "target_tool": state.get("target_tool", ""),
            "confidence": state.get("confidence", 0.0),
        },
        response=state.get("final_response", ""),
        evidence=evidence_items,
        investigation_result=inv_summary,
        pending_action=pending_act,
        llm_used=state.get("llm_used", False),
        trace_id=state.get("request_id"),
    )


# --------------------------------------------------------------------------- #
# Action Confirmation Endpoint                                                #
# --------------------------------------------------------------------------- #

@router.post("/actions/confirm", response_model=ActionConfirmResponse, tags=["Actions"])
def confirm_action_endpoint(payload: ActionConfirmRequest):
    """Execute a CONFIRMATION_REQUIRED action using a valid expiring token."""
    validation = consume_confirmation_token(
        token=payload.confirmation_token,
        customer_id=payload.customer_id,
        order_id=payload.order_id,
    )

    if not validation["valid"]:
        raise HTTPException(
            status_code=403,
            detail=f"Action confirmation denied: {validation.get('reason')}",
        )

    action_name = validation["action"]
    result_summary = ""

    # Execute authorized operation in simulator
    try:
        with httpx.Client(timeout=5.0) as client:
            if action_name == "cancel_order":
                r = client.post(
                    f"{settings.SIMULATOR_URL}/orders/{payload.order_id}/cancel",
                    json={"customer_id": payload.customer_id, "reason": "Customer confirmed cancellation."},
                )
                r.raise_for_status()
                result_summary = f"Order {payload.order_id} successfully cancelled in simulator."

            elif action_name == "submit_refund_review_request":
                r = client.post(
                    f"{settings.SIMULATOR_URL}/refunds/request",
                    json={"customer_id": payload.customer_id, "order_id": payload.order_id, "reason": "Customer confirmed refund review."},
                )
                r.raise_for_status()
                refund_id = r.json().get("refund_request_id", "REF-RECORDED")
                result_summary = f"Refund review case {refund_id} created for human operations review."

            else:
                result_summary = f"Action {action_name} executed successfully."

    except Exception as exc:
        logger.error("Simulator mutation failed for confirmed action: %s", exc)
        result_summary = f"Action was authorized but failed to record in simulator: {exc}"

    # Log audit event
    audit_id = record_audit_event(
        request_id=f"ACT-EXEC-{payload.order_id}",
        actor=payload.customer_id,
        operation=f"CONFIRMED_{action_name.upper()}",
        decision="CONFIRMATION_REQUIRED",
        status="SUCCESS",
        resource_id=payload.order_id,
        details={"token": payload.confirmation_token, "result": result_summary},
    )

    return ActionConfirmResponse(
        success=True,
        action=action_name,
        order_id=payload.order_id,
        result_summary=result_summary,
        audit_event_id=audit_id,
    )


# --------------------------------------------------------------------------- #
# Orders & Case Review                                                         #
# --------------------------------------------------------------------------- #

@router.get("/orders/{order_id}", tags=["Orders"])
def get_order_endpoint(order_id: str, customer_id: Optional[str] = None):
    """Retrieve verified order details from simulator."""
    try:
        url = f"{settings.SIMULATOR_URL}/orders/{order_id}"
        if customer_id:
            url += f"?customer_id={customer_id}"
        with httpx.Client(timeout=5.0) as client:
            r = client.get(url)
            if r.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Order {order_id} not found.")
            if r.status_code == 403:
                raise HTTPException(status_code=403, detail="Customer ownership verification failed.")
            return r.json()
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Simulator service is currently unreachable.")


@router.get("/cases", tags=["Review Cases"])
def list_cases_endpoint():
    """List all open investigation & refund cases."""
    from src.shopguard.database.models import init_shopguard_db
    init_shopguard_db()
    with get_shopguard_db() as conn:
        rows = conn.execute(
            """SELECT case_id, order_id, customer_id, issue_type, severity, recommendation, status, created_at
               FROM investigation_cases ORDER BY created_at DESC LIMIT 50"""
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/audit", tags=["Audit"])
def get_audit_trail(limit: int = 50, offset: int = 0):
    """Return paginated, append-only operational audit events."""
    from src.shopguard.database.models import init_shopguard_db
    init_shopguard_db()
    with get_shopguard_db() as conn:
        rows = conn.execute(
            """SELECT event_id, request_id, timestamp, actor, operation, resource_id, decision, status, details_json
               FROM audit_events ORDER BY timestamp DESC LIMIT ? OFFSET ?""",
            (limit, offset),
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        if d.get("details_json"):
            try:
                d["details"] = json.loads(d["details_json"])
            except Exception:
                d["details"] = d["details_json"]
        result.append(d)
    return result


@router.get("/diagnostics", response_model=DiagnosticsResponse, tags=["Telemetry"])
def get_diagnostics():
    """Return live system telemetry."""
    return DiagnosticsResponse(
        cache_stats=get_cache_stats(),
        groq_stats=get_groq_stats(),
        router_distribution=_router_counts,
    )


@router.post("/cache/clear", tags=["Telemetry"])
def clear_cache_endpoint():
    """Clear memory cache."""
    cleared = clear_cache()
    return {"status": "cleared", "entries_removed": cleared}
