# AGENTS.md — Permanent Project Development Guidelines

This document serves as the mandatory rules of engagement for all AI agents and engineers working in the `shopguard-ai` repository.

---

## 1. Environment & Runtime Mandates

1. **Python 3.11.15 Lock**:
   - The verified runtime is **Python 3.11.15**.
   - Do NOT attempt to upgrade or change the Python version to 3.12 or any other version.
   - All libraries specified in `requirements.txt` must have stable Windows wheels for Python 3.11.

2. **Strict Virtual Environment Policy**:
   - The virtual environment is located at `c:\Users\User\OneDrive\Desktop\shopguard-ai\.venv`.
   - **DO NOT** recreate, delete, or re-initialize `.venv`.
   - **DO NOT** install packages globally.
   - Always run commands via `.\.venv\Scripts\python.exe`, `.\.venv\Scripts\pip.exe`, or activate `.\.venv\Scripts\Activate.ps1`.

---

## 2. Zero-Paid & Dependency Policy

1. **₹0 Budget / Free-Only**:
   - Only free, open-source Python packages may be used.
   - Do NOT introduce OpenAI, Anthropic, or any paid third-party AI APIs.
   - Do NOT introduce paid database hosting, paid cloud services, or paid tools.

2. **Groq API Rules**:
   - Groq API is the primary LLM provider.
   - **Free tier only**. Never upgrade to a billable account.
   - Always use the official `groq` Python SDK.
   - Keep model configurable via the environment variable `GROQ_MODEL` (e.g. `llama-3.1-8b-instant`).
   - Keep prompts concise and enforce bounded max output tokens (e.g. 512).
   - If Groq returns 429, timeouts, or errors, **immediately trigger the deterministic fallback engine**. Groq availability must never be a single point of failure for core operations.
   - Never log API keys. Keep `.env` in `.gitignore`.

---

## 3. Core Architectural Non-Negotiables

1. **No LLM in Request Routing**:
   - The Request Router (`src/shopguard/router/`) must use pure deterministic Python regular expressions, keywords, and explicit priority rules.
   - Zero LLM calls are allowed to determine request classification.

2. **No LLM in Action Authorization**:
   - The Action Gate (`src/shopguard/tools/action_gate.py`) is 100% deterministic code.
   - The 3 permission tiers must be rigidly enforced:
     - `AUTO_ALLOWED` (read/query)
     - `CONFIRMATION_REQUIRED` (cancellations/returns with expiring token)
     - `NEVER_PERMITTED` (money transfers, card changes, log deletions)
   - Prompt injection or LLM output must NEVER be capable of overriding action decisions.

3. **Zero Financial Payouts**:
   - No payment gateway integrations (no Stripe, Razorpay, UPI).
   - No real financial transactions under any circumstances.

4. **Customer Ownership Isolation**:
   - Never serve private order details or permit actions unless the order belongs to the active `customer_id`.
   - Prevent cross-customer information leakage across chat and APIs.

5. **Genuine Implementations**:
   - No mock RAG: use genuine ChromaDB vector storage with `all-MiniLM-L6-v2` embeddings.
   - No mock simulator: use a real running FastAPI application on port 8002 backed by SQLite.
   - No hardcoded dashboard metrics: all numbers must be computed from SQLite queries.

---

## 4. Coding & Architecture Standards

1. **Modular Code**:
   - Keep functions focused and under 60 lines where possible.
   - Write clear docstrings and meaningful comments on complex business logic.
   - Avoid unnecessary abstraction layers or circular imports.

2. **Error Handling & Fail Closed**:
   - Catch specific exceptions rather than bare `except:`.
   - If a database query, simulator call, or RAG search fails, fail closed safely (escalate to human support).
   - Never return fabricated or hallucinated data when a service is unreachable.

3. **Audit Logging**:
   - Every state change and router/action decision must be appended to `shopguard.db` and mirrored to `logs/audit.jsonl`.
   - Sensitive data (passwords, card numbers, raw auth tokens) must be stripped from audit logs.

4. **Testing Before Acceptance**:
   - Run unit tests and golden scenarios after each change.
   - Never bypass or disable a security test to make CI pass.
