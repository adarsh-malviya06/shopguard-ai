"""Deterministic Request Router — keyword/regex-based classification.

NO LLM, NO embeddings, NO external API calls.
Pure Python pattern matching with explicit priority ordering.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Literal

Category = Literal["knowledge", "status", "investigation", "action", "ambiguous"]

TOOL_MAP: dict[Category, str] = {
    "knowledge":     "rag_tool",
    "status":        "status_tool",
    "investigation": "investigation_tool",
    "action":        "action_gate",
    "ambiguous":     "human_escalation",
}


@dataclass
class RouterResult:
    category:     Category
    matched_rule: str
    confidence:   float
    target_tool:  str
    reason:       str
    meta:         dict = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Sentinels & Regex Catalog                                                     #
# --------------------------------------------------------------------------- #

# Prompt injection / jailbreak sentinel
INJECTION_SENTINELS = re.compile(
    r"\b(ignore|override|bypass|forget|disregard)\b.{0,40}"
    r"\b(policy|policies|rule|rules|instruction|instructions|guideline|restriction|restrictions|previous|admin|system)\b",
    re.IGNORECASE,
)

ORDER_ID_RE = re.compile(r"\bORD[-\s]?\d+\b", re.IGNORECASE)

# Questions starting with question words about policies/timeframes are Knowledge
KNOWLEDGE_INQUIRY_PREFIX = re.compile(
    r"^(what|how\s+many|how\s+long|can\s+i|are\s+|tell\s+me|explain|is\s+there)\b",
    re.IGNORECASE,
)

# --- ACTION patterns ---
ACTION_PATTERNS: list[tuple[str, str]] = [
    (r"\b(cancel|cancell?ing)\b.{0,40}\border\b", "action_cancel_order"),
    (r"\border\b.{0,40}\b(cancel|cancell?ing)\b", "action_cancel_order"),
    (r"\b(refund|reimburse|money\s+back)\b.{0,30}\b(now|immediately|asap|please|my|me)\b", "action_refund_request"),
    (r"\b(want|need|request|initiate|process|start|issue|give|send)\b.{0,30}\b(a\s+)?(refund|reimbursement|money\s+back)\b", "action_refund_request"),
    (r"\b(submit|raise|file|lodge|create)\b.{0,30}\b(refund|return|complaint|claim)\b", "action_submit_request"),
    (r"\b(want|need)\s+to\s+return\b", "action_return_request"),
    (r"\bsend\b.{0,30}\bback\b", "action_return_request"),
    (r"\b(return\s+this|return\s+my|return\s+the)\s+(item|product|order|package)\b", "action_return_request"),
    (r"\b(escalate|raise\s+a\s+complaint|file\s+a\s+complaint)\b", "action_escalate"),
    (r"\brefund\s+my\s+(order|money|amount|payment)\b", "action_refund_request"),
    (r"\b(approve|execute|transfer)\b.{0,30}\b(refund|payment|money|rupees|funds)\b", "action_forbidden"),
    (r"\bdelete\b.{0,30}\b(log|audit|record)\b", "action_forbidden"),
    (r"\bmodify\b.{0,30}\b(bank|card|payment\s+method)\b", "action_forbidden"),
]

# --- INVESTIGATION patterns ---
INVESTIGATION_PATTERNS: list[tuple[str, str]] = [
    (r"\bwhy\b.{0,60}\b(delay|delayed|late|stuck|missing|refund|rejected|not\s+arrived|not\s+moving)\b", "investigation_why_issue"),
    (r"\bwhy\b.{0,40}\b(my\s+)?(order|shipment|package|delivery|refund)\b", "investigation_why_general"),
    (r"\b(order|shipment|package|delivery)\b.{0,40}\b(delayed|delay|stuck|stalled|stopped|not\s+moving|late)\b", "investigation_delay_stuck"),
    (r"\b(delayed|delay|stuck|stalled|late)\b.{0,40}\b(for\s+\d+\s+days|at\s+the\s+hub|in\s+transit)\b", "investigation_delay_detail"),
    (r"\b(delivery\s+delay|delayed\s+delivery)\b", "investigation_delivery_delay"),
    (r"\b(where|what\s+happened)\b.{0,40}\b(to\s+my\s+)?refund\b", "investigation_refund_status"),
    (r"\brefund\b.{0,40}\bnot\b.{0,20}\b(arrived|received|processed|credited)\b", "investigation_refund_not_arrived"),
    (r"\b(lost|missing|damaged|broken|defective)\b", "investigation_damaged_missing"),
    (r"\b(investigate|investigation|look\s+into|check\s+why)\b", "investigation_explicit"),
    (r"\bnot\s+received\b.{0,30}\b(order|product|item|package)\b", "investigation_not_received"),
    (r"\brefund\s+request\b.{0,30}\b(rejected|denied|declined)\b", "investigation_rejection"),
]

# --- STATUS patterns ---
STATUS_PATTERNS: list[tuple[str, str]] = [
    (r"\b(where|what\s+is)\b.{0,30}\b(my\s+order|order\s+status|package|parcel|delivery\s+status)\b", "status_order_location"),
    (r"\b(order\s+status|delivery\s+status|shipping\s+status)\b", "status_direct"),
    (r"\bstatus\b.{0,30}\b(of\s+)?(order|shipment|delivery|refund|payment|ORD[-\s]?\d+)\b", "status_check"),
    (r"\b(track|tracking)\b.{0,30}\b(order|package|shipment)\b", "status_tracking"),
    (r"\border\s+(ORD[-\s]?\d+)\b", "status_specific_order"),
    (r"\bORD[-\s]?\d+\b.{0,40}\b(status|where|delivered|shipped)\b", "status_specific_order"),
    (r"\b(has|was)\b.{0,20}\b(order|package|shipment)\b.{0,20}\b(shipped|dispatched|delivered|arrived)\b", "status_shipped_delivered"),
    (r"\bwhen\b.{0,30}\b(deliver|delivered|arrive|arrived|ship|shipped)\b", "status_eta"),
    (r"\bpayment\b.{0,30}\b(received|successful|confirmed|done)\b", "status_payment"),
    (r"\bis\b.{0,20}\b(my\s+)?(order|payment|refund)\b.{0,20}\b(done|complete|confirmed|successful)\b", "status_confirm"),
]

# --- KNOWLEDGE patterns ---
KNOWLEDGE_PATTERNS: list[tuple[str, str]] = [
    (r"\b(refund|return|cancell?ation|shipping|delivery|damaged|missing)\s+policy\b", "knowledge_policy_explicit"),
    (r"\bpolic(y|ies)\b", "knowledge_policy_generic"),
    (r"\b(how\s+many\s+days|how\s+long)\b.{0,40}\b(return|refund|cancel|exchange)\b", "knowledge_time_limit"),
    (r"\b(eligible|eligibility|qualify)\b.{0,30}\b(refund|return|exchange)\b", "knowledge_eligibility"),
    (r"\b(procedure|process|steps)\b.{0,30}\b(refund|return|complaint|claim|support)\b", "knowledge_procedure"),
    (r"\b(document|documents|proof|evidence)\b.{0,30}\b(required|needed|for\s+a\s+refund)\b", "knowledge_documents"),
    (r"\bwhat\b.{0,30}\b(documents?|proof|evidence)\b", "knowledge_documents"),
    (r"\bcan\s+I\b.{0,30}\b(return|refund|exchange|cancel)\b", "knowledge_can_i"),
    (r"\b(explain|tell\s+me|describe)\b.{0,30}\b(policy|procedure|rule|guideline)\b", "knowledge_explain"),
    (r"\b(electronic|electronics|fashion|clothing|book|books|kitchen)\b.{0,30}\b(returnable|eligible|policy)\b", "knowledge_category_policy"),
    (r"\b(returnable|eligible\s+for\s+return)\b", "knowledge_returnable"),
    (r"\bescalation\s+procedure\b", "knowledge_escalation"),
]


def _match_patterns(text: str, patterns: list[tuple[str, str]]) -> list[str]:
    hits = []
    for pattern, rule in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            hits.append(rule)
    return hits


def route_request(text: str) -> RouterResult:
    """Classify incoming user message deterministically."""
    text_stripped = text.strip()

    # 1. Prompt Injection Sentinels -> Action Gate
    if INJECTION_SENTINELS.search(text_stripped):
        return RouterResult(
            category="action",
            matched_rule="security_injection_detected",
            confidence=1.0,
            target_tool=TOOL_MAP["action"],
            reason="Prompt injection attempt detected; routing to Action Gate for safe denial.",
            meta={"injection_detected": True, "order_id": _extract_order_id(text_stripped)},
        )

    # 2. Knowledge Inquiries (Questions about policies/timeframes take precedence over action verbs)
    know_hits = _match_patterns(text_stripped, KNOWLEDGE_PATTERNS)
    is_inquiry = bool(KNOWLEDGE_INQUIRY_PREFIX.search(text_stripped))
    if know_hits and (is_inquiry or "policy" in text_stripped.lower() or "how many" in text_stripped.lower()):
        return RouterResult(
            category="knowledge",
            matched_rule=know_hits[0],
            confidence=min(len(know_hits) / 3.0, 1.0),
            target_tool=TOOL_MAP["knowledge"],
            reason=f"Matched knowledge inquiry: {', '.join(know_hits)}",
            meta={"rules": know_hits},
        )

    # 3. Action Patterns
    action_hits = _match_patterns(text_stripped, ACTION_PATTERNS)
    if action_hits:
        return RouterResult(
            category="action",
            matched_rule=action_hits[0],
            confidence=min(len(action_hits) / 3.0, 1.0),
            target_tool=TOOL_MAP["action"],
            reason=f"Matched action pattern(s): {', '.join(action_hits)}",
            meta={"rules": action_hits, "order_id": _extract_order_id(text_stripped)},
        )

    # 4. Investigation Patterns
    inv_hits = _match_patterns(text_stripped, INVESTIGATION_PATTERNS)
    if inv_hits:
        return RouterResult(
            category="investigation",
            matched_rule=inv_hits[0],
            confidence=min(len(inv_hits) / 3.0, 1.0),
            target_tool=TOOL_MAP["investigation"],
            reason=f"Matched investigation pattern(s): {', '.join(inv_hits)}",
            meta={"rules": inv_hits, "order_id": _extract_order_id(text_stripped)},
        )

    # 5. Status Patterns
    status_hits = _match_patterns(text_stripped, STATUS_PATTERNS)
    if status_hits:
        return RouterResult(
            category="status",
            matched_rule=status_hits[0],
            confidence=min(len(status_hits) / 3.0, 1.0),
            target_tool=TOOL_MAP["status"],
            reason=f"Matched status pattern(s): {', '.join(status_hits)}",
            meta={"rules": status_hits, "order_id": _extract_order_id(text_stripped)},
        )

    # 6. Remaining Knowledge
    if know_hits:
        return RouterResult(
            category="knowledge",
            matched_rule=know_hits[0],
            confidence=min(len(know_hits) / 3.0, 1.0),
            target_tool=TOOL_MAP["knowledge"],
            reason=f"Matched knowledge pattern(s): {', '.join(know_hits)}",
            meta={"rules": know_hits},
        )

    # 7. Fallback Ambiguous
    return RouterResult(
        category="ambiguous",
        matched_rule="fallback_ambiguous",
        confidence=0.0,
        target_tool=TOOL_MAP["ambiguous"],
        reason="No deterministic pattern matched; routing to safe human escalation.",
        meta={},
    )


def _extract_order_id(text: str) -> str | None:
    m = ORDER_ID_RE.search(text)
    return m.group(0).replace(" ", "-").upper() if m else None
