"""Theme styling and helpers for ShopGuard AI Streamlit Dashboard."""

import streamlit as st

CUSTOM_CSS = """
<style>
    /* Global styles */
    .stApp {
        background-color: #f8fafc;
        color: #0f172a;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    /* Header & Branding */
    .brand-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #ffffff;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }

    .brand-title {
        font-size: 1.8rem;
        font-weight: 700;
        margin: 0;
        color: #ffffff;
    }

    .brand-subtitle {
        font-size: 0.95rem;
        color: #94a3b8;
        margin-top: 0.25rem;
    }

    /* Metric cards */
    .metric-card {
        background: #ffffff;
        padding: 1.25rem;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        text-align: center;
    }

    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1e3a8a;
    }

    .metric-label {
        font-size: 0.85rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.25rem;
    }

    /* Badges */
    .badge-evidence {
        background-color: #e0f2fe;
        color: #0369a1;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 0.5rem;
    }
</style>
"""


def apply_theme():
    """Apply standard navy/white enterprise theme."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_brand_header(title: str, subtitle: str):
    """Render top brand banner."""
    st.markdown(
        f"""
        <div class="brand-header">
            <div class="brand-title">🛡️ {title}</div>
            <div class="brand-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
