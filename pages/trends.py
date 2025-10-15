# pages/trends.py
import streamlit as st
from utils import cached_query, format_currency
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# Theme colors (used inline for Plotly/text)
ACCENT = "#9D8C5A"
BG = "#1E2A3A"
TEXT = "#B8B8B8"
MUTED = "#9AA3AC"

def page_trends(filters):
    st.markdown(f"<h1 style='color:{ACCENT}'>Trends & Insights</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='color:{ACCENT}'>Season comparisons, sector growth & VC signals</h3>", unsafe_allow_html=True)

    season = filters.get("season", "All")
    
    # Define parameters for conditional filtering once
    if season == 'All':
        params = tuple()  # Changed from [] to tuple()
        season_filter_sql = "1=1"
    else:
        params = (season,)  # Changed from [season] to (season,)
        season_filter_sql = "season = %s"


    # # If season is a specific value, we pass a list containing that value
    # if season == 'All':
    #     params = []
    #     season_filter_sql = "1=1"
    # else:
    #     params = [season]
    #     season_filter_sql = "season = %s" # Positional placeholder

    # --- Helpers ---
    def format_lakhs(val):
        """Format numeric as lakhs; 100 L = 1 Cr. Keeps strings safe."""
        try:
            if val is None or (isinstance(val, float) and np.isnan(val)):
                return "-"
            v = float(val)
            if v == 0:
                return "0 L"
            if v >= 100:
                crores = v / 100.0
                return f"{crores:.2f} Cr ({int(round(v)):,} L)"
            if v.is_integer():
                return f"{int(v):,} L"
            return f"{v:,.2f} L"
        except Exception:
            return str(val)

    def normalize_investor_list(s):
        """Turn a possibly combined investor string into a cleaned list of investor names."""
        if s is None:
            return []
        # split on comma or semicolon, strip whitespace
        parts = [p.strip() for p in str(s).replace(';', ',').split(',') if p.strip()]
        # preserve order, unique
        out = []
        for p in parts:
            if p not in out:
                out.append(p)
        return out

    # -------------------------
    # Season-over-season KPIs
    # -------------------------
    st.markdown(f"<h2 style='color:{ACCENT}'>Season-over-season KPIs</h2>", unsafe_allow_html=True)
    sql_season_kpis = f"""
    SELECT COALESCE(season,'Unknown') AS season,
            COUNT(1) AS pitches,
            SUM(CASE WHEN invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS funded_count,
            1.0 * SUM(CASE WHEN invested_amount IS NOT NULL THEN 1 ELSE 0 END) / NULLIF(COUNT(1),0) AS funded_rate,
            AVG(NULLIF(invested_amount,0)) AS avg_ticket,
            SUM(COALESCE(invested_amount,0)) AS total_invested,
            AVG(equity_final) AS avg_equity
    FROM public.deals
    WHERE {season_filter_sql} -- Use the dynamic filter string
    GROUP BY COALESCE(season,'Unknown')
    ORDER BY season;
    """
    try:
        df_kpis = cached_query(sql_season_kpis, params) # Pass params as a tuple/list
        if df_kpis is None or df_kpis.empty:
            st.info("No season KPI data available.")
        else:
            df_kpis = df_kpis.sort_values("season").reset_index(drop=True)
            df_kpis['avg_ticket_prev'] = df_kpis['avg_ticket'].shift(1)
            df_kpis['avg_ticket_pct_change'] = ((df_kpis['avg_ticket'] - df_kpis['avg_ticket_prev']) / df_kpis['avg_ticket_prev']).replace([np.inf, -np.inf], np.nan).fillna(0)

            # Friendly display table with user-friendly column names and 1-based index
            display = pd.DataFrame({
                "Season": df_kpis['season'],
                "Pitches": df_kpis['pitches'].fillna(0).astype(int),
                "Funded deals": df_kpis['funded_count'].fillna(0).astype(int),
                "Funded rate": df_kpis['funded_rate'],
                "Avg ticket (L)": df_kpis['avg_ticket'],
                "Avg ticket % change": df_kpis['avg_ticket_pct_change'],
                "Total invested (L)": df_kpis['total_invested'],
                "Avg equity (%)": df_kpis['avg_equity']
            })

            # formatting
            display['Funded rate'] = display['Funded rate'].apply(lambda x: f"{x:.1%}" if pd.notnull(x) else "-")
            display['Avg ticket (L)'] = display['Avg ticket (L)'].apply(lambda x: format_lakhs(x) if pd.notnull(x) else "-")
            display['Avg ticket % change'] = display['Avg ticket % change'].apply(lambda x: f"{x:.1%}" if pd.notnull(x) else "-")
            display['Total invested (L)'] = display['Total invested (L)'].apply(lambda x: format_lakhs(x) if pd.notnull(x) else "-")
            display['Avg equity (%)'] = display['Avg equity (%)'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "-")

            display.index = range(1, len(display) + 1)
            st.dataframe(display, use_container_width=True)

            st.write("**What this shows:** Season-level KPIs so you can quickly see pitch count, funded deals, funded rate, average ticket size and where capital concentrated across seasons.")

            # Bar chart: avg deal size by season (numeric values used, labeled in L)
            # For plotting we need numeric avg_ticket; fillna with 0
            fig = px.bar(df_kpis, x='season', y='avg_ticket', title='Average deal size by season (L)')
            fig.update_traces(marker_color=ACCENT)
            # annotate percent change labels
            for i, r in df_kpis.iterrows():
                pct = r['avg_ticket_pct_change']
                fig.add_annotation(x=r['season'], y=max(0, (r['avg_ticket'] or 0)), text=f"{pct:.1%}", showarrow=False, yshift=12, font=dict(color=TEXT))
            fig.update_layout(
                yaxis_title='Avg deal size (L)',
                xaxis_title='Season',
                xaxis_tickangle=-30,
                height=420,
                paper_bgcolor=BG,
                plot_bgcolor=BG,
                font=dict(color=TEXT)
            )
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error("Failed to load season KPIs: " + str(e))

    st.markdown("---")

    # -------------------------
    # Sector x Season heatmap
    # -------------------------
    st.markdown(f"<h2 style='color:{ACCENT}'>Sector & Product Analytics</h2>", unsafe_allow_html=True)
    try:
        sql_sector_season = f"""
        SELECT COALESCE(sector,'Unknown') AS sector, COALESCE(season,'Unknown') AS season, COUNT(1) AS deals_count
        FROM public.deals
        WHERE {season_filter_sql} -- Use the dynamic filter string
        GROUP BY COALESCE(sector,'Unknown'), COALESCE(season,'Unknown')
        ORDER BY sector, season;
        """
        df_ss = cached_query(sql_sector_season, params) # Pass params as a tuple/list
        if df_ss is None or df_ss.empty:
            st.info("No sector-season data available.")
        else:
            pivot = df_ss.pivot_table(index='sector', columns='season', values='deals_count', fill_value=0)
            pivot['total'] = pivot.sum(axis=1)
            pivot = pivot.sort_values('total', ascending=False).head(30).drop(columns=['total'])
            fig = px.imshow(pivot.values, x=pivot.columns, y=pivot.index, aspect="auto",
                             color_continuous_scale='Blues', title="Sector × Season — deal counts (top 30)")
            fig.update_layout(height=600, margin=dict(l=120), paper_bgcolor=BG, plot_bgcolor=BG, font=dict(color=TEXT))
            st.plotly_chart(fig, use_container_width=True)
            st.write("**What this heatmap shows:** Rows are sectors and columns are seasons. Darker cells mean more deals — use it to spot sector momentum across seasons.")
    except Exception as e:
        st.warning("Sector-season heatmap issue: " + str(e))

    st.markdown("---")

    # -------------------------
    # Product vs Service split
    # -------------------------

    # -------------------------
    # Product vs Service split
    # -------------------------
    st.markdown(f"<h3 style='color:{ACCENT}'>Product vs Service split</h3>", unsafe_allow_html=True)
    try:
        # FIX: Escape literal '%' characters with '%%' to prevent Python's DB-API from misinterpreting them
        sql_prod_service = f"""
        SELECT
          CASE
            WHEN LOWER(sector) LIKE '%%food%%' OR LOWER(sector) LIKE '%%fashion%%' OR LOWER(sector) LIKE '%%beauty%%'
                 OR LOWER(sector) LIKE '%%fmcg%%' OR LOWER(sector) LIKE '%%retail%%' OR LOWER(sector) LIKE '%%consumer%%' THEN 'Product'
            WHEN LOWER(sector) LIKE '%%edu%%' OR LOWER(sector) LIKE '%%service%%' OR LOWER(sector) LIKE '%%health%%' OR LOWER(sector) LIKE '%%consult%%' OR LOWER(sector) LIKE '%%logistic%%' THEN 'Service'
            ELSE 'Other'
          END AS product_service,
          COUNT(1) AS deals_count,
          SUM(COALESCE(invested_amount,0)) AS total_invested,
          AVG(NULLIF(invested_amount,0)) AS avg_ticket
        FROM public.deals
        WHERE {season_filter_sql} -- Use the dynamic filter string
        GROUP BY
          CASE
            WHEN LOWER(sector) LIKE '%%food%%' OR LOWER(sector) LIKE '%%fashion%%' OR LOWER(sector) LIKE '%%beauty%%'
                 OR LOWER(sector) LIKE '%%fmcg%%' OR LOWER(sector) LIKE '%%retail%%' OR LOWER(sector) LIKE '%%consumer%%' THEN 'Product'
            WHEN LOWER(sector) LIKE '%%edu%%' OR LOWER(sector) LIKE '%%service%%' OR LOWER(sector) LIKE '%%health%%' OR LOWER(sector) LIKE '%%consult%%' OR LOWER(sector) LIKE '%%logistic%%' THEN 'Service'
            ELSE 'Other'
          END;
        """
        df_ps = cached_query(sql_prod_service, params) # Pass params as a tuple/list
        
        if df_ps is None or df_ps.empty:
            st.info("Product/service mapping returned no rows.")
        else:
            if not df_ps.empty:
                # convert numeric columns to float to avoid Decimal issues
                if 'total_invested' in df_ps.columns:
                    df_ps['total_invested'] = df_ps['total_invested'].apply(lambda x: float(x) if x is not None else 0.0)
                if 'avg_ticket' in df_ps.columns:
                    df_ps['avg_ticket'] = df_ps['avg_ticket'].apply(lambda x: float(x) if x is not None else 0.0)

                fig = px.pie(df_ps, names='product_service', values='deals_count', title='Product vs Service share (by deals)')
                st.plotly_chart(fig, use_container_width=True)
                # show numeric totals as table, formatted
                df_ps_disp = df_ps.copy()
                if 'total_invested' in df_ps_disp.columns:
                    df_ps_disp['total_invested'] = df_ps_disp['total_invested'].apply(lambda v: format_currency(v) if v is not None else "-")
                st.dataframe(df_ps_disp)
            # END OF REPLACEMENT SNIPPET
            st.write("**What this tells a founder:** whether the show tilts toward product-heavy or service-heavy startups — useful when positioning your pitch.")
    except Exception as e:
        st.warning("Product/service split issue: " + str(e))

    st.markdown("---")

    # -------------------------
    # Top investors: compute robustly by splitting combined names and aggregating in Python
    # -------------------------
    
    st.markdown(f"<h3 style='color:{ACCENT}'>Top Investors</h3>", unsafe_allow_html=True)
    try:
        # Fetch raw investor rows joined with deal invested_amount and deal id
        
        # Fetch raw investor rows joined with deal invested_amount and deal id
        inv_raw = cached_query(f"""
            SELECT di.investor AS investor_raw, 
                COALESCE(d.invested_amount,0) AS invested_amount, 
                d.staging_id AS deal_id
            FROM public.deal_investors di
            JOIN public.deals d ON di.staging_id = d.staging_id
            WHERE d.invested_amount IS NOT NULL
            -- Apply season filter if selected (only needed if All isn't selected)
            AND {season_filter_sql};
        """, params) # Pass params as a tuple/list
                
        # Original plan: explode combined investor strings into individual names
        if inv_raw is None or inv_raw.empty:
            st.info("No investor data available.")
        else:
            # FIX: The original code expected 'investor_raw', 'invested_amount', and 'deal_id'
            # Now we continue with Python logic using these column names:
            rows = []
            for _, r in inv_raw.iterrows():
                # FIX: Use 'investor_raw' column name which is now returned by the SQL
                invs = normalize_investor_list(r['investor_raw'])
                for inv in invs:
                    rows.append({'investor': inv, 'invested_amount': r['invested_amount'], 'deal_id': r['deal_id']})
            inv_exp = pd.DataFrame(rows)

            # aggregate totals per investor
            inv_total = inv_exp.groupby('investor', as_index=False).agg(total_invested=('invested_amount','sum'))
            # CONVERSION FIX: Convert from Lakhs to Crores (and ensure numeric type)
            inv_total['total_invested'] = inv_total['total_invested'].astype(float) / 100.0
            
            inv_total = inv_total.sort_values('total_invested', ascending=False).head(15).reset_index(drop=True)
            # FIX: Change (L) to (Cr) in the auxiliary column name
            inv_total['Total invested (Cr)'] = inv_total['total_invested'].apply(lambda x: float(x))
            inv_total.index = range(1, len(inv_total) + 1)

            # aggregate deal counts per investor (unique deals)
            inv_deals = inv_exp.groupby('investor').deal_id.nunique().reset_index(name='deals_cnt')
            inv_deals = inv_deals.sort_values('deals_cnt', ascending=False).head(15).reset_index(drop=True)
            inv_deals.index = range(1, len(inv_deals) + 1)

            # Plot total invested
            # FIX: Change (L) to (Cr) in the title and y-axis label
            fig1 = px.bar(inv_total, x='investor', y='total_invested', title='Top investors by Total invested (Cr)')
            fig1.update_traces(marker_color=ACCENT)
            fig1.update_layout(xaxis_tickangle=-45, height=420, yaxis_title='Total invested (Cr)', paper_bgcolor=BG, plot_bgcolor=BG, font=dict(color=TEXT))
            st.plotly_chart(fig1, use_container_width=True)
            # Plot deals count (NO CHANGE)
            fig2 = px.bar(inv_deals, x='investor', y='deals_cnt', title='Top investors by Deal count')
            fig2.update_layout(xaxis_tickangle=-45, height=420, yaxis_title='Deals (count)', paper_bgcolor=BG, plot_bgcolor=BG, font=dict(color=TEXT))
            st.plotly_chart(fig2, use_container_width=True)
    except Exception as e:
        st.warning("Top investors visuals issue: " + str(e))

    st.markdown("---")

    # -------------------------
    # Ticket size distributions
    # -------------------------
    st.markdown(f"<h3 style='color:{ACCENT}'>Ticket Size Distributions</h3>", unsafe_allow_html=True)
    try:
        dd = cached_query("SELECT invested_amount FROM public.deals WHERE invested_amount IS NOT NULL")
        if dd is None or dd.empty:
            st.info("No invested amount values available.")
        else:
            # Create a new DataFrame for the violin plot with data converted to Crores
            dd_cr = dd.copy()
            dd_cr['invested_amount_cr'] = dd_cr['invested_amount'].astype(float) / 100.0

            col_hist, col_violin = st.columns(2)
            with col_hist:
                # Histogram (NO CHANGE - uses original dd and (L) labels)
                fig_h = px.histogram(dd, x='invested_amount', nbins=50, title='Distribution of invested amounts')
                fig_h.update_layout(xaxis_title='Invested amount (L)', yaxis_title='Number of deals', height=420, paper_bgcolor=BG, plot_bgcolor=BG, font=dict(color=TEXT))
                st.plotly_chart(fig_h, use_container_width=True)
            with col_violin:
                # Violin plot (FIXED - uses dd_cr and (Cr) labels)
                fig_v = px.violin(dd_cr, y='invested_amount_cr', box=True, points='all', title='Ticket distribution (violin)')
                fig_v.update_layout(yaxis_title='Invested amount (Cr)', height=420, paper_bgcolor=BG, plot_bgcolor=BG, font=dict(color=TEXT)) # Changed (L) to (Cr)
                st.plotly_chart(fig_v, use_container_width=True)
    except Exception as e:
        st.warning("Ticket distribution issue: " + str(e))

    st.markdown("---")

    # -------------------------
    # Advanced VC & Fintech metrics — HHI
    # -------------------------
    st.markdown(f"<h3 style='color:{ACCENT}'>Advanced Metrics</h3>", unsafe_allow_html=True)
    st.markdown(f"<h4 style='color:{ACCENT}'>Investor concentration (HHI) by season</h4>", unsafe_allow_html=True)
    try:
        hhi_sql = """
        WITH inv_sum AS (
        SELECT d.season, inv.investor, SUM(COALESCE(d.invested_amount,0)) AS inv_total
        FROM (
            SELECT staging_id, trim(both ' ' from regexp_split_to_table(investor, E',|;|&|/|\\band\\b')) AS investor
            FROM public.deal_investors
            WHERE investor IS NOT NULL
        ) inv
        JOIN public.deals d ON d.staging_id = inv.staging_id
        GROUP BY d.season, inv.investor
        ), season_totals AS (
        SELECT season, SUM(inv_total) AS season_total FROM inv_sum GROUP BY season
        ), shares AS (
        SELECT i.season, i.investor, i.inv_total, i.inv_total / NULLIF(st.season_total,0) AS share
        FROM inv_sum i JOIN season_totals st ON i.season = st.season
        )
        SELECT season, SUM(POWER(share,2)) AS hhi
        FROM shares
        GROUP BY season
        ORDER BY season;
        """
        df_hhi = cached_query(hhi_sql)
        if df_hhi is None or df_hhi.empty:
            st.info("HHI data not available.")
        else:
            df_hhi['HHI (%)'] = df_hhi['hhi'] * 100
            df_hhi_display = df_hhi.rename(columns={'season':'Season', 'hhi':'HHI'}).copy()
            df_hhi_display['HHI'] = df_hhi_display['HHI'].apply(lambda x: round(x,6))
            df_hhi_display.index = range(1, len(df_hhi_display) + 1)
            st.write("**Herfindahl-Hirschman Index (HHI) per season:** A key metric in finance and economics used to gauge market concentration and competitiveness. <br>"
            "**Formula & Notation:** It's calculated as the sum of the squares of the individual market shares (sᵢ) of all firms in the market: HHI = ∑ sᵢ². <br>"
            "**Interpretation:** Shares are expressed as percentages (e.g., 10% is 10). In a Shark Tank context, if two sharks each did 50% of the deals, the HHI would be 50² + 50² = 5000, indicating high risk.", 
            unsafe_allow_html=True # <-- This is the fix
            )
            st.dataframe(df_hhi_display[['Season','HHI','HHI (%)']], use_container_width=True)
            fig = px.bar(df_hhi_display, x='Season', y='HHI', title='Investor concentration (HHI) by season')
            fig.update_layout(xaxis_title='Season', yaxis_title='HHI (sum of squared shares)', paper_bgcolor=BG, plot_bgcolor=BG, font=dict(color=TEXT))
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning("HHI computation issue: " + str(e))

    st.markdown("---")

    # -------------------------
    # Median ticket growth by sector
    # -------------------------
    st.markdown(f"<h4 style='color:{ACCENT}'>Median ticket growth by sector (season-over-season)</h4>", unsafe_allow_html=True)
    try:
        median_sql = """
        WITH numbered AS (
          SELECT COALESCE(sector,'Unknown') AS sector, COALESCE(season,'Unknown') AS season, invested_amount,
                 ROW_NUMBER() OVER (PARTITION BY COALESCE(sector,'Unknown'), COALESCE(season,'Unknown') ORDER BY invested_amount) AS rn,
                 COUNT(*) OVER (PARTITION BY COALESCE(sector,'Unknown'), COALESCE(season,'Unknown')) AS cnt
          FROM public.deals
          WHERE invested_amount IS NOT NULL
        )
        SELECT sector, season, AVG(CAST(invested_amount AS FLOAT)) AS median_invested
        FROM numbered
        WHERE rn IN ( (cnt+1)/2, (cnt+2)/2 )
        GROUP BY sector, season
        ORDER BY sector, season;
        """
        df_med = cached_query(median_sql)
        if df_med is None or df_med.empty:
            st.info("Median invested data not available.")
        else:
            piv = df_med.pivot(index='sector', columns='season', values='median_invested').fillna(0)
            if piv.shape[1] >= 2:
                first_col = piv.columns[0]
                last_col = piv.columns[-1]
                piv['pct_change'] = np.where(piv[first_col] > 0, (piv[last_col] - piv[first_col]) / piv[first_col], np.nan)
                top_growth = piv.sort_values('pct_change', ascending=False).head(10).reset_index()
                top_growth['pct_change'] = top_growth['pct_change'].apply(lambda v: f"{v:.1%}" if pd.notnull(v) else "-")
                top_growth = top_growth.rename(columns={'sector':'Sector', 'pct_change':'% change (median ticket)'})
                top_growth.index = range(1, len(top_growth) + 1)
                st.dataframe(top_growth[['Sector','% change (median ticket)']], use_container_width=True)
                st.write("**What this shows:** sectors with the largest median-ticket percentage growth across seasons.")
            else:
                st.info("Not enough seasons to compute sector growth.")
    except Exception as e:
        st.warning("Valuation uplift computation issue: " + str(e))

    st.markdown("---")

    # -------------------------
    # Actionable insights (SQL-backed) — cleaned investors & friendly formatting
    # -------------------------
    st.markdown(f"<h3 style='color:{ACCENT}'>Actionable Insights</h3>", unsafe_allow_html=True)
    try:
        top_sector = cached_query("""
            SELECT COALESCE(sector,'Unknown') AS sector, SUM(COALESCE(invested_amount,0)) AS total_invested
            FROM public.deals
            GROUP BY COALESCE(sector,'Unknown')
            ORDER BY total_invested DESC
            LIMIT 1;
        """)
        if top_sector is not None and not top_sector.empty:
            s = top_sector.iloc[0]
            st.metric("Top sector by total invested", f"{s['sector']} — {format_lakhs(s['total_invested'])}")

        # compute investor with highest avg ticket robustly (explode combined names)
        
        # compute investor with highest avg ticket robustly (explode combined names)
        inv_raw = cached_query("""
            SELECT di.investor AS investor_raw, COALESCE(d.invested_amount,0) AS invested_amount, d.staging_id AS deal_id
            FROM public.deal_investors di
            JOIN public.deals d ON di.staging_id = d.staging_id
            WHERE d.invested_amount IS NOT NULL;
         """)
        if inv_raw is not None and not inv_raw.empty:
            rows = []
            for _, r in inv_raw.iterrows():
                invs = normalize_investor_list(r['investor_raw'])
                for inv in invs:
                    rows.append({'investor': inv, 'invested_amount': r['invested_amount'], 'deal_id': r['deal_id']})
            inv_exp = pd.DataFrame(rows)
            inv_avg = inv_exp.groupby('investor', as_index=False).agg(avg_ticket=('invested_amount','mean'))
            inv_avg = inv_avg.sort_values('avg_ticket', ascending=False).reset_index(drop=True)
            if not inv_avg.empty:
                top = inv_avg.iloc[0]
                st.metric("Investor with highest avg ticket", f"{top['investor']} — {format_lakhs(top['avg_ticket'])}")
    except Exception as e:
        st.warning("Could not compute actionable insights: " + str(e))

    st.markdown("---")
    st.write("**Notes & limitations:** The analyses rely on Kaggle-provided fields. Some computations are approximations. See About for ETL assumptions.")
