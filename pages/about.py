# pages/about.py
import streamlit as st
from utils import cached_query, format_currency
import pandas as pd
import os
import plotly.graph_objects as go
import networkx as nx
import textwrap
import re

def _list_sql_files(base_dir="sql"):
    files = []
    if not os.path.exists(base_dir):
        return files
    for root, _, filenames in os.walk(base_dir):
        for fn in sorted(filenames):
            if fn.lower().endswith(".sql"):
                files.append(os.path.join(root, fn))
    return files

def _combine_sql_files(files):
    combined = []
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                combined.append(f"-- FILE: {os.path.relpath(f)}\n")
                combined.append(fh.read())
                combined.append("\n\n")
        except Exception:
            combined.append(f"-- FILE READ ERROR: {f}\n\n")
    return "\n".join(combined)

def _get_clean_investors():
    """
    Return a deduplicated list of investor names by splitting raw lines in
    dbo.deal_investors.investor on common separators (comma, ampersand, slash, semicolon, ' and ').
    This avoids treating "a, b" as one combined investor name.
    """
    names = []
    try:
        df_raw = cached_query("SELECT DISTINCT investor FROM deal_investors WHERE investor IS NOT NULL")
        if not df_raw.empty:
            for raw in df_raw['investor'].dropna().astype(str):
                # split on comma, ampersand, slash, semicolon or the word ' and ' (case-insensitive)
                parts = re.split(r',|&|/|;|\band\b', raw, flags=re.IGNORECASE)
                for p in parts:
                    n = p.strip()
                    if n:
                        names.append(n)
    except Exception:
        # if DB call fails, return empty list (handled by caller)
        return []

    # also attempt to include canonical names from vw_investor_summary if available
    try:
        df_vw = cached_query("SELECT DISTINCT investor FROM vw_investor_summary WHERE investor IS NOT NULL")
        if not df_vw.empty:
            names.extend([x.strip() for x in df_vw['investor'].dropna().astype(str)])
    except Exception:
        pass

    # deduplicate (case-insensitive) and sort
    unique = sorted({n for n in names}, key=lambda s: s.lower())
    return unique


def schema_diagram():
    """Render a small schema diagram using networkx + plotly"""
    try:
        G = nx.DiGraph()
        nodes = ["deals", "companies", "founders", "investors", "deal_investors", "episodes", "dim_city"]
        edges = [
            ("companies", "deals"),
            ("episodes", "deals"),
            ("founders", "companies"),
            ("deal_investors", "deals"),
            ("deal_investors", "investors"),
            ("deals", "dim_city")
        ]
        for n in nodes:
            G.add_node(n)
        for a,b in edges:
            G.add_edge(a,b)

        pos = nx.spring_layout(G, seed=42, k=0.7)
        edge_x, edge_y = [], []
        for e in G.edges():
            x0, y0 = pos[e[0]]
            x1, y1 = pos[e[1]]
            edge_x += [x0, x1, None]
            edge_y += [y0, y1, None]

        node_x = [pos[n][0] for n in G.nodes()]
        node_y = [pos[n][1] for n in G.nodes()]
        labels = list(G.nodes())

        edge_trace = go.Scatter(x=edge_x, y=edge_y, mode='lines', line=dict(width=1, color='#888'), hoverinfo='none')
        node_trace = go.Scatter(x=node_x, y=node_y, mode='markers+text', text=labels, textposition="bottom center",
                                marker=dict(size=40, color="#1f77b4"), hoverinfo='text')
        fig = go.Figure(data=[edge_trace, node_trace],
                        layout=go.Layout(title="Schema diagram (logical)", showlegend=False,
                                         xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                                         yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                                         height=420, margin=dict(l=20,r=20,t=40,b=20)))
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.info("Schema diagram could not be rendered (missing networkx or plotting libs). See schema in README.")

def page_about(filters):
    """
    About / Methodology page. Accepts filters (dict) for consistency with other pages.
    """
    st.title("About")
    st.markdown("This page documents datasets, ETL steps, schema, SQL bank, and provides a safe SQL playground for reproducibility and verification.")

    # Dataset summary
    st.header("Dataset summary")
    st.markdown("- **Primary dataset used (Kaggle):**")
    st.markdown("  - Thirumani — Shark Tank India (Season 1–4): https://www.kaggle.com/datasets/thirumani/shark-tank-india")
    st.markdown("")

    col1, col2 = st.columns(2)
    try:
        deals_count_df = cached_query("SELECT COUNT(*) AS c FROM deals")
        deals_count = int(deals_count_df.iloc[0]['c']) if not deals_count_df.empty else 0
        col1.metric("Deals (rows)", f"{deals_count:,}")
    except Exception:
        col1.metric("Deals (rows)", "N/A")

    try:
        inv_count_df = cached_query("SELECT COUNT(*) AS c FROM deal_investors")
        inv_count = int(inv_count_df.iloc[0]['c']) if not inv_count_df.empty else 0
        col2.metric("Deal-Investor rows", f"{inv_count:,}")
    except Exception:
        col2.metric("Deal-Investor rows", "N/A")

    st.markdown("---")
    st.header("ETL & cleaning (summary)")
    st.markdown(textwrap.dedent("""
    - **Source ingestion:** raw CSV files from Kaggle were imported into staging and normalized.
    - **Missing values:** missing numeric fields set to NULL; missing categorical fields set to 'Unknown' where appropriate.
    - **Currency normalization:** parsed textual amounts (lakhs/crores/₹) into numeric INR values; applied consistent units (INR).
    - **Invested amounts:** unified representation across rows; attempted per-investor breakdown where possible (deal_investors table).
    - **Founder counts & genders:** inferred `founder_count` from presenter fields; gender inferred using heuristics on names (documented limitation).
    - **Sector taxonomy:** normalized sector names into a canonical set; some manual remapping applied for clarity.
    - **City normalization:** normalized city names and mapped to `dim_city` for metro/non-metro classification.
    - **Views & stored procs:** derived views (e.g., `vw_investor_summary`, `vw_co_invest_pairs`) and stored procedures (`sp_home_kpis`, etc.) created to encapsulate SQL logic for the app.
    """))

    st.markdown("---")
    st.header("Schema diagram")
    st.markdown("Logical tables and relationships used in the app:")
    schema_diagram()

    st.markdown("## Curated SQL bank")
    st.write(
        "Below are the curated, public SQL files from the project. "
        "These are the *most important* files used across the app (views & stored procedures). "
        "Full internal SQL (helpers, patches) exist in the repo but are not included here."
    )

    # directory that contains the curated SQL files
    SQL_DIR = os.path.join("sql", "sql")

    if not os.path.exists(SQL_DIR):
        st.info("Curated SQL folder not found: " + SQL_DIR)
    else:
        # list only .sql files and show a short excerpt, plus a download button
        files = sorted([f for f in os.listdir(SQL_DIR) if f.lower().endswith(".sql")])
        # Show only the files (not all 27); this directory contains the curated set
        for fname in files:
            path = os.path.join(SQL_DIR, fname)
            
            # Display the file name as a header
            st.markdown(f"### {fname}")

            # allow download of the full file
            with open(path, "rb") as fh:
                sql_bytes = fh.read()
            st.download_button(label=f"Download {fname}", data=sql_bytes, file_name=fname, mime="text/sql")

    st.markdown("---")
    st.header("SQL Playground (safe list)")
    st.markdown("Choose a preloaded query, optionally edit it (enable checkbox), provide the parameters below, and run. **Safety rules:** only `SELECT`, `WITH` or `EXEC dbo.` calls allowed; destructive statements are blocked. Results are limited by row cap.")

    PRELOADED = {
        "Top sectors by invested (top N)": {
            "sql": "SELECT COALESCE(sector,'Unknown') AS sector, COUNT(*) AS deals, SUM(COALESCE(invested_amount,0)) AS total_invested FROM deals GROUP BY COALESCE(sector,'Unknown') ORDER BY total_invested DESC LIMIT 100;",
            "params": []
        },
        "Top investors (by deals)": {
            "sql": "SELECT di.investor, COUNT(*) AS deals_count, SUM(COALESCE(d.invested_amount,0)) AS total_invested FROM deal_investors di JOIN deals d ON di.deal_id = d.id GROUP BY di.investor ORDER BY deals_count DESC LIMIT 100;",
            "params": []
        },
        "Recent deals (top 100)": {
            "sql": "SELECT id, company, season, original_air_date, asked_amount, invested_amount, equity_final, pitchers_city, sector FROM deals ORDER BY original_air_date DESC LIMIT 100;",
            "params": []
        },
        
        "Investor equity distribution (median & quartiles)": {
            "sql": (
                "SELECT DISTINCT di.investor,\n"
                "  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY d.equity_final) OVER (PARTITION BY di.investor) AS median_equity,\n"
                "  PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY d.equity_final) OVER (PARTITION BY di.investor) AS q1,\n"
                "  PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY d.equity_final) OVER (PARTITION BY di.investor) AS q3\n"
                "FROM deal_investors di\n"
                "JOIN deals d ON di.deal_id = d.id\n"
                "WHERE di.investor = :investor;"
            ),
            "params": ["investor"]
        }
    }

    choice = st.selectbox("Pick a preloaded query", list(PRELOADED.keys()))
    editable = st.checkbox("Allow editing SQL (careful)", value=False)
    selected = PRELOADED[choice]
    sql_text = selected["sql"]

    # --- PREFILL SUPPORT: if another page set playground_sql/playground_params in session_state, pick it up ---
    pre_sql = None
    pre_params = None
    if "playground_sql" in st.session_state:
        pre_sql = st.session_state.pop("playground_sql")
    if "playground_params" in st.session_state:
        pre_params = st.session_state.pop("playground_params")

    if pre_sql:
        sql_text = pre_sql
        editable = True  # allow user to edit the prefilled SQL

    if editable:
        sql_text = st.text_area("SQL (editable)", value=sql_text, height=200)
    else:
        st.code(sql_text)

    # parameter inputs (basic and merged with pre_params if present)
    params = {}
    if "season" in selected["params"] or (pre_params and "season" in pre_params):
        default_season = pre_params.get("season") if pre_params and "season" in pre_params else "All"
        params["season"] = st.selectbox("Season parameter", ["All","Season 1","Season 2","Season 3","Season 4"], index=0 if default_season=="All" else 0)
    if "investor" in selected["params"] or (pre_params and "investor" in pre_params):
        investors_list = _get_clean_investors()
        investors_list = []
        # try:
        #     # Read distinct raw investor strings
        #     df_raw = cached_query("SELECT DISTINCT investor FROM dbo.deal_investors WHERE investor IS NOT NULL")
        #     names = []
        #     if not df_raw.empty:
        #         for raw in df_raw['investor'].dropna().astype(str):
        #             # Split on comma, ampersand, slash, semicolon, or the word 'and' (case-insensitive)
        #             parts = re.split(r',|&|/|;|\band\b', raw, flags=re.IGNORECASE)
        #             for p in parts:
        #                 name = p.strip()
        #                 if name:
        #                     names.append(name)
        #     # Deduplicate and sort case-insensitively
        #     investors_list = sorted({n for n in names}, key=lambda s: s.lower())
        # except Exception:
        #     investors_list = []


        default_inv = pre_params.get("investor") if pre_params and "investor" in pre_params else ""
        params["investor"] = st.selectbox("Investor parameter", [""] + investors_list, index=(0 if default_inv=="" else ([""] + investors_list).index(default_inv)))

    # merge pre_params into params (pre_params takes precedence)
    if pre_params:
        for k, v in pre_params.items():
            params[k] = v

    max_rows = st.number_input("Max rows to return (client-side limit)", min_value=10, max_value=5000, value=1000, step=10)

    def _is_sql_safe(sql_str):
        s = sql_str.strip().lower()
        if s.startswith("select") or s.startswith("with"):
        # if s.startswith("select") or s.startswith("with") or (s.startswith("exec") and "dbo." in s):
            pass
        else:
            return False, "Only SELECT / WITH / EXEC dbo. statements are allowed."
        blacklist = ["insert ", "update ", "delete ", "drop ", "create ", "alter ", "truncate ", "merge ", "exec sp_", "sp_executesql"]
        for kw in blacklist:
            if kw in s:
                return False, f"Disallowed keyword found in query: {kw.strip()}"
        return True, ""

    if st.button("Run query"):
        ok, reason = _is_sql_safe(sql_text)
        if not ok:
            st.error("Query blocked for safety: " + reason)
        else:
            try:
                df = cached_query(sql_text, params)
                rows = len(df)
                st.success(f"Query executed — {rows} rows returned (showing up to {int(max_rows)} rows).")
                if rows > 0:
                    st.dataframe(df.head(int(max_rows)))
                    csv_bytes = df.to_csv(index=False).encode('utf-8')
                    st.download_button("Download query results (CSV)", data=csv_bytes, file_name="query_results.csv", mime="text/csv")
            except Exception as e:
                st.error("Query execution failed: " + str(e))

    st.markdown("---")
    st.header("Assumptions & limitations")
    st.markdown(textwrap.dedent("""
    - Some fields are missing or noisy in the Kaggle datasets (revenue, gross margin, EBITDA). We use available fields only and mark missing values as NULL.  
    - Founder gender is inferred from names using heuristics — this is imperfect and flagged in the dataset.  
    - Season/episode alignment is based on the Kaggle data and may not cover every aired pitch.  
    - Comparable deals are nearest by ticket + sector; do not substitute for full diligence.  
    - This analysis is exploratory and aimed at practitioner insights, not legal or investment advice.
    """))
