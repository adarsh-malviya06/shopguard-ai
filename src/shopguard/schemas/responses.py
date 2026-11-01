"""Response schemas for ShopGuard AI and Simulator."""

from typing import Optional, List, Dict, Any, Generic, TypeVar
from datetime import datetime, timezone
from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ErrorResponse(BaseModel):
    error: ErrorDetail


class StandardResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    message: Optional[str] = None


class EvidenceItem(BaseModel):
    source: str
    detail: str


class InvestigationSummary(BaseModel):
    investigation_id: str
    order_id: str
    issue: str
    severity: str
    findings: List[str] = Field(default_factory=list)
    recommendation: str
    requires_human: bool = False


class PendingAction(BaseModel):
    action_name: str
    confirmation_token: str
    expires_at: str
    description: str


class ChatResponse(BaseModel):
    """Primary chat endpoint response."""

    request_id: str
    session_id: Optional[str] = None
    category: str
    router_metadata: Dict[str, Any] = Field(default_factory=dict)
    response: str
    evidence: List[EvidenceItem] = Field(default_factory=list)
    investigation_result: Optional[InvestigationSummary] = None
    pending_action: Optional[PendingAction] = None
    llm_used: bool = False
    trace_id: Optional[str] = None


class ActionConfirmResponse(BaseModel):
    """Response returned upon confirming an action."""

    success: bool
    action: str
    order_id: str
    result_summary: str
    audit_event_id: str


class DiagnosticsResponse(BaseModel):
    """System diagnostics and telemetry payload."""

    cache_stats: Dict[str, Any]
    groq_stats: Dict[str, Any]
    router_distribution: Dict[str, int]
