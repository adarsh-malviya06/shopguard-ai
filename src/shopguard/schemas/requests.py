"""Request schemas for ShopGuard AI and Simulator."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Incoming user chat request."""

    customer_id: str = Field(..., description="Active simulated customer ID (e.g. CUST-001)")
    message: str = Field(..., min_length=1, max_length=1000, description="Customer inquiry or command")
    session_id: Optional[str] = Field(None, description="Optional session or conversation ID")


class ActionConfirmRequest(BaseModel):
    """Action confirmation submission with expiring token."""

    confirmation_token: str = Field(..., description="Server-issued action confirmation token")
    customer_id: str = Field(..., description="Customer ID performing the confirmation")
    order_id: str = Field(..., description="Target order ID")
    confirmed: bool = Field(..., description="Whether user explicitly confirmed the action")


class ScenarioInjectRequest(BaseModel):
    """Admin scenario injection request for tests and demos."""

    scenario_id: str = Field(..., description="Scenario code (e.g. SG-01)")
    order_id: str = Field(..., description="Target order to modify")
    override_type: str = Field(..., description="Type of incident: HUB_DELAY, DAMAGED_ITEM, etc.")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Scenario parameters")


class OrderCancelRequest(BaseModel):
    """Order cancellation request payload."""

    customer_id: str = Field(...)
    reason: str = Field(default="Customer requested cancellation")


class RefundCreateRequest(BaseModel):
    """Refund review request payload."""

    customer_id: str = Field(...)
    order_id: str = Field(...)
    reason: str = Field(...)
    evidence_notes: Optional[str] = None
