"""Overview Dashboard — Live Operational Metrics & Case Status."""

import streamlit as st
import httpx
import pandas as pd
from src.shopguard.config import settings
from ui.components.theme import apply_theme, render_brand_header

apply_theme()
render_brand_header("Operations Overview", "Real-Time System Metrics & Order Statistics")

# Fetch Backend Diagnostics & Live Data
backend_url = f"http://localhost:{settings.SHOPGUARD_PORT}"
sim_url = settings.SIMULATOR_URL

diag_data = None
orders_data = []
cases_data = []

try:
    with httpx.Client(timeout=3.0) as client:
        r_diag = client.get(f"{backend_url}/api/diagnostics")
        if r_diag.status_code == 200:
            diag_data = r_diag.json()

        r_cases = client.get(f"{backend_url}/api/cases")
        if r_cases.status_code == 200:
            cases_data = r_cases.json()

        r_orders = client.get(f"{sim_url}/customers/CUST-001/orders")
        if r_orders.status_code == 200:
            orders_data = r_orders.json()
except Exception as e:
    st.warning(f"Could not connect to backend services: {e}. Showing offline status.")

# Top Metrics
col1, col2, col3, col4 = st.columns(4)

total_cases = len(cases_data)
pending_cases = sum(1 for c in cases_data if c.get("status") == "OPEN")
cache_hits = diag_data.get("cache_stats", {}).get("hits", 0) if diag_data else 0
groq_calls = diag_data.get("groq_stats", {}).get("calls", 0) if diag_data else 0

with col1:
    st.markdown(
        f"""<div class="metric-card"><div class="metric-value">{total_cases}</div><div class="metric-label">Investigation Cases</div></div>""",
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        f"""<div class="metric-card"><div class="metric-value">{pending_cases}</div><div class="metric-label">Open Review Cases</div></div>""",
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        f"""<div class="metric-card"><div class="metric-value">{cache_hits}</div><div class="metric-label">Cache Hits</div></div>""",
        unsafe_allow_html=True,
    )
with col4:
    st.markdown(
        f"""<div class="metric-card"><div class="metric-value">{groq_calls}</div><div class="metric-label">Groq Explanations</div></div>""",
        unsafe_allow_html=True,
    )

st.markdown("---")

col_left, col_right = st.columns([1, 1])

with col_left:
    st.markdown("### 📊 Router Classification Distribution")
    if diag_data and "router_distribution" in diag_data:
        dist = diag_data["router_distribution"]
        df_dist = pd.DataFrame(list(dist.items()), columns=["Category", "Count"])
        st.bar_chart(df_dist.set_index("Category"))
    else:
        st.info("No query traffic recorded yet. Start chatting in Customer Co-Pilot to populate.")

with col_right:
    st.markdown("### 🚨 Recent Operational Cases")
    if cases_data:
        df_cases = pd.DataFrame(cases_data)
        st.dataframe(df_cases[["case_id", "order_id", "issue_type", "severity", "status"]], use_container_width=True)
    else:
        st.info("No open escalation cases in database.")
