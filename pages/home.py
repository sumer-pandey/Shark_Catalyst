# pages/home.py
import streamlit as st
import plotly.express as px
from utils import cached_query, format_currency
import pandas as pd

def page_home(filters):
    st.title("Executive Snapshot")
#     st.markdown("""
#     <div style="background-color: #262626; padding: 10px; border-radius: 5px;">
#         <h1 style="color: white; text-align: center;">Executive Snapshot</h1>
#     </div>
#     """,
#     unsafe_allow_html=True
# )
    season = filters.get("season", "All")

        # --- Helper: format amounts assuming input numbers are in lakhs (L) ---
    def format_lakhs(val):
        """
        val: numeric (assumed to represent lakhs)
        Returns string:
         - for <100 L: "12,345 L"
         - for >=100 L: "12.34 Cr (12,345 L)"
        Keeps it human-friendly and consistent for the Home page only.
        """
        try:
            if val is None:
                return "-"
            # numeric handling
            v = float(val)
            if v == 0:
                return "0 L"
            # show crores if 100 L or more (100 L = 1 Cr)
            if v >= 100:
                crores = v / 100.0
                # show two decimals for crores and full lakhs with thousands separator
                return f"{crores:.2f} Cr ({int(round(v)):,} L)"
            # else show lakhs, if integer remove decimals
            if v.is_integer():
                return f"{int(v):,} L"
            return f"{v:,.2f} L"
        except Exception:
            return str(val)

    # KPI query (stored proc)
    try:
        kpi_df = cached_query("EXEC dbo.sp_home_kpis @season = :season", {"season": season})
        if not kpi_df.empty:
            kpi = kpi_df.iloc[0]

            # --- Local short formatter for KPI display (succinct) ---
            def format_lakhs_short(val):
                """
                Accepts value in lakhs.
                - >= 100 L -> show in crores with 2 decimals: '2.68 Cr'
                - 1 L <= val < 100 -> show in lakhs with 1 decimal '12.3 L' or integer when whole
                - 0 or None -> '-'
                """
                try:
                    if val is None:
                        return "-"
                    v = float(val)
                    if v == 0:
                        return "0 L"
                    if v >= 100:
                        crores = v / 100.0
                        return f"{crores:.2f} Cr"
                    if v >= 1:
                        if v.is_integer():
                            return f"{int(v)} L"
                        return f"{v:.1f} L"
                    return f"{v:.2f} L"
                except Exception:
                    return str(val)

            # display 6 KPI cards (responsive)
            cols = st.columns(6)

            # 1. Total Pitches
            cols[0].markdown("**Total Pitches**", unsafe_allow_html=True)
            cols[0].metric("", int(kpi.total_pitches or 0))

            # 2. Funded Deals + funded rate delta
            funded = int(kpi.funded_deals or 0)
            total_pitches = int(kpi.total_pitches or 0)
            funded_rate = (funded / total_pitches) if total_pitches > 0 else None
            cols[1].markdown("**Funded Deals**", unsafe_allow_html=True)
            cols[1].metric("", funded, delta=f"{funded_rate:.1%}" if funded_rate is not None else "")

            # 3. Total Capital Invested (short, succinct)
            cols[2].markdown("**Total Capital Invested**", unsafe_allow_html=True)
            cols[2].metric("", format_lakhs_short(kpi.total_capital_invested))

            # 4. Average Deal Size (short)
            cols[3].markdown("**Average Deal Size**", unsafe_allow_html=True)
            cols[3].metric("", format_lakhs_short(kpi.avg_deal_size))

            # 5. Average Equity Accepted (%)
            # use markdown above metric so label wraps instead of getting truncated
            cols[4].markdown("**Average Equity (%)**", unsafe_allow_html=True)
            cols[4].metric("", f"{(kpi.avg_equity_accepted or 0):.2f}%")

            # 6. Deals < ₹1 Cr (%)
            cols[5].markdown("**Deals < ₹1 Cr (%)**", unsafe_allow_html=True)
            cols[5].metric("", f"{(kpi.pct_deals_under_1cr or 0):.2%}")
    except Exception as e:
        st.warning("Could not load KPIs: " + str(e))

    st.markdown("---")

    # Trend by episode (use stored proc that includes rolling_3_episode_avg)

    try:
        trend_df = cached_query("EXEC dbo.sp_home_trend_by_episode @season = :season", {"season": season})
        if not trend_df.empty:
            # 1) Aggregate to season-level: sum invested and count pitches (episodes) per season
            invest_by_season = trend_df.groupby('season', sort=False)['total_invested'].sum().reset_index()
            counts = trend_df.groupby('season', sort=False).size().reset_index(name='pitches')
            season_summary = invest_by_season.merge(counts, on='season').sort_values('season').reset_index(drop=True)

            # 2) Uniform x positions so ticks don't crowd (10,20,30 ...)
            season_summary['x_pos'] = [(i + 1) * 10 for i in range(len(season_summary))]

            # 3) Add an auxiliary series: avg invested per pitch (friendly secondary metric)
            season_summary['avg_per_pitch'] = season_summary.apply(
                lambda r: (r['total_invested'] / r['pitches']) if r['pitches'] and r['pitches'] > 0 else 0, axis=1
            )

            # 4) Plot: primary = total invested (L), secondary = avg invested per pitch (L)
            # Primary trace (total invested)
            fig = px.line(season_summary, x='x_pos', y='total_invested', markers=True, title="Total Amount Invested by Season")
            fig.update_traces(name="Total Amount Invested (L)", selector=dict(mode='lines+markers'))

            # Secondary trace (avg per pitch) created via px and then adjusted to use yaxis 'y2'
            trace2 = px.line(season_summary, x='x_pos', y='avg_per_pitch', markers=True).data[0]
            trace2.update(name='Avg Invested per Pitch (L)', mode='lines+markers',
              line=dict(color='red', width=3), marker=dict(symbol='circle-open'))
            # assign the second trace to the secondary y-axis
            trace2.update(yaxis='y2')
            fig.add_trace(trace2)

            # annotate number of pitches above markers (primary series)
            for _, r in season_summary.iterrows():
                fig.add_annotation(x=r['x_pos'], y=r['total_invested'],
                                   text=f"{int(r['pitches'])} pitches",
                                   showarrow=False, yshift=10, font=dict(size=11))

            # Friendly axis labels and tidy layout (secondary y-axis shown on right)
            fig.update_layout(
                xaxis=dict(tickmode='array', tickvals=season_summary['x_pos'], ticktext=season_summary['season'], title='Season'),
                yaxis=dict(title='Total Amount Invested (L)'),
                yaxis2=dict(title='Avg Invested per Pitch (L)', overlaying='y', side='right'),
                legend=dict(title='Series'),
                height=420,
                margin=dict(l=40, r=60, t=64, b=120)
            )

            # y-range for primary axis: keep small positive lower bound if values positive
            yvals = season_summary["total_invested"].fillna(0)
            if yvals.max() > 0:
                fig.update_yaxes(range=[max(1, float(yvals.min() - 0.1 * yvals.max())), float(yvals.max() * 1.05)])

            # optional: scale secondary axis to its values so markers/line are visible
            y2vals = season_summary["avg_per_pitch"].fillna(0)
            if y2vals.max() > 0:
                # set a comfortable top on y2
                fig.update_layout(yaxis2=dict(range=[0, float(y2vals.max() * 1.2)], title='Avg Invested per Pitch (L)', overlaying='y', side='right'))

            st.markdown("""
            <div style='display:flex; justify-content:center; gap: 2rem; margin-bottom: 1rem;'>
            <div style='display:flex; align-items:center;'>
            <div style='width:12px; height:12px; background-color:#636EFA; border-radius:50%; margin-right:5px;'></div>
            <span style='font-size:14px;'>Total Amount Invested (L)</span>
            </div>
            <div style='display:flex; align-items:center;'>
            <div style='width:12px; height:12px; background-color:#EF553B; border-radius:50%; margin-right:5px;'></div>
            <span style='font-size:14px;'>Avg Invested per Pitch (L)</span>
            </div>
            </div>
            """, unsafe_allow_html=True)

            st.plotly_chart(fig, use_container_width=True)

            if filters.get("view_sql"):
                st.code("EXEC dbo.sp_home_trend_by_episode @season = :season")
    except Exception as e:
        st.warning("Trend load issue: " + str(e))


    st.markdown("## Sector-wise breakdown")
    # Sector breakdown — exclude zero-total sectors and show download CSV
    sectors_sql = """
    SELECT COALESCE(sector,'Unknown') AS sector, COUNT(*) AS deals, SUM(ISNULL(invested_amount,0)) AS total_invested
    FROM dbo.deals
    WHERE (:season = 'All' OR season = :season)
    GROUP BY COALESCE(sector,'Unknown')
    HAVING SUM(ISNULL(invested_amount,0)) > 0
    ORDER BY total_invested DESC
    OFFSET 0 ROWS FETCH NEXT 10 ROWS ONLY;
    """
    try:
        df_sectors = cached_query(sectors_sql, {"season": season})
        if not df_sectors.empty:
            # friendly axis labels and chart tweaks
            fig_s = px.bar(df_sectors, x="sector", y="total_invested", title="Top sectors by capital invested")
            fig_s.update_layout(
                xaxis_title="Sector",
                yaxis_title="Total Capital Invested (L)",
                xaxis_tickangle=-45,
                height=380,
                margin=dict(b=120)
            )
            # ensure y-axis starts at 1 if positive
            if df_sectors["total_invested"].max() > 0:
                fig_s.update_yaxes(range=[1, df_sectors["total_invested"].max() * 1.05])
            st.plotly_chart(fig_s, use_container_width=True)
            st.download_button("Download sectors CSV", df_sectors.to_csv(index=False), file_name="sectors.csv", mime="text/csv")
            if filters.get("view_sql"):
                st.code(sectors_sql)
        else:
            st.info("No sector data to display for this season.")
    except Exception as e:
        st.warning("Sectors load issue: " + str(e))

    st.markdown("## Top 5 Sharks")
    try:
        # Use per-investor invested_amount when available in deal_investors.
        # If per-investor amounts missing, fall back to splitting deal-level invested_amount evenly across investors on that deal.
        top_sharks_sql = """
        WITH inv_counts AS (
          SELECT deal_id, COUNT(*) AS inv_count
          FROM dbo.deal_investors
          GROUP BY deal_id
        )
        SELECT TOP 5
          di.investor,
          COUNT(DISTINCT di.deal_id) AS deals_count,
          SUM(
            COALESCE(
              di.invested_amount,
              CASE WHEN ic.inv_count > 0 THEN CAST(d.invested_amount AS FLOAT) / ic.inv_count ELSE CAST(d.invested_amount AS FLOAT) END
            )
          ) AS total_invested,
          AVG(
            COALESCE(
              di.invested_amount,
              CASE WHEN ic.inv_count > 0 THEN CAST(d.invested_amount AS FLOAT) / ic.inv_count ELSE CAST(d.invested_amount AS FLOAT) END
            )
          ) AS avg_ticket
        FROM dbo.deal_investors di
        JOIN dbo.deals d ON di.deal_id = d.id
        LEFT JOIN inv_counts ic ON ic.deal_id = d.id
        WHERE di.investor IS NOT NULL
        GROUP BY di.investor
        ORDER BY total_invested DESC;
        """
        top_sharks = cached_query(top_sharks_sql)
        if not top_sharks.empty:
            cols = st.columns(5)
            for i, row in top_sharks.reset_index(drop=True).iterrows():
                with cols[i]:
                    # use project accent color for names
                    st.markdown(f"<span style='color:#9D8C5A;font-weight:700'>{row['investor']}</span>", unsafe_allow_html=True)
                    st.metric("Deals", int(row['deals_count']), delta=None)
                    # format total invested (assumed lakhs in source)
                    # Note: total_invested comes out in same units as source (we assume lakhs)
                    st.write(f"Total: {format_lakhs(row['total_invested'])}")
                    if st.button(f"Open profile: {row['investor']}", key=f"open_{i}"):
                        st.session_state["navigate_to"] = {"page":"Investor Intelligence", "quick_select_investor": row['investor']}
        else:
            st.info("No sharks found.")
    except Exception as e:
        st.warning("Top sharks load issue: " + str(e))


    st.markdown("---")
    st.subheader("Recent Deals")
    try:
        df_recent = cached_query("EXEC dbo.sp_recent_deals @season = :season, @top = :top", {"season": season, "top": 8})
        if not df_recent.empty:
            # apply quick_search filter client-side if provided
            q = filters.get("quick_search","").strip()
            if q:
                mask = df_recent.apply(lambda r: r.astype(str).str.contains(q, case=False, na=False).any(), axis=1)
                df_recent = df_recent[mask]
            # format currency for human display
            display = df_recent.copy()
            # convert amounts (assumed in lakhs)
            if 'asked_amount' in display.columns:
                display['asked_amount'] = display['asked_amount'].apply(lambda x: format_lakhs(x) if pd.notnull(x) and x != 0 else "-")
            if 'invested_amount' in display.columns:
                display['invested_amount'] = display['invested_amount'].apply(lambda x: format_lakhs(x) if pd.notnull(x) and x != 0 else "-")
            if 'equity_final' in display.columns:
                display['equity_final'] = display['equity_final'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "-")

            # friendly column renames (only rename columns that exist)
            rename_map = {}
            if 'company' in display.columns: rename_map['company'] = 'Company'
            if 'season' in display.columns: rename_map['season'] = 'Season'
            if 'episode_number' in display.columns: rename_map['episode_number'] = 'Episode'
            if 'episode_title' in display.columns: rename_map['episode_title'] = 'Episode Title'
            if 'asked_amount' in display.columns: rename_map['asked_amount'] = 'Asked (L)'
            if 'invested_amount' in display.columns: rename_map['invested_amount'] = 'Invested (L)'
            if 'equity_final' in display.columns: rename_map['equity_final'] = 'Equity (%)'
            if 'pitchers_city' in display.columns: rename_map['pitchers_city'] = 'City'
            if 'investors' in display.columns: rename_map['investors'] = 'Investors'

            display.rename(columns=rename_map, inplace=True)

            # reset index to start at 1 (for user-friendly numbering)
            display.index = range(1, len(display) + 1)

            st.dataframe(display, use_container_width=True)
            st.download_button("Download recent deals CSV", display.to_csv(index=True), file_name="recent_deals.csv", mime="text/csv")
            if filters.get("view_sql"):
                st.code("EXEC dbo.sp_recent_deals @season = :season, @top = :top")
                
        else:
            st.info("No recent deals available.")
    except Exception as e:
        st.warning("Recent deals load issue: " + str(e))

    st.markdown("### Quick Insights")
    insight_cols = st.columns(3)
    # compute small insights safely
    try:
        top_sector_df = cached_query("""
            SELECT TOP 1 COALESCE(sector,'Unknown') AS sector, SUM(ISNULL(invested_amount,0)) AS total_invested
            FROM dbo.deals
            GROUP BY COALESCE(sector,'Unknown')
            ORDER BY total_invested DESC;
        """)
        top_sector = top_sector_df.iloc[0]['sector'] if not top_sector_df.empty else "N/A"
    except Exception:
        top_sector = "N/A"

    try:
        # average ticket (assume avg_deal_size in kpi if available)
        if 'kpi' in locals():
            avg_ticket_val = kpi.avg_deal_size
        else:
            avg_ticket_df = cached_query("SELECT AVG(ISNULL(invested_amount,0)) AS avg_ticket FROM dbo.deals;")
            avg_ticket_val = avg_ticket_df.iloc[0]['avg_ticket'] if not avg_ticket_df.empty else None
    except Exception:
        avg_ticket_val = None

    try:
        funded_rates = cached_query("""
            SELECT season, SUM(CASE WHEN invested_amount IS NOT NULL THEN 1 ELSE 0 END)*1.0/NULLIF(COUNT(*),0) AS funded_rate
            FROM dbo.deals
            GROUP BY season
            ORDER BY season;
        """)
        if funded_rates is not None and len(funded_rates) >= 2:
            last = funded_rates.iloc[-1]['funded_rate'] or 0
            prev = funded_rates.iloc[-2]['funded_rate'] or 0
            diff_pp = (last - prev) * 100
            funded_trend = "up" if diff_pp > 0 else ("down" if diff_pp < 0 else "flat")
            funded_text = f"{diff_pp:+.1f} pp"
        else:
            funded_text = "N/A"
    except Exception:
        funded_text = "N/A"

    # render three insight cards with friendly headings + accent color
    insight_cols[0].markdown(f"<div style='color:#9D8C5A;font-weight:700'>Most Capital Invested</div>", unsafe_allow_html=True)
    insight_cols[0].write(top_sector)
    if insight_cols[0].button("Explore related myth"):
        st.session_state["navigate_to"] = {"page":"Myth Buster"}

    insight_cols[1].markdown(f"<div style='color:#9D8C5A;font-weight:700'>Average Ticket Size</div>", unsafe_allow_html=True)
    insight_cols[1].write(format_lakhs(avg_ticket_val) if avg_ticket_val is not None else "N/A")

    insight_cols[2].markdown(f"<div style='color:#9D8C5A;font-weight:700'>Funded Rate Trend</div>", unsafe_allow_html=True)
    insight_cols[2].write(funded_text)
