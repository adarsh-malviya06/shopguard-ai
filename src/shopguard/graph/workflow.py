"""LangGraph Workflow — wires nodes and conditional edges."""

from __future__ import annotations
from langgraph.graph import StateGraph, END

from src.shopguard.graph.state import ShopGuardState
from src.shopguard.graph.nodes import (
    request_router_node,
    knowledge_handler_node,
    status_handler_node,
    investigation_handler_node,
    action_gate_handler_node,
    audit_logger_node,
)


def _route_after_router(state: ShopGuardState) -> str:
    """Conditional edge: select next node based on router category."""
    return {
        "knowledge":     "knowledge_handler",
        "status":        "status_handler",
        "investigation": "investigation_handler",
        "action":        "action_gate_handler",
        "ambiguous":     "audit_logger",
    }.get(state.get("category", "ambiguous"), "audit_logger")


def build_workflow() -> StateGraph:
    """Construct and compile the ShopGuard LangGraph workflow."""
    builder = StateGraph(ShopGuardState)

    # Add nodes
    builder.add_node("request_router",      request_router_node)
    builder.add_node("knowledge_handler",   knowledge_handler_node)
    builder.add_node("status_handler",      status_handler_node)
    builder.add_node("investigation_handler", investigation_handler_node)
    builder.add_node("action_gate_handler", action_gate_handler_node)
    builder.add_node("audit_logger",        audit_logger_node)

    # Entry point
    builder.set_entry_point("request_router")

    # Conditional routing from router
    builder.add_conditional_edges(
        "request_router",
        _route_after_router,
        {
            "knowledge_handler":     "knowledge_handler",
            "status_handler":        "status_handler",
            "investigation_handler": "investigation_handler",
            "action_gate_handler":   "action_gate_handler",
            "audit_logger":          "audit_logger",
        },
    )

    # All handlers converge to audit_logger
    for node in ("knowledge_handler", "status_handler",
                 "investigation_handler", "action_gate_handler"):
        builder.add_edge(node, "audit_logger")

    # Audit logger terminates the graph
    builder.add_edge("audit_logger", END)

    return builder.compile()


# Module-level compiled graph (lazy singleton)
_graph = None


def get_graph():
    """Return the compiled ShopGuard workflow graph (singleton)."""
    global _graph
    if _graph is None:
        _graph = build_workflow()
    return _graph


def run_workflow(customer_id: str, message: str, session_id: str | None = None,
                 order_id: str | None = None) -> ShopGuardState:
    """Run the ShopGuard workflow for a user message.

    This is the single entry point called by the API and tests.
    """
    import uuid
    graph = get_graph()

    initial_state: ShopGuardState = {
        "request_id":  f"REQ-{uuid.uuid4().hex[:10].upper()}",
        "session_id":  session_id,
        "customer_id": customer_id,
        "user_message": message,
        "order_id":    order_id,
        "trace":       [],
        "llm_used":    False,
    }

    return graph.invoke(initial_state)
