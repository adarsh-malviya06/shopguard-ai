"""System Diagnostics — Tracing, Vector Retrieval Telemetry & Golden Scenario Evaluator."""

import streamlit as st
import httpx
import json
import pandas as pd
from src.shopguard.config import settings
from ui.components.theme import apply_theme, render_brand_header
from src.shopguard.tools.rag_tool import collection_health

apply_theme()
render_brand_header("System Diagnostics", "Under-The-Hood Traces, Telemetry & Golden Scenario Tests")

backend_url = f"http://localhost:{settings.SHOPGUARD_PORT}"

# 1. Telemetry row
diag = {}
try:
    with httpx.Client(timeout=3.0) as client:
        r = client.get(f"{backend_url}/api/diagnostics")
        if r.status_code == 200:
            diag = r.json()
except Exception:
    pass

col1, col2, col3, col4 = st.columns(4)
c_stats = diag.get("cache_stats", {})
g_stats = diag.get("groq_stats", {})

with col1:
    st.metric("Cache Hit Ratio", f"{c_stats.get('hit_ratio', 0.0) * 100:.1f}%")
with col2:
    st.metric("Cache Entries", f"{c_stats.get('active_entries', 0)} / {c_stats.get('total_capacity', 100)}")
with col3:
    st.metric("Groq Calls", g_stats.get("calls", 0))
with col4:
    st.metric("Fallback Activations", g_stats.get("fallbacks", 0))

st.markdown("---")

# 2. ChromaDB RAG Health
st.markdown("### 📚 ChromaDB Vector Store Status")
health = collection_health()
col_r1, col_r2 = st.columns(2)
with col_r1:
    st.info(f"**Collection Status:** `{health['status']}` | **Total Chunks:** `{health['total_chunks']}`")
with col_r2:
    st.caption(f"**Indexed Policy Sources:** {', '.join(health['indexed_sources'])}")

st.markdown("---")

# 3. Live Audit Trail Browser
st.markdown("### 📜 Append-Only Audit Trail")
try:
    with httpx.Client(timeout=3.0) as client:
        r_audit = client.get(f"{backend_url}/api/audit?limit=15")
        if r_audit.status_code == 200:
            audit_events = r_audit.json()
            if audit_events:
                df_audit = pd.DataFrame(audit_events)
                st.dataframe(df_audit[["timestamp", "actor", "operation", "decision", "status"]], use_container_width=True)
            else:
                st.info("No audit events recorded yet.")
except Exception as ex:
    st.warning(f"Could not load audit log: {ex}")

st.markdown("---")

# 4. Cache Management
st.markdown("### 🧹 Cache Operations")
if st.button("Clear Semantic Cache"):
    try:
        with httpx.Client(timeout=3.0) as client:
            r = client.post(f"{backend_url}/api/cache/clear")
            if r.status_code == 200:
                st.success("Semantic cache successfully cleared.")
                st.rerun()
    except Exception as ex:
        st.error(f"Error clearing cache: {ex}")
