"""LangGraph Graph Nodes — one function per node, pure state transforms."""

from __future__ import annotations
import uuid
import time
from datetime import datetime, timezone

from src.shopguard.graph.state import ShopGuardState
from src.shopguard.router.request_router import route_request
from src.shopguard.tools import rag_tool, status_tool, investigation_tool, action_gate
from src.shopguard.services import llm_service, audit_service
from src.shopguard.logging_config import logger


def _trace(state: ShopGuardState, node: str, detail: str) -> None:
    """Append a trace entry to state."""
    state.setdefault("trace", []).append({
        "node":      node,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "detail":    detail,
    })


# --------------------------------------------------------------------------- #
# Node 1 — Request Router                                                       #
# --------------------------------------------------------------------------- #

def request_router_node(state: ShopGuardState) -> ShopGuardState:
    """Classify the user message deterministically. No LLM."""
    result = route_request(state.get("user_message", ""))
    state["category"]      = result.category
    state["router_reason"] = result.reason
    state["matched_rule"]  = result.matched_rule
    state["target_tool"]   = result.target_tool
    state["confidence"]    = result.confidence

    # Extract order_id hint from router metadata if present
    if result.meta.get("order_id"):
        state.setdefault("order_id", result.meta["order_id"])

    _trace(state, "request_router_node",
           f"category={result.category} | rule={result.matched_rule} | confidence={result.confidence:.2f}")
    return state


# --------------------------------------------------------------------------- #
# Node 2 — Knowledge Handler (RAG)                                              #
# --------------------------------------------------------------------------- #

def knowledge_handler_node(state: ShopGuardState) -> ShopGuardState:
    """Retrieve policy chunks from ChromaDB and generate response."""
    query  = state.get("user_message", "")
    chunks = rag_tool.retrieve_policy(query)
    state["policy_chunks"] = chunks
    state["evidence"]      = [{"source": c["source"], "detail": c["content"][:200]} for c in chunks]

    if not chunks:
        state["final_response"] = (
            "I could not find a matching policy in our knowledge base. "
            "Please contact our support team for assistance."
        )
        state["llm_used"] = False
        _trace(state, "knowledge_handler_node", "RAG returned 0 chunks — failing closed.")
        return state

    response, used = llm_service.explain_policy(query, chunks)
    state["final_response"] = response
    state["llm_used"]       = used
    _trace(state, "knowledge_handler_node", f"RAG chunks={len(chunks)} | llm_used={used}")
    return state


# --------------------------------------------------------------------------- #
# Node 3 — Status Handler                                                       #
# --------------------------------------------------------------------------- #

def status_handler_node(state: ShopGuardState) -> ShopGuardState:
    """Retrieve live order status from the Simulator."""
    order_id    = state.get("order_id", "")
    customer_id = state.get("customer_id", "")

    if not order_id:
        state["final_response"] = (
            "Please provide an Order ID (e.g. ORD-1001) so I can look it up for you."
        )
        state["llm_used"] = False
        _trace(state, "status_handler_node", "No order_id provided.")
        return state

    order_data = status_tool.get_order_status(order_id, customer_id)
    state["order_data"] = order_data

    if "error" in order_data:
        err = order_data["error"]
        if err == "access_denied":
            state["final_response"] = "Access denied: that order does not belong to your account."
        elif err == "not_found":
            state["final_response"] = f"Order {order_id} was not found."
        else:
            state["final_response"] = "The order information service is temporarily unavailable."
        state["llm_used"] = False
        _trace(state, "status_handler_node", f"error={err}")
        return state

    # Format deterministically — no LLM needed for simple status
    state["final_response"] = (
        f"**Order {order_data['order_id']}** — {order_data.get('product_name', 'N/A')}\n\n"
        f"• Order Status:    {order_data.get('order_status')}\n"
        f"• Delivery Status: {order_data.get('delivery_status')}\n"
        f"• Payment Status:  {order_data.get('payment_status')}\n"
        f"• Order Date:      {order_data.get('order_date', 'N/A')}"
    )
    state["llm_used"] = False
    state["evidence"] = [{"source": "simulator:order", "detail": f"Order {order_id} status retrieved."}]
    _trace(state, "status_handler_node", f"order_status={order_data.get('order_status')}")
    return state


# --------------------------------------------------------------------------- #
# Node 4 — Investigation Handler                                                #
# --------------------------------------------------------------------------- #

def investigation_handler_node(state: ShopGuardState) -> ShopGuardState:
    """Run the investigation pipeline and generate a grounded explanation."""
    order_id    = state.get("order_id", "")
    customer_id = state.get("customer_id", "")
    query       = state.get("user_message", "")

    if not order_id:
        state["final_response"] = (
            "Please provide an Order ID so I can investigate the issue for you."
        )
        state["llm_used"] = False
        _trace(state, "investigation_handler_node", "No order_id provided.")
        return state

    result = investigation_tool.investigate_order(order_id, customer_id)
    state["investigation_result"] = result
    state["evidence"]             = result.get("evidence", [])

    if result.get("issue") == "error":
        state["final_response"] = result["findings"][0] if result.get("findings") else "Investigation failed."
        state["llm_used"] = False
        _trace(state, "investigation_handler_node", "error returned from investigate_order")
        return state

    response, used = llm_service.explain_investigation(query, result)
    state["final_response"] = response
    state["llm_used"]       = used
    _trace(state, "investigation_handler_node",
           f"issue={result.get('issue')} | severity={result.get('severity')} | llm_used={used}")
    return state


# --------------------------------------------------------------------------- #
# Node 5 — Action Gate Handler                                                  #
# --------------------------------------------------------------------------- #

def action_gate_handler_node(state: ShopGuardState) -> ShopGuardState:
    """Evaluate the requested action deterministically."""
    customer_id = state.get("customer_id", "")
    order_id    = state.get("order_id", "")
    order_data  = state.get("order_data") or {}
    matched_rule = state.get("matched_rule", "")

    # Map router rule to action name
    action_name = _rule_to_action(matched_rule, state.get("user_message", ""))

    # Fetch order state for eligibility checks if needed
    if order_id and not order_data:
        od = status_tool.get_order_status(order_id, customer_id)
        if "error" not in od:
            state["order_data"] = od
            order_data = od

    decision = action_gate.evaluate_action(action_name, customer_id, order_id, order_data)
    state["action_decision"] = decision["decision"]
    state["action_reason"]   = decision.get("reason", "")

    if decision["decision"] == "CONFIRMATION_REQUIRED":
        state["pending_confirmation"] = {
            "action":             decision.get("action"),
            "confirmation_token": decision.get("confirmation_token"),
            "expires_at":         decision.get("expires_at"),
            "description":        decision.get("reason"),
        }
        state["final_response"] = decision.get("reason", "Action requires your confirmation.")
    elif decision["decision"] == "NEVER_PERMITTED":
        state["final_response"] = (
            f"⛔ This action is not permitted: {decision.get('reason', '')}"
        )
    else:
        state["final_response"] = f"✅ {decision.get('reason', 'Action completed.')}"

    state["llm_used"] = False
    _trace(state, "action_gate_handler_node",
           f"action={action_name} | decision={decision['decision']}")
    return state


# --------------------------------------------------------------------------- #
# Node 6 — Audit Logger                                                         #
# --------------------------------------------------------------------------- #

def audit_logger_node(state: ShopGuardState) -> ShopGuardState:
    """Append an audit event for every completed request."""
    decision = state.get("action_decision", "INFO_ONLY")
    if not decision or decision not in ("AUTO_ALLOWED", "CONFIRMATION_REQUIRED", "NEVER_PERMITTED"):
        decision = "INFO_ONLY"

    op_map = {
        "knowledge":     "POLICY_RETRIEVAL",
        "status":        "ORDER_STATUS_CHECK",
        "investigation": "ORDER_INVESTIGATION",
        "action":        "ACTION_REQUEST",
        "ambiguous":     "AMBIGUOUS_REQUEST",
    }
    operation = op_map.get(state.get("category", ""), "UNKNOWN")

    audit_service.record_audit_event(
        request_id  = state.get("request_id", "unknown"),
        actor       = state.get("customer_id", "unknown"),
        operation   = operation,
        decision    = decision,
        status      = "SUCCESS" if not state.get("error") else "FAILED",
        resource_id = state.get("order_id"),
        details     = {
            "category":    state.get("category"),
            "matched_rule": state.get("matched_rule"),
            "llm_used":    state.get("llm_used"),
        },
    )
    _trace(state, "audit_logger_node", f"operation={operation} | decision={decision}")
    return state


# --------------------------------------------------------------------------- #
# Helpers                                                                       #
# --------------------------------------------------------------------------- #

def _rule_to_action(matched_rule: str, message: str) -> str:
    """Infer action name, prioritizing forbidden financial operations."""
    import re

    text = f"{matched_rule} {message}".lower()

    # 1. Forbidden financial actions MUST be checked first.
    transfer_patterns = [
        r"\btransfer\b",
        r"\bwire\s+(?:money|funds)\b",
        r"\b(send|pay)\s+(?:the\s+)?(?:money|funds)\b",
    ]

    if any(re.search(pattern, text) for pattern in transfer_patterns):
        return "transfer_money"

    # 2. Actual financial refund execution is forbidden.
    forbidden_refund_patterns = [
        r"\bexecute\s+(?:an?\s+)?(?:financial\s+)?refund\b",
        r"\bfinancial\s+refund\b",
        r"\bmark\s+(?:the\s+)?refund\s+paid\b",
    ]

    if any(re.search(pattern, text) for pattern in forbidden_refund_patterns):
        return "execute_financial_refund"

    # 3. Normal permitted actions are checked afterward.
    if "cancel" in text:
        return "cancel_order"

    if "refund" in text or "reimburs" in text:
        return "submit_refund_review_request"

    if "return" in text:
        return "submit_return_request"

    if "escalate" in text or "complaint" in text:
        return "escalate_to_support"

    return "unknown_action"
