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
    Define and set a Plotly template named 'custom_theme' that matches the Playfair/Lato theme.
    This ensures all Plotly charts use the same fonts and the project's accent color.
    """
    template = dict(
        layout=dict(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Lato, Arial, sans-serif", color="#B8B8B8"),
            colorway=["#9D8C5A", "#E0E0E0", "#B8B8B8", "#9FB0C3", "#7A5C2F"],
            title=dict(font=dict(family="Playfair Display, Georgia, serif", color="#E0E0E0", size=18)),
            xaxis=dict(titlefont=dict(family="Lato, Arial", color="#B8B8B8")),
            yaxis=dict(titlefont=dict(family="Lato, Arial", color="#B8B8B8"))
        )
    )
    pio.templates["custom_theme"] = template
    pio.templates.default = "custom_theme"
