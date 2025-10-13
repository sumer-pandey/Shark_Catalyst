# app.py
import streamlit as st
from importlib import import_module
from utils import cached_query, set_plotly_theme
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Shark Catalyst - Interactive Analytics Platform for Indian Startup Ecosystem", page_icon="assets/logo.png", layout="wide")

# Apply dark theme styling to all charts and tables
st.markdown("""
    <style>
    /* Make all dataframes/tables match dark theme */
    [data-testid="stDataFrame"], 
    [data-testid="stTable"],
    .dataframe {
        background-color: transparent !important;
    }
    
    /* Plotly charts dark background */
    .js-plotly-plot .plotly,
    .js-plotly-plot .plotly .main-svg {
        background-color: transparent !important;
    }
    
    /* Tables and dataframe cells */
    .dataframe tbody tr,
    .dataframe thead tr {
        background-color: rgba(14, 17, 23, 0.8) !important;
    }
    
    .dataframe th {
        background-color: rgba(14, 17, 23, 0.9) !important;
        color: white !important;
    }
    
    .dataframe td {
        background-color: rgba(28, 31, 38, 0.8) !important;
        color: white !important;
    }
    
    /* Remove white backgrounds from metrics and containers */
    [data-testid="metric-container"],
    [data-testid="stMetricValue"] {
        background-color: transparent !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown(
    """
    <style>
    /* Sidebar background */
    [data-testid="stSidebar"] {
        background-color: #1E2A3A;  /* dark navy background */
        color: #B8B8B8;             /* text color */
    }

    /* Sidebar header and widget text */
    [data-testid="stSidebar"] .css-1d391kg, 
    [data-testid="stSidebar"] .stMarkdown, 
    [data-testid="stSidebar"] .stSelectbox, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] div {
        color: #B8B8B8 !important;
    }

    /* Sidebar scrollbar (optional: for visibility) */
    [data-testid="stSidebar"]::-webkit-scrollbar {
        width: 8px;
    }
    [data-testid="stSidebar"]::-webkit-scrollbar-thumb {
        background-color: #444;
        border-radius: 4px;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# ---- ensure custom css and Material Icons load globally ----

def _load_css():
    try:
        # Preconnect & multiple font links to maximize chance fonts load correctly
        st.markdown("<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>", unsafe_allow_html=True)
        st.markdown("<link href='https://fonts.googleapis.com/css2?family=Material+Icons' rel='stylesheet'>", unsafe_allow_html=True)
        st.markdown("<link href='https://fonts.googleapis.com/css2?family=Material+Icons+Outlined' rel='stylesheet'>", unsafe_allow_html=True)
        st.markdown("<link href='https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined' rel='stylesheet'>", unsafe_allow_html=True)

        # Inline priority rule: ensure icon elements use icon fonts before custom CSS can override
        st.markdown(
            """
            <style>
            .material-icons, .material-icons-outlined, .material-symbols-outlined {
                font-family: 'Material Icons', 'Material Icons Outlined', 'Material Symbols Outlined' !important;
                speak: none;
                font-style: normal;
                font-weight: normal;
                font-variant: normal;
                text-transform: none;
                line-height: 1;
                -webkit-font-smoothing: antialiased;
                -moz-osx-font-smoothing: grayscale;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # Load your project CSS file (assets/custom.css). Load it after inline rule to allow page visuals.
        with open("assets/custom.css", "r", encoding="utf-8") as f:
            css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("assets/custom.css not found — create it at assets/custom.css")
    except Exception as e:
        st.warning("Unable to load custom CSS: " + str(e))


# call once on app start
_load_css()

# Apply Plotly theme (safe call)
try:
    set_plotly_theme()
except Exception:
    pass

# st.set_page_config(page_title="Shark Catalyst - Interactive Analytics Platform for Indian Startup Ecosystem", page_icon="assets/logo.png", layout="wide")

# Inject CSS from assets/custom.css (if present)
css_path = os.path.join('assets', 'custom.css')
if os.path.exists(css_path):
    try:
        with open(css_path, 'r', encoding='utf-8') as fh:
            css = fh.read()
            st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except Exception:
        pass

# Pages map
PAGES = {
    "Home": "pages.home",
    "Myth Buster": "pages.myths",
    "Investor Intelligence": "pages.investors",
    "Deal Explorer": "pages.deals",
    "Financial Modeling": "pages.equity",
    "Trends & Insights": "pages.trends",
    "About": "pages.about",
    "Disclaimer": "pages.disclaimer"
}


# Header: title + CTA
def render_header():
        # --- render centered main logo at top of page ---
    logo_path = "assets/border.png"
    if os.path.exists(logo_path):
        # center via three columns (streamlit-friendly)
        left, mid, right = st.columns([3, 2, 2])
        with mid:
            st.image(logo_path, width=80, caption=None)

    col1, col2 = st.columns([4,1])
    with col1:
        st.markdown("<h1 style='margin:0;padding:0'>Shark Catalyst - Interactive Analytics Platform for Indian Startup Ecosystem</h1>", unsafe_allow_html=True)
        st.markdown("<div style='color:gray;margin-top:0.2rem'>A data-driven deep dive into the business of India's biggest entrepreneurial show - Shark Tank India.<br>Interactive analytics, investor playbook & reproducible SQL bank.</div>", unsafe_allow_html=True)
    # with col2:
    #     report_url = "static/case-study.pdf"
    #     st.markdown(f'<a href="{report_url}" target="_blank"><button class="big-cta">Open Case Study</button></a>', unsafe_allow_html=True)

    with col2:
        with open("static/case-study.pdf", "rb") as f:
            st.markdown("""
                <style>
                .stDownloadButton button {
                    background-color: #9D8C5A !important;
                    color: #FFFFFF !important;
                    font-weight: 700 !important;
                }
                .stDownloadButton button p {
                    color: #FFFFFF !important;
                }
                </style>
            """, unsafe_allow_html=True)
            
            st.download_button(
                label="**Open Case Study**",
                data=f,
                file_name="Shark-Catalyst-Case-Study.pdf",
                mime="application/pdf",
                use_container_width=True
            )


render_header()
st.markdown("---")

# Read possible navigation request placed by pages to jump (and set defaults)
nav_request = st.session_state.get("navigate_to", None)
nav_page_default_index = 0
page_keys = list(PAGES.keys())
if nav_request and isinstance(nav_request, dict):
    req_page = nav_request.get("page")
    if req_page in page_keys:
        nav_page_default_index = page_keys.index(req_page)

# Check if user wants to go to disclaimer
if st.session_state.get("go_to_disclaimer", False):
    st.session_state["go_to_disclaimer"] = False
    st.session_state["navigate_to"] = {"page": "Disclaimer"}
    st.rerun()

# Sidebar: navigation + global controls
st.sidebar.markdown("### Menu")


selection = st.sidebar.radio("Go to", page_keys, index=nav_page_default_index)

st.sidebar.markdown("### Global Controls")
season = st.sidebar.selectbox("Season", ["All", "Season 1", "Season 2", "Season 3", "Season 4"], index=0)
view_sql = st.sidebar.checkbox("View SQL", value=False)
# quick_search removed per request — keep empty so pages that read it still work
quick_search = ""

filters = {"season": season, "view_sql": view_sql, "quick_search": quick_search}

# If a page set navigate_to in st.session_state, consume its keys and set them to session_state.
# This allows pages to request programmatic navigation + prefill values (e.g., quick_select_investor, deal_filters_prefill, playground_sql)
if nav_request and isinstance(nav_request, dict):
    # set any keys (except 'page') into session_state so target pages can pick them up
    for k, v in nav_request.items():
        if k == "page":
            continue
        # write into session_state directly
        st.session_state[k] = v
    # clear the request so it doesn't repeat
    st.session_state["navigate_to"] = None

# Dynamically import and run the selected page module
module_path = PAGES[selection]
module = import_module(module_path)
page_func_name = f"page_{module_path.split('.')[-1]}"
page_func = getattr(module, page_func_name, None)
if page_func:
    page_func(filters)
else:
    st.error(f"Page function {page_func_name} not found in module {module_path}")

# Footer
st.markdown("---")
with st.container():
    col1, col2 = st.columns([3,1])
    with col1:
        st.markdown("**Data source:** Kaggle dataset - Thirumani (Shark Tank India).  ")
        st.markdown("[Kaggle: Shark Tank India (Thirumani)](https://www.kaggle.com/datasets/thirumani/shark-tank-india)  ")
        st.markdown("[GitHub repo](https://github.com/being-sumer)  |  [LinkedIn](https://www.linkedin.com/in/sumerpandey/)")
    
    with col2:
        try:
            # FIX: Use PostgreSQL syntax (public.deals) and ensure correct column name
            last_refresh_df = cached_query("SELECT MAX(original_air_date) AS last_date FROM public.deals") 
            if not last_refresh_df.empty and last_refresh_df.iloc[0].last_date is not None:
                lr = last_refresh_df.iloc[0].last_date
                st.markdown(f"**Last data date:** {lr}")
            else:
                st.markdown(f"**App loaded:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception:
            st.markdown(f"**App loaded:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # with col2:
    #     try:
    #         last_refresh_df = cached_query("SELECT MAX(original_air_date) AS last_date FROM dbo.deals")
    #         if not last_refresh_df.empty and last_refresh_df.iloc[0].last_date is not None:
    #             lr = last_refresh_df.iloc[0].last_date
    #             st.markdown(f"**Last data date:** {lr}")
    #         else:
    #             st.markdown(f"**App loaded:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    #     except Exception:
    #         st.markdown(f"**App loaded:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Small project signature (appears at the end of every page)
st.markdown("---")
# st.markdown("<div font-weight: bold;style='font-size:0.95rem;color:#9AA3AC'>Built with accuracy. <br>", unsafe_allow_html=True)
st.markdown("<div font-weight: bold;style='font-size:0.95rem;color:#9AA3AC'>Created by Sumer Pandey, with a commitment to accuracy. <br>", unsafe_allow_html=True)
# st.markdown("<div style='font-size:0.95rem;color:#9AA3AC'>LinkedIn: <a href='https://www.linkedin.com/in/sumerpandey/' target='_blank'>Sumer Pandey</a></div> GitHub: <a href='https://github.com/sumer-pandey' target='_blank'>sumer-pandey</a></div><br>", unsafe_allow_html=True)
st.markdown("<div style='font-size:0.95rem;color:#9AA3AC'><a href='https://www.linkedin.com/in/sumerpandey/' target='_blank'>LinkedIn</a> | <a href='https://github.com/sumer-pandey' target='_blank'>GitHub</a></div><br>", unsafe_allow_html=True)

st.markdown("")

# Added the disclaimer line below the existing project signature
# st.markdown(
#     """
#     <div style='font-size:0.8rem;color:gray;text-align:left;'>
#         "Shark Tank India" is a trademark of Sony Pictures Networks India. This site is for educational purposes only under fair use, with no intent of trademark infringement.
#         <br><a href='/Disclaimer' target='_self'>View full disclaimer</a>
#     </div>
#     """,
#     unsafe_allow_html=True
# )
# Disclaimer with working internal link

st.markdown(
    """
    <div style='font-size:0.8rem;color:gray;text-align:left;'>
        "Shark Tank India" is a trademark of Sony Pictures Networks India. This site is for educational purposes only under fair use, with no intent of trademark infringement.
    </div>
    """,
    unsafe_allow_html=True
)
if st.button("View full disclaimer", key="disclaimer_link"):
    st.session_state["go_to_disclaimer"] = True
    st.rerun()