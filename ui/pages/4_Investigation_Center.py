"""Investigation Center — Operational Issue Analysis & Evidence Reviews."""

import streamlit as st
import httpx
from src.shopguard.config import settings
from ui.components.theme import apply_theme, render_brand_header
from src.shopguard.tools.investigation_tool import investigate_order

apply_theme()
render_brand_header("Investigation Center", "Root-Cause Incident Analysis & Delay Heuristics")

active_cust = st.session_state.get("active_customer_id", "CUST-001")

st.markdown("### 🔍 Run Investigation Pipeline on Demand")
col1, col2 = st.columns([2, 1])

with col1:
    order_input = st.text_input("Enter Order ID to Investigate (e.g. ORD-1003, ORD-1004):", value="ORD-1003")

with col2:
    st.write("")
    st.write("")
    run_btn = st.button("Investigate Order", type="primary")

if run_btn and order_input:
    with st.spinner("Analyzing timeline, ETA, and transit anomalies..."):
        result = investigate_order(order_input.strip().upper(), active_cust)

        if result.get("issue") == "error":
            st.error(f"Investigation failed: {result['findings'][0]}")
        else:
            st.success(f"Investigation Complete: `{result['investigation_id']}`")

            # Severity badge & recommendation
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("Issue Identified", result["issue"].replace("_", " ").title())
            with col_b:
                st.metric("Severity", result["severity"].upper())
            with col_c:
                st.metric("Human Escalation Required", "YES" if result["requires_human"] else "NO")

            st.markdown("#### 📋 Verified Findings")
            for f in result.get("findings", []):
                st.markdown(f"- {f}")

            st.markdown("#### 📌 Chronological Evidence")
            for ev in result.get("evidence", []):
                st.markdown(f"- `[{ev.get('source')}]` {ev.get('detail')}")

            st.markdown("#### 💡 System Recommendation")
            st.info(f"**Action Recommended:** {result.get('recommendation', '').replace('_', ' ').title()}")

