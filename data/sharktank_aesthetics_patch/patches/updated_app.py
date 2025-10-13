# app.py (updated to inject CSS and apply Plotly theme)
import streamlit as st
from importlib import import_module
from utils import cached_query, set_plotly_theme
import datetime
import os

# Apply Plotly theme
try:
    set_plotly_theme()
except Exception:
    # If theme setup fails, continue gracefully
    pass

st.set_page_config(page_title="Shark Tank India — Data, Deals & VC Playbook", layout="wide")

# Inject CSS from assets/custom.css (if present)
css_path = os.path.join('assets', 'custom.css')
if os.path.exists(css_path):
    try:
        with open(css_path, 'r', encoding='utf-8') as fh:
            css = fh.read()
            st.markdown(f"""<style>{css}</style>""", unsafe_allow_html=True)
    except Exception:
        pass

# --- Navigation + pages map ---
PAGES = {
    "Home": "pages.home",
    "Myth Buster": "pages.myths",
    "Investors": "pages.investors",
    "Deal Explorer": "pages.deals",
    "Equity Calculator": "pages.equity",
    "Trends & Insights": "pages.trends",
    "About / Methodology": "pages.about"
}

# --- Header (title + CTA) ---
def render_header():
    col1, col2 = st.columns([4,1])
    with col1:
        st.markdown("<h1 style='margin:0;padding:0'>Shark Tank India — Data, Deals & VC Playbook</h1>", unsafe_allow_html=True)
        st.markdown("<div style='color:gray;margin-top:0.2rem'>Interactive analytics, investor playbook & reproducible SQL bank</div>", unsafe_allow_html=True)
    with col2:
        report_url = "https://example.com/your-case-study.pdf"
        st.markdown(f'<a href="{report_url}" target="_blank"><button class="big-cta">Open Case Study</button></a>', unsafe_allow_html=True)

render_header()
st.markdown("---")

# --- Sidebar: navigation + global controls ---
nav_request = st.session_state.get("navigate_to", None)
nav_page_default_index = 0
page_keys = list(PAGES.keys())
if nav_request and isinstance(nav_request, dict):
    req_page = nav_request.get("page")
    if req_page in page_keys:
        nav_page_default_index = page_keys.index(req_page)

st.sidebar.title("Navigation")
selection = st.sidebar.radio("Go to", page_keys, index=nav_page_default_index)

# Global controls (passed as filters)
st.sidebar.markdown("### Global Controls")
season = st.sidebar.selectbox("Season", ["All", "Season 1", "Season 2", "Season 3", "Season 4"], index=0)
view_sql = st.sidebar.checkbox("View SQL", value=False)
quick_search = st.sidebar.text_input("Quick search (company / founder / investor)", value="")

filters = {"season": season, "view_sql": view_sql, "quick_search": quick_search}

if nav_request:
    quick_select = nav_request.get("quick_select_investor")
    if quick_select:
        st.session_state["quick_select_investor"] = quick_select
    st.session_state["navigate_to"] = None

# --- Load & run page module ---
module_path = PAGES[selection]
module = import_module(module_path)
page_func_name = f"page_{module_path.split('.')[-1]}"
page_func = getattr(module, page_func_name, None)
if page_func:
    page_func(filters)
else:
    st.error(f"Page function {page_func_name} not found in module {module_path}")

# --- Footer (data sources, last refresh, links) ---
st.markdown("---")
with st.container():
    col1, col2 = st.columns([3,1])
    with col1:
        st.markdown("**Data sources:** Kaggle datasets — Thirumani (Season 1–4), KGopal02 S1S2.  ")
        st.markdown("[Kaggle: Large dataset](https://www.kaggle.com/datasets/thirumani/shark-tank-india)  |  [Kaggle: S1S2](https://www.kaggle.com/datasets/kgopal02/shark-tank-india-dataset-season-1-and-season-2)  ")
        st.markdown("[GitHub repo](https://github.com/yourusername/sharktank-app)  |  [LinkedIn](https://www.linkedin.com/in/yourprofile)")
    with col2:
        try:
            last_refresh_df = cached_query("SELECT MAX(original_air_date) AS last_date FROM dbo.deals")
            if not last_refresh_df.empty and last_refresh_df.iloc[0].last_date is not None:
                lr = last_refresh_df.iloc[0].last_date
                st.markdown(f"**Last data date:** {lr}")
            else:
                st.markdown(f"**App loaded:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception:
            st.markdown(f"**App loaded:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")