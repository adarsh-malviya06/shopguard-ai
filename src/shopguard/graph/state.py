"""LangGraph Workflow State Schema."""

from __future__ import annotations
from typing import Optional, Literal, Any
from typing_extensions import TypedDict


class ShopGuardState(TypedDict, total=False):
    # Identity
    request_id:   str
    session_id:   Optional[str]
    customer_id:  str
    user_message: str

    # Routing
    category:      Literal["knowledge", "status", "investigation", "action", "ambiguous"]
    router_reason: str
    matched_rule:  str
    target_tool:   str
    confidence:    float

    # Order context
    order_id:        Optional[str]
    order_data:      Optional[dict]
    shipment_events: Optional[list]

    # Tool outputs
    policy_chunks:       Optional[list]
    evidence:            Optional[list]
    investigation_result: Optional[dict]

    # Action gate
    action_decision:     Optional[str]
    action_reason:       Optional[str]
    pending_confirmation: Optional[dict]

    # Response
    final_response: str
    llm_used:       bool

    # Debug / Audit
    error: Optional[str]
    trace: list
