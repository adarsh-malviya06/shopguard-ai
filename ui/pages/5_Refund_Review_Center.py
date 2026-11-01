"""Refund Review Center — Operational Case Processing & Risk Analysis."""

import streamlit as st
import httpx
import pandas as pd
from src.shopguard.config import settings
from ui.components.theme import apply_theme, render_brand_header

apply_theme()
render_brand_header("Refund Review Center", "Controlled Review Queue & Simulated Operations")

sim_url = settings.SIMULATOR_URL

st.markdown("### 📋 Pending Refund Review Cases (Simulator)")

try:
    with httpx.Client(timeout=4.0) as client:
        # Fetch simulated refunds from simulator DB
        r = client.get(f"{sim_url}/orders/ORD-1008/refunds")
        refunds = r.json() if r.status_code == 200 else []
except Exception as ex:
    st.error(f"Failed to fetch refund cases: {ex}")
    refunds = []

if refunds:
    df_ref = pd.DataFrame(refunds)
    st.dataframe(df_ref, use_container_width=True)
else:
    st.info("No active refund reviews pending in queue.")

st.markdown("---")
st.markdown("### ⚠️ Strict Operational Policy Notice")
st.warning(
    """
    **Zero-Financial Payout Enforced**:
    ShopGuard AI supports operational review decisions and status tracking only.
    Under no circumstances does this platform execute automated financial transfers, bank charges, or UPI transactions.
    """
)
