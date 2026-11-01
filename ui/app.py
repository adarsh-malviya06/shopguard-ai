"""ShopGuard AI — Main Streamlit Dashboard Application (Port 8501)."""

import streamlit as st
import httpx
from src.shopguard.config import settings
from ui.components.theme import apply_theme, render_brand_header

st.set_page_config(
    page_title="ShopGuard AI — Operations Co-Pilot",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()

render_brand_header(
    title="ShopGuard AI",
    subtitle="AI-Powered Order Management, Refund Investigation & Safety Gateway",
)

# Sidebar System Health & Active Customer Context
st.sidebar.markdown("### 👤 Active Identity Context")
demo_customers = {
    "CUST-001": "Aarav Sharma (Metro / Normal Orders)",
    "CUST-002": "Priya Patel (Delayed Hub Issues)",
    "CUST-003": "Rahul Mehta (Damaged / Missing Items)",
    "CUST-004": "Sneha Iyer (Cancelled & Active Refund)",
    "CUST-005": "Vikram Nair (Duplicate & Expired Window)",
}

selected_customer = st.sidebar.selectbox(
    "Select Customer Identity",
    options=list(demo_customers.keys()),
    format_func=lambda x: f"{x} - {demo_customers[x]}",
    index=0,
)
st.session_state["active_customer_id"] = selected_customer

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔌 Service Status")

# Probe Backend
backend_status = "🔴 Offline"
try:
    with httpx.Client(timeout=2.0) as client:
        r = client.get(f"http://localhost:{settings.SHOPGUARD_PORT}/health")
        if r.status_code == 200:
            backend_status = "🟢 Port 8010 Online"
except Exception:
    pass

# Probe Simulator
sim_status = "🔴 Offline"
try:
    with httpx.Client(timeout=2.0) as client:
        r = client.get(f"{settings.SIMULATOR_URL}/health")
        if r.status_code == 200:
            sim_status = "🟢 Port 8002 Online"
except Exception:
    pass

st.sidebar.markdown(f"**Co-Pilot Backend**: {backend_status}")
st.sidebar.markdown(f"**E-Commerce Simulator**: {sim_status}")
st.sidebar.caption("Runtime: Python 3.11.15 | Zero-Paid Architecture")

# Main Page Overview
st.markdown("### Welcome to ShopGuard AI Operations Hub")
st.markdown(
    """
    ShopGuard AI is an intelligent e-commerce operations co-pilot that helps customers and support teams
    safely investigate order issues, understand policies, and handle refund requests with **100% deterministic safety gates**.

    👈 **Select a page from the sidebar to begin:**
    - **1_Overview_Dashboard**: High-level operations telemetry and case metrics.
    - **2_Customer_CoPilot**: Live interactive chat co-pilot with verified citations.
    - **3_Order_Management**: Live order lookup and delivery timelines.
    - **4_Investigation_Center**: Detailed anomaly and root-cause analysis.
    - **5_Refund_Review_Center**: Operational refund cases and risk evaluations.
    - **6_System_Diagnostics**: Behind-the-scenes traces, cache stats, and router metrics.
    """
)

# Metric summary row
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(
        """<div class="metric-card"><div class="metric-value">4</div><div class="metric-label">Router Categories</div></div>""",
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        """<div class="metric-card"><div class="metric-value">3</div><div class="metric-label">Permission Tiers</div></div>""",
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        """<div class="metric-card"><div class="metric-value">100%</div><div class="metric-label">Deterministic Routing</div></div>""",
        unsafe_allow_html=True,
    )
with col4:
    st.markdown(
        """<div class="metric-card"><div class="metric-value">₹0</div><div class="metric-label">Paid API Cost</div></div>""",
        unsafe_allow_html=True,
    )
