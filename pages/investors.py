# pages/investors.py
import streamlit as st
from utils import cached_query, format_currency
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# network libs (optional click support)
try:
    from streamlit_plotly_events import plotly_events
    PLOTLY_EVENTS_AVAILABLE = True
except Exception:
    PLOTLY_EVENTS_AVAILABLE = False

import networkx as nx

def get_investors_list():
    """
    Return a cleaned, deduplicated list of investor names.

    Fix:
    - Properly split multiple names that appear in a single cell (e.g. "Azhar Iqubal,Radhika Gupta").
    - Split on comma, &, /, ;, ' and '.
    - Normalize whitespace and casing.
    """

    names = []

    # 1) Pull raw investor strings from deal_investors
    try:
        df_raw = cached_query("SELECT DISTINCT investor FROM public.deal_investors WHERE investor IS NOT NULL")
        if not df_raw.empty:

# NEW CODE:
            for raw in df_raw['investor'].dropna().astype(str):
                parts = re.split(r'\s*,\s*|\s*&\s*|\s*/\s*|\s*;\s*|\s*\band\b\s*', raw, flags=re.IGNORECASE)
                for p in parts:
                    name = p.strip()
                    # normalize multiple spaces, capitalize first letters
                    if name:
                        cleaned = re.sub(r'\s+', ' ', name).strip()
                        names.append(cleaned)
    except Exception:
        pass

    # 2) Add names from vw_investor_summary (canonical list)
    try:
        df_vw = cached_query("SELECT DISTINCT investor FROM public.vw_investor_summary WHERE investor IS NOT NULL")
        if not df_vw.empty:
            for raw in df_vw['investor'].dropna().astype(str):
                cleaned = re.sub(r'\s+', ' ', raw.strip())
                if cleaned:
                    names.append(cleaned)
    except Exception:
        pass

    # 3) Deduplicate case-insensitively and sort
    unique_names = sorted({n for n in names if n}, key=lambda s: s.lower())

    return unique_names


def page_investors(filters):
    st.title("Investor Intelligence")


    # allow pre-selection via session_state (set by other pages)
    investors = get_investors_list()
    default_index = 0
    quick_select = st.session_state.get("quick_select_investor")
    if quick_select and quick_select in investors:
        default_index = investors.index(quick_select)

    investor = st.selectbox("Choose investor", investors, index=default_index)

    # clear quick select after reading
    if "quick_select_investor" in st.session_state:
        try:
            del st.session_state["quick_select_investor"]
        except Exception:
            pass

    if not investor:
        st.info("No investors found.")
        return

    season = filters.get("season", "All")

        # --- Helper: format amounts assuming input numbers are in lakhs (L) ---
    def format_lakhs(val):
        """
        val: numeric (assumed to represent lakhs)
        Returns:
          - for <100 L: "12,345 L"
          - for >=100 L: "12.34 Cr (12,345 L)"
        """
        try:
            if val is None:
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


    # --- Summary KPIs (including median equity and top sector) ---
    
    try:
        # Attempt to display the precomputed view if available (non-authoritative)
        try:
            summary = cached_query("SELECT * FROM public.vw_investor_summary WHERE investor = %s", (investor,))
        except Exception:
            summary = None

        # Compute accurate per-investor metrics directly (preferred): use di.invested_amount when present,
        # else split d.invested_amount evenly across the number of investors for that deal.
        accurate_sql = """
        WITH inv_counts AS (
            SELECT staging_id, COUNT(*) AS cnt
            FROM public.deal_investors
            GROUP BY staging_id
        )
        SELECT
            COUNT(DISTINCT di.staging_id) AS deals_count,
            SUM(
                COALESCE(
                    di.invested_amount,
                    -- fall back to fair share: deal invested_amount divided by number of investors
                    CASE WHEN inv.cnt IS NOT NULL AND inv.cnt > 0 THEN d.invested_amount::numeric / inv.cnt ELSE d.invested_amount::numeric END
                )
            ) AS total_invested,
            AVG(
                COALESCE(
                    di.invested_amount,
                    CASE WHEN inv.cnt IS NOT NULL AND inv.cnt > 0 THEN d.invested_amount::numeric / inv.cnt ELSE d.invested_amount::numeric END
                )
            ) AS avg_ticket,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY d.equity_final) AS median_equity
        FROM public.deal_investors di
        JOIN public.deals d ON di.staging_id = d.staging_id
        LEFT JOIN inv_counts inv ON inv.staging_id = d.staging_id
        WHERE trim(di.investor) = %s
        ;
        """
        # run accurate calculation (positional params: investor)
        acc = cached_query(accurate_sql, (investor,))

        # prefer the accurate numbers; if accurate query failed, fall back to view results (if any)
        if acc is not None and not acc.empty:
            ar = acc.iloc[0]
            deals_cnt = int(ar.deals_count or 0)
            total_inv_val = float(ar.total_invested or 0.0)
            avg_ticket_val = float(ar.avg_ticket or 0.0)
            median_eq = float(ar.median_equity) if (ar.median_equity is not None) else None
        elif summary is not None and not summary.empty:
            # fallback to the view (if available)
            r = summary.iloc[0]
            deals_cnt = int(r.deals_count or 0)
            # view may contain string or Decimal; convert safely
            try:
                total_inv_val = float(r.total_invested or 0.0)
            except Exception:
                total_inv_val = 0.0
            try:
                avg_ticket_val = float(r.avg_ticket or 0.0)
            except Exception:
                avg_ticket_val = 0.0
            median_eq = r.median_invested_equity if not pd.isnull(r.median_invested_equity) else None
        else:
            deals_cnt = 0
            total_inv_val = 0.0
            avg_ticket_val = 0.0
            median_eq = None

        # Now render the KPI columns (same layout as before)
        cols = st.columns(6)
        cols[0].markdown(f"<div style='color:#9D8C5A;font-weight:700'>Deals Invested</div>", unsafe_allow_html=True)
        cols[0].markdown(f"<div style='white-space:normal;line-height:1.05'>{deals_cnt}</div>", unsafe_allow_html=True)

        cols[1].markdown(f"<div style='color:#9D8C5A;font-weight:700'>Total Invested</div>", unsafe_allow_html=True)
        cols[1].markdown(f"<div style='white-space:normal;line-height:1.05'>{format_lakhs(total_inv_val)}</div>", unsafe_allow_html=True)

        cols[2].markdown(f"<div style='color:#9D8C5A;font-weight:700'>Average Ticket (L)</div>", unsafe_allow_html=True)
        cols[2].markdown(f"<div style='white-space:normal;line-height:1.05'>{format_lakhs(avg_ticket_val)}</div>", unsafe_allow_html=True)

        cols[3].markdown(f"<div style='color:#9D8C5A;font-weight:700'>Median Equity (%)</div>", unsafe_allow_html=True)
        cols[3].markdown(f"<div style='white-space:normal;line-height:1.05'>{(f'{median_eq:.2f}%' if median_eq is not None else '-')}</div>", unsafe_allow_html=True)

        # Most invested sector: keep using the view value if available, else compute quickly
        top_sector = None
        try:
            if summary is not None and not summary.empty and (not pd.isnull(summary.iloc[0].top_sector)):
                top_sector = summary.iloc[0].top_sector
            else:
                top_sector_q = """
                SELECT COALESCE(d.sector,'Unknown') AS sector, SUM(
                    COALESCE(
                        di.invested_amount,
                        CASE WHEN inv.cnt IS NOT NULL AND inv.cnt > 0 THEN d.invested_amount::numeric / inv.cnt ELSE d.invested_amount::numeric END
                    )
                ) AS total_inv
                FROM public.deal_investors di
                JOIN public.deals d ON di.staging_id = d.staging_id
                LEFT JOIN (SELECT staging_id, COUNT(*) AS cnt FROM public.deal_investors GROUP BY staging_id) inv ON inv.staging_id = d.staging_id
                WHERE trim(di.investor) = %s
                GROUP BY COALESCE(d.sector,'Unknown')
                ORDER BY total_inv DESC
                LIMIT 1;
                """
                top_df = cached_query(top_sector_q, (investor,))
                if top_df is not None and not top_df.empty:
                    top_sector = top_df.iloc[0].sector
        except Exception:
            top_sector = None

        cols[4].markdown(f"<div style='color:#9D8C5A;font-weight:700'>Most Invested Sector</div>", unsafe_allow_html=True)
        cols[4].markdown(f"<div style='white-space:normal;line-height:1.05'>{top_sector or 'N/A'}</div>", unsafe_allow_html=True)
        cols[5].write(" ")

    except Exception as e:
        st.warning("Could not load investor summary: " + str(e))

    st.markdown("---")

    # --- Time series: deals over time for this investor ---
    
    try:
        
        ts_sql = """
        SELECT 
          d.season,
          d.episode_number,
          COUNT(*) AS deals_count,
          SUM(COALESCE(d.invested_amount,0)) AS total_invested
        FROM public.deal_investors di
        JOIN public.deals d ON di.staging_id = d.staging_id
        WHERE trim(di.investor) = %s
          AND (%s = 'All' OR d.season = %s)
        GROUP BY d.season, d.episode_number
        ORDER BY d.season, d.episode_number;
        """
        ts_df = cached_query(ts_sql, (investor, season, season))
        
        st.subheader("Deals over time")
        if not ts_df.empty:
            # Aggregate to season-level (sum invested, sum deals_count)
            season_summary = ts_df.groupby('season', sort=False).agg({
                'total_invested': 'sum',
                'deals_count': 'sum'
            }).reset_index().sort_values('season').reset_index(drop=True)

            # CONVERSION FIX: Convert 'total_invested' to float before division.
            # This resolves the 'decimal.Decimal' and 'float' unsupported operand issue.
            season_summary['total_invested'] = season_summary['total_invested'].astype(float) / 100.0

            # uniform x positions so ticks don't crowd (10,20,30...)
            season_summary['x_pos'] = [(i + 1) * 10 for i in range(len(season_summary))]

            fig_ts = px.line(season_summary, x='x_pos', y='total_invested', markers=True,
                             title=f"{investor} — Total Amount Invested by Season")
            fig_ts.update_traces(mode='lines+markers', marker=dict(size=10, color='#9D8C5A'))
            # annotate number of deals above markers
            for _, r in season_summary.iterrows():
                fig_ts.add_annotation(x=r['x_pos'], y=r['total_invested'], text=f"{int(r['deals_count'])} deals", showarrow=False, yshift=8)

            # friendly axis labels and season tick labels
            fig_ts.update_layout(
                xaxis=dict(tickmode='array', tickvals=season_summary['x_pos'], ticktext=season_summary['season'], title='Season'),
                yaxis=dict(title='Total Amount Invested (Cr)'),
                height=360,
                margin=dict(b=120)
            )
            # match background / theme for readability
            fig_ts.update_layout(paper_bgcolor='#1E2A3A', plot_bgcolor='#1E2A3A', font=dict(color='#B8B8B8'))

            # set y-range to start at 0 if positive numbers present
            
            yvals = season_summary['total_invested'].fillna(0).astype(float)
            if yvals.max() > 0:
                fig_ts.update_yaxes(range=[max(0, yvals.min() - 0.1 * yvals.max()), yvals.max() * 1.05])
            st.plotly_chart(fig_ts, use_container_width=True)
            
            # yvals = season_summary['total_invested'].fillna(0)
            # if yvals.max() > 0:
            #     fig_ts.update_yaxes(range=[max(1, float(yvals.min() - 0.1 * yvals.max())), float(yvals.max() * 1.05)])
            # st.plotly_chart(fig_ts, use_container_width=True)
        else:
            st.info("No time series data for this investor.")
    except Exception as e:
        st.warning("Time series load issue: " + str(e))

    # --- Sector distribution (donut) ---
    try:
        
        sectors_sql = """
        SELECT COALESCE(d.sector,'Unknown') AS sector, COUNT(*) AS deals_count, SUM(COALESCE(d.invested_amount,0)) AS total_invested
        FROM public.deal_investors di
        JOIN public.deals d ON di.staging_id = d.staging_id
        WHERE trim(di.investor) = %s
          AND (%s = 'All' OR d.season = %s)
        GROUP BY COALESCE(d.sector,'Unknown')
        ORDER BY total_invested DESC;
        """
        sector_df = cached_query(sectors_sql, (investor, season, season))
        st.subheader("Sector distribution")
        if not sector_df.empty:
            fig = px.pie(sector_df.head(12), names="sector", values="total_invested", hole=0.45, title="Top sectors by invested capital")
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No sector data to show.")
    except Exception as e:
        st.warning("Sector distribution issue: " + str(e))

    st.markdown("---")

    # --- Co-investor network graph + clickable nodes (if possible) ---
    try:
        # Fetch co-investor pairs where selected investor is part of the pair
        co_sql = """
        SELECT investor_a, investor_b, together_count
        FROM public.vw_co_invest_pairs -- FIX: dbo.vw_co_invest_pairs -> public.vw_co_invest_pairs
        WHERE investor_a = %s OR investor_b = %s
        ORDER BY together_count DESC;
        """
        # FIX: Changed params dict to tuple
        co_df = cached_query(co_sql, (investor, investor))

        st.subheader("Co-investor network")
        if co_df.empty:
            st.info("No co-investor data for this investor.")
        else:
            # Build partners table for display below
            partners = []
            for _, row in co_df.iterrows():
                a = row['investor_a']
                b = row['investor_b']
                partner = b if a == investor else a
                partners.append({"co_investor": partner, "together_count": int(row['together_count'] or 0)})
            partners_df = pd.DataFrame(partners)

            # Build nodes and edges for networkx
            G = nx.Graph()
            G.add_node(investor, size=30, label=investor)
            for _, row in co_df.iterrows():
                a = row['investor_a']
                b = row['investor_b']
                partner = b if a == investor else a
                weight = int(row['together_count'] or 1)
                G.add_node(partner, size=20, label=partner)
                # add edge between central investor and partner (we only show star-like edges here)
                G.add_edge(investor, partner, weight=weight)

            pos = nx.spring_layout(G, k=0.5, seed=42)

            # edge trace
            edge_x = []
            edge_y = []
            for u, v, d in G.edges(data=True):
                x0, y0 = pos[u]
                x1, y1 = pos[v]
                edge_x += [x0, x1, None]
                edge_y += [y0, y1, None]
            edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='#888'), hoverinfo='none', mode='lines')

            # node trace
            node_x = []
            node_y = []
            node_text = []
            node_custom = []
            node_size = []
            for n in G.nodes():
                x, y = pos[n]
                node_x.append(x)
                node_y.append(y)
                node_text.append(n)
                node_custom.append(n)
                node_size.append(G.nodes[n].get('size', 10) * (1.2 if n==investor else 1))

            node_trace = go.Scatter(
                x=node_x, y=node_y,
                mode='markers+text',
                text=node_text,
                textposition="bottom center",
                hoverinfo='text',
                
                marker=dict(
                    showscale=False,
                    color=['#9D8C5A' if n==investor else '#7C93A3' for n in G.nodes()],
                    size=node_size,
                    line_width=2
                ),

                customdata=node_custom
            )

            fig = go.Figure(data=[edge_trace, node_trace],
                            layout=go.Layout(
                                title=f"Co-investor network for {investor}",
                                showlegend=False,
                                hovermode='closest',
                                margin=dict(b=20,l=5,r=5,t=40),
                                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                                height=450,
                                paper_bgcolor='#1E2A3A',
                                plot_bgcolor='#1E2A3A',
                                font=dict(color='#B8B8B8', family='Lora, Arial')

                            ))

            # Render network once: use plotly_events if available (it renders), otherwise use st.plotly_chart
            if PLOTLY_EVENTS_AVAILABLE:
                clicked = plotly_events(fig, click_event=True, hover_event=False, key=f"net_{investor}")
                # If a node clicked and it's not the central investor, navigate to that investor
                if clicked:
                    clicked_name = clicked[0].get("customdata")
                    if clicked_name and clicked_name != investor:
                        st.session_state["navigate_to"] = {"page":"Investors", "quick_select_investor": clicked_name}
                        # Some Streamlit installs may not expose experimental_rerun; handle both cases gracefully
                        if hasattr(st, "experimental_rerun"):
                            st.experimental_rerun()
                        else:
                            st.info(f"Navigation queued to {clicked_name}. Please click 'Investors' in the sidebar to go to the profile.")
                            return
            else:
                st.plotly_chart(fig, use_container_width=True)
                st.info("Tip: To enable 'click node to open profile' install `streamlit-plotly-events` in your venv.")

    except Exception as e:
            st.error(f"Error rendering co-investor network: {e}")


            # --- Co-investors table (always show below the network) ---
    st.markdown("**Co-investors**")
    partners_df = pd.DataFrame(partners)
    # Friendly column names and ordering, start index at 1
    if not partners_df.empty:
        partners_df = partners_df.rename(columns={'co_investor': 'Co-investor', 'together_count': 'Deals Together'})
        partners_df = partners_df[['Co-investor', 'Deals Together']].sort_values('Deals Together', ascending=False).reset_index(drop=True)
        partners_df.index = range(1, len(partners_df) + 1)
        st.markdown("**Co-investors - Sorted by deals together**")
        st.dataframe(partners_df, use_container_width=True, column_config={"Deals Together": {"css_text_align": "left"}})
        
    else:
        st.info("No co-investors to list.")

    st.markdown("---")

    # --- Pitch recommendations card (auto-generated) ---
    st.subheader("Pitch Recommendations")
    st.caption("_For informational purposes only — these are heuristic suggestions based on the investor's historical behavior. Not investment advice._")

    try:
        # Avg ticket & median equity from vw_investor_summary (fallback compute if missing)
        # FIX: Named params to positional (%s)
        # FIX: dbo.vw_investor_summary -> public.vw_investor_summary
        stats = cached_query("SELECT * FROM public.vw_investor_summary WHERE investor = %s", (investor,))
        if not stats.empty:
            
            s = stats.iloc[0]
            # Convert to float here
            avg_ticket = float(s.avg_ticket) if not pd.isnull(s.avg_ticket) else 0.0
            median_equity = s.median_invested_equity if not pd.isnull(s.median_invested_equity) else None
            if avg_ticket and avg_ticket > 0:
                rec_min = max(10000, 0.5 * avg_ticket)
                rec_max = 1.5 * avg_ticket
            
            # s = stats.iloc[0]
            # avg_ticket = s.avg_ticket if not pd.isnull(s.avg_ticket) else 0
            # median_equity = s.median_invested_equity if not pd.isnull(s.median_invested_equity) else None
            # if avg_ticket and avg_ticket > 0:
            #     rec_min = max(10000, 0.5 * avg_ticket)
            #     rec_max = 1.5 * avg_ticket
            else:
                rec_min, rec_max = 100000, 1000000
            
            # FIX: T-SQL TOP 3 and ISNULL -> PostgreSQL LIMIT 3 and COALESCE
            # FIX: Named params to positional (%s)
            pref_sql = """
            SELECT COALESCE(d.sector, 'Unknown') AS sector, COUNT(*) AS deals, SUM(COALESCE(d.invested_amount, 0)) AS total_invested
            FROM public.deal_investors di JOIN public.deals d ON di.staging_id = d.staging_id
            WHERE di.investor = %s
            GROUP BY COALESCE(d.sector, 'Unknown')
            ORDER BY total_invested DESC
            LIMIT 3;
            """
            pref_df = cached_query(pref_sql, (investor,))
            pref_sectors = pref_df['sector'].tolist() if not pref_df.empty else []

            # FIX: T-SQL TOP 1 and ISNULL -> PostgreSQL DISTINCT and COALESCE (PERCENTILE_CONT is standard SQL)
            # FIX: Named params to positional (%s)
            rev_sql = """
            
            SELECT 
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY d.yearly_revenue) AS median_yearly
            FROM public.deal_investors di
            JOIN public.deals d ON di.staging_id = d.staging_id
            WHERE di.investor = %s AND d.yearly_revenue IS NOT NULL;
            """

            rev_df = cached_query(rev_sql, (investor,))
            median_yearly = None
            if not rev_df.empty:
                median_yearly = rev_df.iloc[0].median_yearly

            cols = st.columns(2)
            with cols[0]:
                st.markdown("**Suggested ask range**")
                st.write(f"{format_lakhs(rec_min)} — {format_lakhs(rec_max)}")
                st.markdown("**Typical equity (median)**")
                st.write(f"{median_equity:.2f}%" if median_equity else "N/A")
                st.markdown("**Preferred sectors**")
                st.write(", ".join(pref_sectors) if pref_sectors else "N/A")
            with cols[1]:
                st.markdown("**Suggested pitch lines**")
                if median_yearly and median_yearly>0:
                    st.write(f"- \"We're at ₹{int(median_yearly):,} ARR with month-on-month growth of X% — targeting ₹{int(rec_min)}-{int(rec_max)} for a Y% equity stake.\"")
                else:
                    st.write(f"- \"We are revenue-generating with strong unit economics — looking for ₹{int(rec_min)} to scale distribution; happy to discuss equity around {median_equity:.1f}% typical for your investments.\"")
                st.write("- Emphasize unit economics, CAC payback, and repeat purchase (D2C) metrics if applicable.")
                st.write("- Show a 3–6 month growth plan with channel unit economics and retention.")
    except Exception as e:
        st.warning("Could not compute pitch recommendations: " + str(e))

    st.markdown("---")

    # --- Portfolio list (detailed table) ---
    try:
        # FIX: Replace T-SQL STUFF((SELECT... FOR XML PATH) with PostgreSQL STRING_AGG or a correlated subquery + STRING_AGG
        # FIX: Named params to positional (%s)
        port_sql = """
        SELECT 
            d.company, 
            d.season, 
            d.asked_amount, 
            
            d.invested_amount, 
            d.equity_final,
            (SELECT STRING_AGG(di2.investor, ', ') FROM public.deal_investors di2 WHERE di2.staging_id = d.staging_id AND di2.investor != %s) AS investors
        FROM public.deal_investors di
        JOIN public.deals d ON di.staging_id = d.staging_id
        WHERE di.investor = %s
        ORDER BY d.invested_amount DESC;
        """
        # FIX: Changed params dict to tuple
        df_port = cached_query(port_sql, (investor, investor))
        st.subheader("Portfolio - Detailed Holdings")
        if not df_port.empty:
            
            df_disp = df_port.copy()
            # format monetary fields as lakhs / crores
            if 'asked_amount' in df_disp.columns:
                df_disp['asked_amount'] = df_disp['asked_amount'].apply(lambda x: format_lakhs(x) if pd.notnull(x) and x != 0 else "-")
            if 'invested_amount' in df_disp.columns:
                df_disp['invested_amount'] = df_disp['invested_amount'].apply(lambda x: format_lakhs(x) if pd.notnull(x) and x != 0 else "-")
            if 'equity_final' in df_disp.columns:
                df_disp['equity_final'] = df_disp['equity_final'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "-")

            # friendly column names
            rename_map = {}
            if 'company' in df_disp.columns: rename_map['company'] = 'Company'
            if 'season' in df_disp.columns: rename_map['season'] = 'Season'
            if 'asked_amount' in df_disp.columns: rename_map['asked_amount'] = 'Asked (L)'
            if 'invested_amount' in df_disp.columns: rename_map['invested_amount'] = 'Invested (L)'
            if 'equity_final' in df_disp.columns: rename_map['equity_final'] = 'Equity (%)'
            if 'investors' in df_disp.columns: rename_map['investors'] = 'Co-investors'
            df_disp.rename(columns=rename_map, inplace=True)

            # user-friendly 1-based index
            df_disp.index = range(1, len(df_disp) + 1)

            st.dataframe(df_disp, use_container_width=True)
            st.download_button("Download portfolio CSV", df_disp.to_csv(index=True), file_name=f"{investor}_portfolio.csv", mime="text/csv")

        else:
            st.info("No portfolio rows found.")
    except Exception as e:
        st.warning("Portfolio load issue: " + str(e))