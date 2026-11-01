"""Order Management — Live Order Tracking & Event Timelines."""

import streamlit as st
import httpx
import pandas as pd
from src.shopguard.config import settings
from ui.components.theme import apply_theme, render_brand_header

apply_theme()
render_brand_header("Order Management", "Live Tracking & Chronological Event Auditing")

active_cust = st.session_state.get("active_customer_id", "CUST-001")
sim_url = settings.SIMULATOR_URL

st.markdown(f"**Viewing Orders for Customer:** `{active_cust}`")

orders = []
try:
    with httpx.Client(timeout=4.0) as client:
        r = client.get(f"{sim_url}/customers/{active_cust}/orders")
        if r.status_code == 200:
            orders = r.json()
except Exception as ex:
    st.error(f"Failed to fetch orders from Simulator: {ex}")

if orders:
    df = pd.DataFrame(orders)
    st.dataframe(
        df[["order_id", "product_name", "amount", "order_status", "delivery_status", "order_date"]],
        use_container_width=True,
    )

    st.markdown("---")
    st.markdown("### 📦 Detailed Shipment Timeline")
    order_options = [o["order_id"] for o in orders]
    selected_order = st.selectbox("Select Order to View Timeline", options=order_options)

    if selected_order:
        try:
            with httpx.Client(timeout=4.0) as client:
                ev_res = client.get(f"{sim_url}/orders/{selected_order}/events?customer_id={active_cust}")
                if ev_res.status_code == 200:
                    events = ev_res.json().get("events", [])
                    if events:
                        for ev in events:
                            with st.container():
                                st.markdown(f"**{ev['timestamp']}** — `{ev['event_type']}` at *{ev['location']}*")
                                st.caption(ev['description'])
                                st.markdown("---")
                    else:
                        st.info("No shipment events recorded yet.")
        except Exception as ex:
            st.error(f"Error fetching shipment events: {ex}")
else:
    st.info("No orders found for this customer.")

