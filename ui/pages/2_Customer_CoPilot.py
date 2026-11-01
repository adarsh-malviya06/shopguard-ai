"""Customer Co-Pilot — Interactive Chat with Evidence & Safety Confirmation."""

import streamlit as st
import httpx
from src.shopguard.config import settings
from ui.components.theme import apply_theme, render_brand_header

apply_theme()
render_brand_header("Customer Co-Pilot", "AI-Powered Order Assistance with Grounded Citations")

backend_url = f"http://localhost:{settings.SHOPGUARD_PORT}"

# Session State for Chat History
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "assistant",
            "content": "Hello! I am ShopGuard Co-Pilot. I can help you check order status, understand return policies, or investigate delivery delays. How can I help you today?",
            "evidence": [],
            "pending_action": None,
        }
    ]

active_cust = st.session_state.get("active_customer_id", "CUST-001")

st.markdown(f"**Chatting as Active Customer:** `{active_cust}`")

# Display Message History
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("evidence"):
            st.markdown("##### 📌 Verified Evidence & Citations")
            for ev in msg["evidence"]:
                st.markdown(f"- `<span class='badge-evidence'>{ev['source']}</span>` {ev['detail']}", unsafe_allow_html=True)

        # Handle Action Confirmation Card
        if msg.get("pending_action"):
            act = msg["pending_action"]
            st.warning(f"**Confirmation Required:** {act['description']}")
            col_conf1, col_conf2 = st.columns([1, 4])
            with col_conf1:
                if st.button("Confirm Action", key=f"btn_{act['confirmation_token']}"):
                    try:
                        with httpx.Client(timeout=5.0) as client:
                            res = client.post(
                                f"{backend_url}/api/actions/confirm",
                                json={
                                    "confirmation_token": act["confirmation_token"],
                                    "customer_id": active_cust,
                                    "order_id": act.get("order_id", "ORD-UNKNOWN"),
                                    "confirmed": True,
                                },
                            )
                            if res.status_code == 200:
                                st.success(f"Action Confirmed! {res.json()['result_summary']}")
                            else:
                                st.error(f"Action failed: {res.json().get('detail')}")
                    except Exception as ex:
                        st.error(f"Error submitting confirmation: {ex}")

# Chat Input Box
user_input = st.chat_input("Ask a question, check order status, or request assistance...")

if user_input:
    # Append user message
    st.session_state["messages"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Call backend /api/chat
    with st.chat_message("assistant"):
        with st.spinner("Analyzing request and verifying facts..."):
            try:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(
                        f"{backend_url}/api/chat",
                        json={
                            "customer_id": active_cust,
                            "message": user_input,
                            "session_id": f"sess-{active_cust}",
                        },
                    )

                    if resp.status_code == 200:
                        data = resp.json()
                        reply = data.get("response", "")
                        evidence = data.get("evidence", [])
                        pending_action = data.get("pending_action")
                        llm_used = data.get("llm_used", False)

                        st.markdown(reply)
                        if llm_used:
                            st.caption("🤖 Explanation generated using Groq API Free-Tier (Grounded).")
                        else:
                            st.caption("⚡ Deterministic template response (Zero-LLM fallback).")

                        if evidence:
                            st.markdown("##### 📌 Verified Evidence & Citations")
                            for ev in evidence:
                                st.markdown(f"- `<span class='badge-evidence'>{ev['source']}</span>` {ev['detail']}", unsafe_allow_html=True)

                        if pending_action:
                            st.warning(f"**Confirmation Required:** {pending_action['description']}")

                        # Save to session history
                        st.session_state["messages"].append({
                            "role": "assistant",
                            "content": reply,
                            "evidence": evidence,
                            "pending_action": pending_action,
                        })

                    elif resp.status_code == 429:
                        st.error("Rate limit exceeded. Please wait a few seconds before trying again.")
                    else:
                        st.error(f"Server returned status {resp.status_code}: {resp.text}")

            except Exception as e:
                st.error(f"Could not connect to ShopGuard Backend on port {settings.SHOPGUARD_PORT}: {e}")
