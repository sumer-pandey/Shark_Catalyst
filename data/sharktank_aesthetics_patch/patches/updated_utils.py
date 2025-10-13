# utils.py (updated with plotly theme helper and formatting utilities)
import streamlit as st
from db import run_query
import pandas as pd
import plotly.io as pio

@st.cache_data(ttl=600)
def cached_query(sql: str, params: dict = None) -> pd.DataFrame:
    """
    Cached wrapper around run_query.
    """
    return run_query(sql, params)

def format_currency(x):
    """
    Format numeric as Indian-rupee style with separators. Accepts None/NaN.
    """
    try:
        if x is None:
            return "-"
        x = float(x)
        if x == 0:
            return "₹0"
        return "₹{:,.0f}".format(x)
    except Exception:
        return str(x)

def set_plotly_theme():
    """
    Define and set a Plotly template named 'custom_theme' for consistent visuals.
    """
    template = dict(
        layout=dict(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, Arial", color="#e6eef8"),
            colorway=["#0f62fe","#7c3aed","#16a34a","#f59e0b","#ff6b6b"]
        )
    )
    pio.templates["custom_theme"] = template
    pio.templates.default = "custom_theme"