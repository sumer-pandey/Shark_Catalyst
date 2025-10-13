# # pages/home.py
# import streamlit as st
# import plotly.express as px
# from utils import cached_query, format_currency
# import pandas as pd

# def page_home(filters):
#     st.title("Executive Snapshot")
# #     st.markdown("""
# #     <div style="background-color: #262626; padding: 10px; border-radius: 5px;">
# #         <h1 style="color: white; text-align: center;">Executive Snapshot</h1>
# #     </div>
# #     """,
# #     unsafe_allow_html=True
# # )
#     season = filters.get("season", "All")

#         # --- Helper: format amounts assuming input numbers are in lakhs (L) ---
#     def format_lakhs(val):
#         """
#         val: numeric (assumed to represent lakhs)
#         Returns string:
#          - for <100 L: "12,345 L"
#          - for >=100 L: "12.34 Cr (12,345 L)"
#         Keeps it human-friendly and consistent for the Home page only.
#         """
#         try:
#             if val is None:
#                 return "-"
#             # numeric handling
#             v = float(val)
#             if v == 0:
#                 return "0 L"
#             # show crores if 100 L or more (100 L = 1 Cr)
#             if v >= 100:
#                 crores = v / 100.0
#                 # show two decimals for crores and full lakhs with thousands separator
#                 return f"{crores:.2f} Cr ({int(round(v)):,} L)"
#             # else show lakhs, if integer remove decimals
#             if v.is_integer():
#                 return f"{int(v):,} L"
#             return f"{v:,.2f} L"
#         except Exception:
#             return str(val)

#     # KPI query (stored proc)
#     try:
#         # --- FIX: Replace EXEC dbo.sp_home_kpis with direct Postgres SQL ---
        
#                 # --- FIXED KPI SQL (Postgres) ---
#         kpi_sql = """
#         SELECT
#           COUNT(1) AS total_pitches,
#           SUM(CASE WHEN invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS funded_deals,
#           SUM(COALESCE(invested_amount,0)) AS total_capital_invested,
#           -- average deal size: average over funded deals (non-null invested_amount)
#           CASE WHEN SUM(CASE WHEN invested_amount IS NOT NULL THEN 1 ELSE 0 END) > 0
#                THEN SUM(COALESCE(invested_amount,0)) / SUM(CASE WHEN invested_amount IS NOT NULL THEN 1 ELSE 0 END)
#                ELSE 0 END AS avg_deal_size,
#           AVG(NULLIF(equity_final,0)) AS avg_equity_accepted,
#           -- percent of all pitches that resulted in a funded deal < 100 L (1 Cr)
#           SUM(CASE WHEN invested_amount IS NOT NULL AND invested_amount < 100 THEN 1 ELSE 0 END) * 1.0 / NULLIF(COUNT(1),0) AS pct_deals_under_1cr
#         FROM public.deals
#         WHERE (%s = 'All' OR season = %s)
#         """
#         kpi_df = cached_query(kpi_sql, (season, season))
#         # --- END FIX ---

#         # pages/home.py, around line 65 (in the KPI try block)
#         if not kpi_df.empty:
#             # FIX: Explicitly cast critical columns to float to avoid Decimal type issues in plotting/calculations
#             # FIX: Use the new column name for the KPI
#             for col in ['total_capital_invested', 'avg_deal_size', 'avg_equity_accepted']:
#                 if col in kpi_df.columns:
#                     kpi_df[col] = kpi_df[col].apply(lambda x: float(x) if x is not None else 0.0)
            
#             # NEW FIX: Process the new pct_deals column
            
#             if 'pct_deals_under_1cr' in kpi_df.columns:
#                 kpi_df['pct_deals_under_1cr'] = kpi_df['pct_deals_under_1cr'].apply(lambda x: float(x) if x is not None else 0.0)
#             else:
#                 # fallback if SQL alias changed or missing
#                 kpi_df['pct_deals_under_1cr'] = 0.0

#             # Ensure other KPI fields are numeric floats (already done for three columns above)
#             if 'funded_deals' in kpi_df.columns:
#                 kpi_df['funded_deals'] = kpi_df['funded_deals'].apply(lambda x: int(x) if x is not None else 0)
#             if 'total_pitches' in kpi_df.columns:
#                 kpi_df['total_pitches'] = kpi_df['total_pitches'].apply(lambda x: int(x) if x is not None else 0)

#             kpi = kpi_df.iloc[0]

#             # --- Local short formatter for KPI display (succinct) ---
#             def format_lakhs_short(val):
#                 """
#                 Accepts value in lakhs.
#                 - >= 100 L -> show in crores with 2 decimals: '2.68 Cr'
#                 - 1 L <= val < 100 -> show in lakhs with 1 decimal '12.3 L' or integer when whole
#                 - 0 or None -> '-'
#                 """
#                 try:
#                     if val is None:
#                         return "-"
#                     v = float(val)
#                     if v == 0:
#                         return "0 L"
#                     if v >= 100:
#                         crores = v / 100.0
#                         return f"{crores:.2f} Cr"
#                     if v >= 1:
#                         if v.is_integer():
#                             return f"{int(v)} L"
#                         return f"{v:.1f} L"
#                     return f"{v:.2f} L"
#                 except Exception:
#                     return str(val)

#             # display 6 KPI cards (responsive)
#             cols = st.columns(6)

#             # 1. Total Pitches
#             cols[0].markdown("**Total Pitches**", unsafe_allow_html=True)
#             cols[0].metric("", int(kpi.total_pitches or 0))

#             # 2. Funded Deals + funded rate delta
#             funded = int(kpi.funded_deals or 0)
#             total_pitches = int(kpi.total_pitches or 0)
#             funded_rate = (funded / total_pitches) if total_pitches > 0 else None
#             cols[1].markdown("**Funded Deals**", unsafe_allow_html=True)
#             cols[1].metric("", funded, delta=f"{funded_rate:.1%}" if funded_rate is not None else "")

#             # 3. Total Capital Invested (short, succinct)
#             cols[2].markdown("**Total Capital Invested**", unsafe_allow_html=True)
#             cols[2].metric("", format_lakhs_short(kpi.total_capital_invested))

#             # 4. Average Deal Size (short)
#             cols[3].markdown("**Average Deal Size**", unsafe_allow_html=True)
#             cols[3].metric("", format_lakhs_short(kpi.avg_deal_size))

#             # 5. Average Equity Accepted (%)
#             # use markdown above metric so label wraps instead of getting truncated
#             cols[4].markdown("**Average Equity (%)**", unsafe_allow_html=True)
#             cols[4].metric("", f"{(kpi.avg_equity_accepted or 0):.2f}%")

#             # 6. Deals < ₹1 Cr (%)
#             cols[5].markdown("**Deals < ₹1 Cr (%)**", unsafe_allow_html=True)
#             cols[5].metric("", f"{(kpi.pct_deals_under_1cr or 0):.2%}")
#     except Exception as e:
#         st.warning("Could not load KPIs: " + str(e))

#     st.markdown("---")

#     # Trend by episode (use stored proc that includes rolling_3_episode_avg)

#     try:
#         # --- FIX: Replace EXEC dbo.sp_home_trend_by_episode with equivalent SQL ---
#         # Assuming the stored proc returns total invested by episode, season, and episode number
#         trend_sql = """
#         SELECT
#             season,
#             episode_number,
#             SUM(COALESCE(invested_amount, 0)) AS total_invested
#         FROM public.deals
#         WHERE (%s = 'All' OR season = %s)
#         GROUP BY season, episode_number
#         ORDER BY season, episode_number
#         """
#         # FIX: Changed dictionary to tuple/list matching the two '%s' placeholders
#         trend_df = cached_query(trend_sql, (season, season))
#         # --- END FIX ---

#         if not trend_df.empty:
#             # 1) Aggregate to season-level: sum invested and count pitches (episodes) per season
#             invest_by_season = trend_df.groupby('season', sort=False)['total_invested'].sum().reset_index()
#             # Count the number of unique episodes per season for 'pitches'
#             counts = trend_df.groupby('season', sort=False)['episode_number'].nunique().reset_index(name='pitches')
            
#             season_summary = invest_by_season.merge(counts, on='season').sort_values('season').reset_index(drop=True)
            
#             # NEW FIX: Explicitly convert the aggregated column to float
#             season_summary['total_invested'] = season_summary['total_invested'].apply(lambda x: float(x) if x is not None else 0.0)
#             # END NEW FIX
            
#             # 2) Uniform x positions so ticks don't crowd (10,20,30 ...)
#             season_summary['x_pos'] = [(i + 1) * 10 for i in range(len(season_summary))]

#             # 3) Add an auxiliary series: avg invested per pitch (friendly secondary metric)
#             # The lambda function will now safely use float(r['total_invested'])
#             season_summary['avg_per_pitch'] = season_summary.apply(
#                 lambda r: (r['total_invested'] / r['pitches']) if r['pitches'] and r['pitches'] > 0 else 0, axis=1
#             )
    
#     # ... (rest of the plotting code is now safe)

#         # if not trend_df.empty:
#         #     # 1) Aggregate to season-level: sum invested and count pitches (episodes) per season
#         #     invest_by_season = trend_df.groupby('season', sort=False)['total_invested'].sum().reset_index()
#         #     # Count the number of unique episodes per season for 'pitches'
#         #     counts = trend_df.groupby('season', sort=False)['episode_number'].nunique().reset_index(name='pitches')
            
#         #     season_summary = invest_by_season.merge(counts, on='season').sort_values('season').reset_index(drop=True)

            

#         #     # 2) Uniform x positions so ticks don't crowd (10,20,30 ...)
#         #     season_summary['x_pos'] = [(i + 1) * 10 for i in range(len(season_summary))]

#         #     # 3) Add an auxiliary series: avg invested per pitch (friendly secondary metric)
#         #     season_summary['avg_per_pitch'] = season_summary.apply(
#         #         lambda r: (r['total_invested'] / r['pitches']) if r['pitches'] and r['pitches'] > 0 else 0, axis=1
#         #     )

#                         # 4) Plot: primary = total invested (L), secondary = avg invested per pitch (L)
#             fig = px.line(season_summary, x='x_pos', y='total_invested', markers=True, title="Total Amount Invested by Season")
#             fig.update_traces(name="Total Amount Invested (L)", selector=dict(mode='lines+markers'))

#             trace2 = px.line(season_summary, x='x_pos', y='avg_per_pitch', markers=True).data[0]
#             trace2.update(name='Avg Invested per Pitch (L)', mode='lines+markers',
#                           line=dict(color='red', width=3), marker=dict(symbol='circle-open'))
#             trace2.update(yaxis='y2')
#             fig.add_trace(trace2)

#             # annotate number of pitches above markers (primary series)
#             for _, r in season_summary.iterrows():
#                 fig.add_annotation(x=r['x_pos'], y=r['total_invested'],
#                                    text=f"{int(r['pitches'])} pitches",
#                                    showarrow=False, yshift=10, font=dict(size=11))

#             # Friendly axis labels and tidy layout
#             fig.update_layout(
#                 xaxis=dict(tickmode='array', tickvals=season_summary['x_pos'], ticktext=season_summary['season'], title='Season'),
#                 yaxis=dict(title='Total Amount Invested (L)'),
#                 yaxis2=dict(title='Avg Invested per Pitch (L)', overlaying='y', side='right'),
#                 legend=dict(title='Series'),
#                 height=420,
#                 margin=dict(l=40, r=60, t=64, b=120)
#             )

#             # ----- SAFE numeric handling for axis ranges -----
#             # Use aggregated season_summary totals (already converted to float above)
#             yvals = season_summary["total_invested"].fillna(0).apply(lambda v: float(v) if v is not None else 0.0)
#             if len(yvals) and yvals.max() > 0:
#                 y_min = float(yvals.min())
#                 y_max = float(yvals.max())
#                 fig.update_yaxes(range=[max(1.0, y_min - 0.1 * y_max), y_max * 1.05])

#             # scale secondary axis
#             y2vals = season_summary["avg_per_pitch"].fillna(0).apply(lambda v: float(v) if v is not None else 0.0)
#             if len(y2vals) and y2vals.max() > 0:
#                 fig.update_layout(yaxis2=dict(range=[0, float(y2vals.max() * 1.2)], title='Avg Invested per Pitch (L)', overlaying='y', side='right'))

#             st.markdown("""
#             <div style='display:flex; justify-content:center; gap: 2rem; margin-bottom: 1rem;'>
#             <div style='display:flex; align-items:center;'>
#             <div style='width:12px; height:12px; background-color:#636EFA; border-radius:50%; margin-right:5px;'></div>
#             <span style='font-size:14px;'>Total Amount Invested (L)</span>
#             </div>
#             <div style='display:flex; align-items:center;'>
#             <div style='width:12px; height:12px; background-color:#EF553B; border-radius:50%; margin-right:5px;'></div>
#             <span style='font-size:14px;'>Avg Invested per Pitch (L)</span>
#             </div>
#             </div>
#             """, unsafe_allow_html=True)

#             st.plotly_chart(fig, use_container_width=True)

#             if filters.get("view_sql"):
#                 # FIX: Show the actual SQL being executed now
#                 st.code(trend_sql)
#     except Exception as e:
#         st.warning("Trend load issue: " + str(e))


#     st.markdown("## Sector-wise breakdown")
#     # Sector breakdown — exclude zero-total sectors and show download CSV
#     sectors_sql = """
#     SELECT COALESCE(sector,'Unknown') AS sector, COUNT(*) AS deals, SUM(COALESCE(invested_amount,0)) AS total_invested -- FIX: ISNULL -> COALESCE
#     FROM public.deals -- FIX: dbo.deals -> public.deals
#     WHERE (%s = 'All' OR season = %s)
#     GROUP BY COALESCE(sector,'Unknown')
#     HAVING SUM(COALESCE(invested_amount,0)) > 0
#     ORDER BY total_invested DESC
#     LIMIT 10; -- FIX: OFFSET/FETCH -> LIMIT
#     """
#     try:
#         # FIX: Changed dictionary to tuple/list matching the two '%s' placeholders
#         df_sectors = cached_query(sectors_sql, (season, season))
#         if not df_sectors.empty:
#             # friendly axis labels and chart tweaks
#             fig_s = px.bar(df_sectors, x="sector", y="total_invested", title="Top sectors by capital invested")
#             fig_s.update_layout(
#                 xaxis_title="Sector",
#                 yaxis_title="Total Capital Invested (L)",
#                 xaxis_tickangle=-45,
#                 height=380,
#                 margin=dict(b=120)
#             )
#             # ensure y-axis starts at 1 if positive
            
#                         # ensure y-axis starts at 1 if positive
#             max_val = df_sectors["total_invested"].max()
#             if max_val is not None and float(max_val) > 0:
#                 fig_s.update_yaxes(range=[1, float(max_val) * 1.05])


#             # if df_sectors["total_invested"].max() > 0:
#             #     fig_s.update_yaxes(range=[1, df_sectors["total_invested"].max() * 1.05])
#             st.plotly_chart(fig_s, use_container_width=True)
#             st.download_button("Download sectors CSV", df_sectors.to_csv(index=False), file_name="sectors.csv", mime="text/csv")
#             if filters.get("view_sql"):
#                 st.code(sectors_sql)
#         else:
#             st.info("No sector data to display for this season.")
#     except Exception as e:
#         st.warning("Sectors load issue: " + str(e))

#     st.markdown("## Top 5 Sharks")
#     try:
#         # Fetch raw deal data for all funded deals matching the season filter
#         top_sharks_raw_sql = f"""
#         SELECT 
#             d.staging_id, 
#             d.invested_amount, 
#             di.investor AS investor_raw,
#             d.number_of_sharks_in_deal -- Use this to divide the total invested amount later
#         FROM public.deals d
#         JOIN public.deal_investors di ON d.staging_id = di.staging_id
#         WHERE d.invested_amount IS NOT NULL
#         AND (%s = 'All' OR d.season = %s);
#         """
#         # FIX: Pass season filter arguments
#         top_sharks_raw_df = cached_query(top_sharks_raw_sql, (season, season))

#         if not top_sharks_raw_df.empty:
#             # FIX: Python Logic to correct for double-counting in multi-shark deals
#             rows = []
#             for _, r in top_sharks_raw_df.iterrows():
#                 # 1. Clean and split investor names
#                 investors = [inv.strip() for inv in str(r['investor_raw']).replace(';', ',').split(',') if inv.strip()]
                
#                 # 2. Determine the number of sharks in the deal (use the column if present, otherwise count from list)
#                 shark_count = int(r.get('number_of_sharks_in_deal') or len(investors))
#                 # Ensure shark_count is at least 1 to prevent division by zero
#                 shark_count = max(1, shark_count)
                
#                 # 3. Calculate the imputed investment amount per shark (assuming equal split)
#                 imputed_investment = float(r['invested_amount']) / shark_count
                
#                 # 4. Create a row for each shark
#                 for inv in investors:
#                     rows.append({
#                         'investor': inv, 
#                         'deals_count_unit': 1, # This will be summed to count unique deals
#                         'imputed_investment': imputed_investment, 
#                         'staging_id': r['staging_id']
#                     })
            
#             # Aggregate the cleaned data
#             df_sharks_agg = pd.DataFrame(rows).groupby('investor', as_index=False).agg(
#                 deals_count=('staging_id', 'nunique'), # Count unique deals
#                 total_invested=('imputed_investment', 'sum'), # Sum imputed investment
#             )
            
#             # Filter and sort the top 5
#             top_sharks = df_sharks_agg.sort_values('total_invested', ascending=False).head(5).reset_index(drop=True)
            
#             # Continue with display logic using the corrected 'top_sharks' DataFrame:
#             cols = st.columns(5)
#             for i, row in top_sharks.iterrows():
#                 with cols[i]:
#                     # use project accent color for names
#                     st.markdown(f"<span style='color:#9D8C5A;font-weight:700'>{row['investor']}</span>", unsafe_allow_html=True)
#                     # FIX: Use corrected column names for deals_count and total_invested
#                     st.metric("Deals", int(row['deals_count']), delta=None)
#                     # format total invested (assumed lakhs in source)
#                     total_inv_val = float(row['total_invested'])
#                     st.write(f"Total: {format_lakhs(total_inv_val)}")
#                     # ... rest of the button code
                    
#                     if st.button(f"Open profile: {row['investor']}", key=f"open_{i}"):
#                         # set navigation request for app.py to consume and then rerun so the new page loads
#                         st.session_state["navigate_to"] = {"page":"Investors", "quick_select_investor": row['investor']}
#                         # force an immediate rerun so the app consumes the navigate_to request
#                         if hasattr(st, "experimental_rerun"):
#                             st.experimental_rerun()
                    
#         else:
#             st.info("No sharks found.")
#     except Exception as e:
#         st.warning("Top sharks load issue: " + str(e))

#     st.markdown("---")
#     st.subheader("Recent Deals")
#     try:
#         # --- RECENT DEALS: fetch the most recent deals by date, with robust staging_id ordering ---
#         recent_deals_sql = """
#         SELECT *
#         FROM public.deals
#         WHERE (%s = 'All' OR season = %s)
#         ORDER BY original_air_date DESC NULLS LAST, 
#                  -- cast staging_id to integer for stable numeric ordering; NULLs last if non-numeric
#                  CASE WHEN staging_id ~ '^[0-9]+$' THEN (staging_id::integer) ELSE NULL END DESC
#         LIMIT %s
#         """
#         # Use integer for limit parameter (e.g., 8). Pass parameters as a tuple to match %s placeholders.
#         df_recent = cached_query(recent_deals_sql, (season, season, int(8)))

#         if not df_recent.empty:
#             # apply quick_search filter client-side if provided
#             q = filters.get("quick_search","").strip()
#             if q:
#                 mask = df_recent.apply(lambda r: r.astype(str).str.contains(q, case=False, na=False).any(), axis=1)
#                 df_recent = df_recent[mask]

#             # format currency for human display
#             display = df_recent.copy()

#             # Ensure episode_number is a proper integer where possible (preserve NaN if not convertible)
#             if 'episode_number' in display.columns:
#                 def safe_int(x):
#                     try:
#                         if pd.isnull(x):
#                             return x
#                         return int(float(x))
#                     except Exception:
#                         return x
#                 display['episode_number'] = display['episode_number'].apply(safe_int)

#             # convert amounts (assumed in lakhs)
#             if 'asked_amount' in display.columns:
#                 display['asked_amount'] = display['asked_amount'].apply(lambda x: format_lakhs(x) if pd.notnull(x) and x != 0 else "-")
#             if 'invested_amount' in display.columns:
#                 display['invested_amount'] = display['invested_amount'].apply(lambda x: format_lakhs(x) if pd.notnull(x) and x != 0 else "-")
#             if 'equity_final' in display.columns:
#                 display['equity_final'] = display['equity_final'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "-")

#             # friendly column renames (only rename columns that exist)
#             rename_map = {}
#             if 'company' in display.columns: rename_map['company'] = 'Company'
#             if 'season' in display.columns: rename_map['season'] = 'Season'
#             if 'episode_number' in display.columns: rename_map['episode_number'] = 'Episode'
#             if 'episode_title' in display.columns: rename_map['episode_title'] = 'Episode Title'
#             if 'asked_amount' in display.columns: rename_map['asked_amount'] = 'Asked (L)'
#             if 'invested_amount' in display.columns: rename_map['invested_amount'] = 'Invested (L)'
#             if 'equity_final' in display.columns: rename_map['equity_final'] = 'Equity (%)'
#             if 'pitchers_city' in display.columns: rename_map['pitchers_city'] = 'City'
#             if 'investors' in display.columns: rename_map['investors'] = 'Investors'

#             display.rename(columns=rename_map, inplace=True)

#             # Re-sort by original_air_date desc then staging_id numeric desc to ensure most recent first
#             if 'original_air_date' in display.columns:
#                 # convert to datetime when possible for proper sorting
#                 try:
#                     display['original_air_date'] = pd.to_datetime(display['original_air_date'], errors='coerce')
#                     display = display.sort_values(by=['original_air_date'], ascending=False)
#                 except Exception:
#                     pass
#             # If staging_id exists, use numeric cast for stable ordering
#             if 'staging_id' in display.columns:
#                 try:
#                     display['_stg_int'] = display['staging_id'].apply(lambda x: int(x) if (pd.notnull(x) and str(x).isdigit()) else -1)
#                     display = display.sort_values(by=['original_air_date' if 'original_air_date' in display.columns else '_stg_int', '_stg_int'], ascending=[False, False])
#                     display.drop(columns=['_stg_int'], inplace=True, errors='ignore')
#                 except Exception:
#                     pass

#             # Choose desired display columns (Episode column will be present if we renamed it)
#             desired_columns = ['Company', 'Season', 'Episode', 'Asked (L)', 'Invested (L)', 'Equity (%)']

#             # Filter the dataframe to only include columns that exist after renaming
#             display_cols = [col for col in desired_columns if col in display.columns]
            
#             display_final = display[display_cols].copy()

#             # choose a column that represents the true deal id
#             id_col = None
#             for candidate in ('staging_id', 'id', 'deal_id'):
#                 if candidate in display.columns:
#                     id_col = candidate
#                     break

#             def _parse_id(x):
#                 """Return integer if numeric-looking, else original string (trimmed)."""
#                 try:
#                     if pd.isnull(x):
#                         return ""
#                     if isinstance(x, (int, float)):
#                         return int(x)
#                     s = str(x).strip()
#                     # if fully numeric, return int, else return trimmed string
#                     return int(s) if s.isdigit() else s
#                 except Exception:
#                     return str(x)

#             if id_col:
#                 # create Id column from the actual id column
#                 display_final['Id'] = display[id_col].apply(_parse_id)
#                 # drop the original id column from the display body if it was among display_cols
#                 cols_without_id = [c for c in display_cols if c != id_col]
#                 # move Id to front
#                 ordered_cols = ['Id'] + cols_without_id
#                 display_final = display_final[ordered_cols]
#             else:
#                 # fallback: create 1-based numeric Id (previous behaviour)
#                 display_final = display_final.reset_index(drop=True)
#                 display_final.index = range(1, len(display_final) + 1)
#                 display_final = display_final.reset_index().rename(columns={'index': 'Id'})
#                 final_cols = ['Id'] + display_cols
#                 display_final = display_final[final_cols]

            
#             # # Select only the desired data columns while preserving sorting (most recent first)
#             # display_final = display[display_cols].copy()

#             # # Reset the index to start at 1, make it a column named 'Id' (1-based)
#             # display_final = display_final.reset_index(drop=True)
#             # display_final.index = range(1, len(display_final) + 1)
#             # display_final = display_final.reset_index().rename(columns={'index': 'Id'})

#             # # Re-order columns to put Id first
#             # final_cols = ['Id'] + display_cols
#             # display_final = display_final[final_cols]

#             # show the dataframe
#             st.dataframe(display_final, use_container_width=True)

#             st.download_button("Download recent deals CSV", display_final.to_csv(index=False), file_name="recent_deals.csv", mime="text/csv")
#             if filters.get("view_sql"):
#                 # FIX: Show the actual SQL being executed now
#                 st.code(recent_deals_sql)
                
#         else:
#             st.info("No recent deals available.")
#     except Exception as e:
#         st.warning("Recent deals load issue: " + str(e))


#     st.markdown("### Quick Insights")
#     insight_cols = st.columns(3)
#     # compute small insights safely
#     try:
#         # --- FIX: T-SQL syntax -> Postgres syntax ---
#         top_sector_sql = """
#             SELECT COALESCE(sector,'Unknown') AS sector, SUM(COALESCE(invested_amount,0)) AS total_invested
#             FROM public.deals -- FIX: dbo.deals -> public.deals
#             GROUP BY COALESCE(sector,'Unknown')
#             ORDER BY total_invested DESC
#             LIMIT 1
#         """
#         # FIX: No parameters needed for this query
#         top_sector_df = cached_query(top_sector_sql, ())
#         # --- END FIX ---
        
#         top_sector = top_sector_df.iloc[0]['sector'] if not top_sector_df.empty else "N/A"
#     except Exception:
#         top_sector = "N/A"

#     try:
#         # average ticket (assume avg_deal_size in kpi if available)
#         if 'kpi' in locals():
#             avg_ticket_val = kpi.avg_deal_size
#         else:
#             # --- FIX: T-SQL syntax -> Postgres syntax ---
#             avg_ticket_sql = "SELECT AVG(COALESCE(invested_amount,0)) AS avg_ticket FROM public.deals"
#             # FIX: No parameters needed for this query
#             avg_ticket_df = cached_query(avg_ticket_sql, ())
#             # --- END FIX ---
            
#             avg_ticket_val = avg_ticket_df.iloc[0]['avg_ticket'] if not avg_ticket_df.empty else None
#     except Exception:
#         avg_ticket_val = None

#     try:
#         # --- FIX: T-SQL syntax -> Postgres syntax ---
#         funded_rates_sql = """
#             SELECT season, SUM(CASE WHEN invested_amount IS NOT NULL THEN 1 ELSE 0 END)*1.0/NULLIF(COUNT(*),0) AS funded_rate
#             FROM public.deals -- FIX: dbo.deals -> public.deals
#             GROUP BY season
#             ORDER BY season
#         """
#         # FIX: No parameters needed for this query
#         funded_rates = cached_query(funded_rates_sql, ())
#         # --- END FIX ---
        
#         if funded_rates is not None and len(funded_rates) >= 2:
#             last = funded_rates.iloc[-1]['funded_rate'] or 0
#             prev = funded_rates.iloc[-2]['funded_rate'] or 0
#             diff_pp = (last - prev) * 100
#             funded_trend = "up" if diff_pp > 0 else ("down" if diff_pp < 0 else "flat")
#             funded_text = f"{diff_pp:+.1f} pp"
#         else:
#             funded_text = "N/A"
#     except Exception:
#         funded_text = "N/A"

#     # render three insight cards with friendly headings + accent color
#     insight_cols[0].markdown(f"<div style='color:#9D8C5A;font-weight:700'>Most Capital Invested</div>", unsafe_allow_html=True)
#     insight_cols[0].write(top_sector)
#     if insight_cols[0].button("Explore related myth"):
#         st.session_state["navigate_to"] = {"page":"Myth Buster"}

#     insight_cols[1].markdown(f"<div style='color:#9D8C5A;font-weight:700'>Average Ticket Size</div>", unsafe_allow_html=True)
#     insight_cols[1].write(format_lakhs(avg_ticket_val) if avg_ticket_val is not None else "N/A")

#     insight_cols[2].markdown(f"<div style='color:#9D8C5A;font-weight:700'>Funded Rate Trend</div>", unsafe_allow_html=True)
#     insight_cols[2].write(funded_text)


# pages/home.py
import streamlit as st
import plotly.express as px
from utils import cached_query, format_currency
import pandas as pd
import re

def page_home(filters):
    st.title("Executive Snapshot")
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
            return f"{v:,.1f} L"
        except Exception:
            return str(val)

    # KPI query (Postgres-friendly)
    try:
        # --- FIXED KPI SQL (Postgres) ---
        # avg_deal_size computed via AVG(NULLIF(invested_amount,0)) to match manual expectation
        # pct_deals_under_1cr computed as percent of funded deals (not percent of all pitches)
        kpi_sql = """
        SELECT
          COUNT(1) AS total_pitches,
          SUM(CASE WHEN invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS funded_deals,
          SUM(COALESCE(invested_amount,0)) AS total_capital_invested,
          AVG(NULLIF(invested_amount,0)) AS avg_deal_size,
          AVG(NULLIF(equity_final,0)) AS avg_equity_accepted,
          SUM(CASE WHEN invested_amount IS NOT NULL AND invested_amount < 100 THEN 1 ELSE 0 END) * 1.0
            / NULLIF(SUM(CASE WHEN invested_amount IS NOT NULL THEN 1 ELSE 0 END),0) AS pct_deals_under_1cr
        FROM public.deals
        WHERE (%s = 'All' OR season = %s)
        """
        kpi_df = cached_query(kpi_sql, (season, season))

        if not kpi_df.empty:
            # cast critical numeric/nullable columns to floats/ints to avoid Decimal issues
            for col in ['total_capital_invested', 'avg_deal_size', 'avg_equity_accepted', 'pct_deals_under_1cr']:
                if col in kpi_df.columns:
                    kpi_df[col] = kpi_df[col].apply(lambda x: float(x) if x is not None else 0.0)

            if 'funded_deals' in kpi_df.columns:
                kpi_df['funded_deals'] = kpi_df['funded_deals'].apply(lambda x: int(x) if x is not None else 0)
            if 'total_pitches' in kpi_df.columns:
                kpi_df['total_pitches'] = kpi_df['total_pitches'].apply(lambda x: int(x) if x is not None else 0)

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
            cols[4].markdown("**Average Equity (%)**", unsafe_allow_html=True)
            cols[4].metric("", f"{(kpi.avg_equity_accepted or 0):.2f}%")

            # 6. Deals < ₹1 Cr (%) — computed as percent of funded deals
            cols[5].markdown("**Deals < ₹1 Cr (%)**", unsafe_allow_html=True)
            cols[5].metric("", f"{(kpi.pct_deals_under_1cr or 0):.2%}")
    except Exception as e:
        st.warning("Could not load KPIs: " + str(e))

    st.markdown("---")

    # Trend by episode: convert stored-proc usage to direct SQL (Postgres)
    try:
        trend_sql = """
        SELECT
            season,
            episode_number,
            SUM(COALESCE(invested_amount, 0)) AS total_invested
        FROM public.deals
        WHERE (%s = 'All' OR season = %s)
        GROUP BY season, episode_number
        ORDER BY season, episode_number
        """
        trend_df = cached_query(trend_sql, (season, season))

        if not trend_df.empty:
            # aggregate to season-level: sum invested and count unique episodes per season
            invest_by_season = trend_df.groupby('season', sort=False)['total_invested'].sum().reset_index()
            counts = trend_df.groupby('season', sort=False)['episode_number'].nunique().reset_index(name='pitches')
            season_summary = invest_by_season.merge(counts, on='season').sort_values('season').reset_index(drop=True)

            # convert totals to floats to avoid Decimal arithmetic issues
            
            # --- REPLACEMENT: Ensure avg_per_pitch exists and then plot using 'season' as x-axis ---
            # Place this where you currently build the season_summary chart.

            # safety: ensure numeric types
            season_summary['total_invested'] = season_summary['total_invested'].apply(lambda v: float(v) if v is not None else 0.0)
            season_summary['pitches'] = season_summary['pitches'].apply(lambda v: int(v) if v is not None else 0)

            # Ensure avg_per_pitch column exists (float). Avoid division-by-zero.
            if 'avg_per_pitch' not in season_summary.columns:
                season_summary['avg_per_pitch'] = season_summary.apply(
                    lambda r: (float(r['total_invested']) / r['pitches']) if (r['pitches'] and r['pitches'] > 0) else 0.0,
                    axis=1
                )
            else:
                # coerce to float and safe divide if any zeros
                season_summary['avg_per_pitch'] = season_summary.apply(
                    lambda r: (float(r['avg_per_pitch']) if r['avg_per_pitch'] is not None else 0.0), axis=1
                )

            # Create a crores version for the primary series (100 L = 1 Cr)
            season_summary['total_invested_cr'] = season_summary['total_invested'].apply(lambda v: float(v) / 100.0 if v is not None else 0.0)

            # Primary trace: total invested (Cr) using season as x
            fig = px.line(season_summary, x='season', y='total_invested_cr', markers=True,
                        title="Total Amount Invested by Season")
            fig.update_traces(name="Total Amount Invested (Cr)", selector=dict(mode='lines+markers'))

            # Secondary trace: avg per pitch (L) also using season as x
            trace2 = px.line(season_summary, x='season', y='avg_per_pitch', markers=True).data[0]
            trace2.update(name='Avg Invested per Pitch (L)', mode='lines+markers',
                        line=dict(color='red', width=3), marker=dict(symbol='circle-open'))
            trace2.update(yaxis='y2')
            fig.add_trace(trace2)

            # annotate number of pitches above primary markers and show value in Cr
            for _, r in season_summary.iterrows():
                fig.add_annotation(x=r['season'], y=r['total_invested_cr'],
                                text=f"{int(r['pitches'])} pitches<br>{r['total_invested_cr']:.2f} Cr",
                                showarrow=False, yshift=12, font=dict(size=11))

            # Friendly axis labels and tidy layout (primary axis now in Cr)
            fig.update_layout(
                xaxis=dict(title='Season', tickangle=-15),
                yaxis=dict(title='Total Amount Invested (Cr)'),
                yaxis2=dict(title='Avg Invested per Pitch (L)', overlaying='y', side='right'),
                legend=dict(title='Series'),
                height=420,
                margin=dict(l=40, r=60, t=64, b=120)
            )

            # numeric-safe axis ranges for primary (in Cr)
            yvals_cr = season_summary["total_invested_cr"].fillna(0).apply(lambda v: float(v) if v is not None else 0.0)
            if len(yvals_cr) and yvals_cr.max() > 0:
                y_min_cr = float(yvals_cr.min())
                y_max_cr = float(yvals_cr.max())
                fig.update_yaxes(range=[max(0.01, y_min_cr - 0.1 * y_max_cr), y_max_cr * 1.05])

            # scale secondary axis (avg_per_pitch in L)
            y2vals = season_summary["avg_per_pitch"].fillna(0).apply(lambda v: float(v) if v is not None else 0.0)
            if len(y2vals) and y2vals.max() > 0:
                fig.update_layout(yaxis2=dict(range=[0, float(y2vals.max() * 1.2)], title='Avg Invested per Pitch (L)', overlaying='y', side='right'))

            st.markdown("""
            <div style='display:flex; justify-content:center; gap: 2rem; margin-bottom: 1rem;'>
            <div style='display:flex; align-items:center;'>
            <div style='width:12px; height:12px; background-color:#636EFA; border-radius:50%; margin-right:5px;'></div>
            <span style='font-size:14px;'>Total Amount Invested (Cr)</span>
            </div>
            <div style='display:flex; align-items:center;'>
            <div style='width:12px; height:12px; background-color:#EF553B; border-radius:50%; margin-right:5px;'></div>
            <span style='font-size:14px;'>Avg Invested per Pitch (L)</span>
            </div>
            </div>
            """, unsafe_allow_html=True)

            st.plotly_chart(fig, use_container_width=True)
            # --- end replacement ---


            if filters.get("view_sql"):
                st.code(trend_sql)
    except Exception as e:
        st.warning("Trend load issue: " + str(e))


    st.markdown("## Sector-wise breakdown")
    # Sector breakdown — exclude zero-total sectors and show download CSV
    sectors_sql = """
    SELECT COALESCE(sector,'Unknown') AS sector, COUNT(*) AS deals, SUM(COALESCE(invested_amount,0)) AS total_invested
    FROM public.deals
    WHERE (%s = 'All' OR season = %s)
    GROUP BY COALESCE(sector,'Unknown')
    HAVING SUM(COALESCE(invested_amount,0)) > 0
    ORDER BY total_invested DESC
    LIMIT 10;
    """
    
    try:
        df_sectors = cached_query(sectors_sql, (season, season))
        if not df_sectors.empty:
            # convert numeric to float for safe plotting, and convert from Lakhs to Crores (divide by 100)
            df_sectors['total_invested'] = df_sectors['total_invested'].apply(lambda x: float(x) if x is not None else 0.0) / 100.0

            fig_s = px.bar(df_sectors, x="sector", y="total_invested", title="Top sectors by capital invested")
            fig_s.update_layout(
                xaxis_title="Sector",
                yaxis_title="Total Capital Invested (Cr)", # Changed (L) to (Cr)
                xaxis_tickangle=-45,
                height=380,
                margin=dict(b=120)
            )

            max_val = df_sectors["total_invested"].max()
            if max_val is not None and float(max_val) > 0:
                # Update y-axis range to start at 0 and use the new max_val (in Cr)
                fig_s.update_yaxes(range=[0, float(max_val) * 1.05])

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
        # Fetch raw deal data for all funded deals matching the season filter
        top_sharks_raw_sql = """
        SELECT 
            d.staging_id, 
            d.invested_amount, 
            di.investor AS investor_raw,
            d.number_of_sharks_in_deal
        FROM public.deals d
        JOIN public.deal_investors di ON d.staging_id = di.staging_id
        WHERE d.invested_amount IS NOT NULL
        AND (%s = 'All' OR d.season = %s);
        """
        top_sharks_raw_df = cached_query(top_sharks_raw_sql, (season, season))

        if not top_sharks_raw_df.empty:
            rows = []
            for _, r in top_sharks_raw_df.iterrows():
                raw_investor = str(r.get('investor_raw') or "")
                # split on comma, semicolon, ampersand, slash, or the word ' and ' (case-insensitive)
                parts = re.split(r',|;|&|/|\\band\\b', raw_investor, flags=re.IGNORECASE)
                investors = [inv.strip() for inv in parts if inv and inv.strip()]

                # Determine shark_count: prefer explicit column, otherwise count split list
                shark_count = None
                try:
                    shark_count = int(r.get('number_of_sharks_in_deal')) if r.get('number_of_sharks_in_deal') not in (None, '') else None
                except Exception:
                    shark_count = None
                if not shark_count or shark_count < 1:
                    shark_count = max(1, len(investors) if len(investors) > 0 else 1)

                # impute per-shark contribution (equal split)
                invested_amt = float(r['invested_amount']) if r['invested_amount'] is not None else 0.0
                imputed_investment = invested_amt / float(shark_count)

                # produce rows
                for inv in investors:
                    rows.append({
                        'investor': inv,
                        'staging_id': r['staging_id'],
                        'imputed_investment': imputed_investment
                    })

            if len(rows) == 0:
                st.info("No sharks found.")
            else:
                df_sharks_agg = pd.DataFrame(rows).groupby('investor', as_index=False).agg(
                    deals_count=('staging_id', 'nunique'),
                    total_invested=('imputed_investment', 'sum')
                )

                top_sharks = df_sharks_agg.sort_values('total_invested', ascending=False).head(5).reset_index(drop=True)

                cols = st.columns(5)
                for i, row in top_sharks.iterrows():
                    with cols[i]:
                        st.markdown(f"<span style='color:#9D8C5A;font-weight:700'>{row['investor']}</span>", unsafe_allow_html=True)
                        st.metric("Deals", int(row['deals_count']), delta=None)
                        total_inv_val = float(row['total_invested'])
                        st.write(f"Total: {format_lakhs(total_inv_val)}")
                        if st.button(f"Open profile: {row['investor']}", key=f"open_{i}"):
                            st.session_state["navigate_to"] = {"page":"Investors", "quick_select_investor": row['investor']}
                            if hasattr(st, "experimental_rerun"):
                                st.experimental_rerun()
        else:
            st.info("No sharks found.")
    except Exception as e:
        st.warning("Top sharks load issue: " + str(e))

    st.markdown("---")
    st.subheader("Recent Deals")
    try:
        recent_deals_sql = """
        SELECT *
        FROM public.deals
        WHERE (%s = 'All' OR season = %s)
        ORDER BY original_air_date DESC NULLS LAST,
                 CASE WHEN staging_id ~ '^[0-9]+$' THEN (staging_id::integer) ELSE NULL END DESC
        LIMIT %s
        """
        df_recent = cached_query(recent_deals_sql, (season, season, int(8)))

        if not df_recent.empty:
            q = filters.get("quick_search","").strip()
            if q:
                mask = df_recent.apply(lambda r: r.astype(str).str.contains(q, case=False, na=False).any(), axis=1)
                df_recent = df_recent[mask]

            display = df_recent.copy()

            if 'episode_number' in display.columns:
                def safe_int(x):
                    try:
                        if pd.isnull(x):
                            return x
                        return int(float(x))
                    except Exception:
                        return x
                display['episode_number'] = display['episode_number'].apply(safe_int)

            if 'asked_amount' in display.columns:
                display['asked_amount'] = display['asked_amount'].apply(lambda x: format_lakhs(x) if pd.notnull(x) and x != 0 else "-")
            if 'invested_amount' in display.columns:
                display['invested_amount'] = display['invested_amount'].apply(lambda x: format_lakhs(x) if pd.notnull(x) and x != 0 else "-")
            if 'equity_final' in display.columns:
                display['equity_final'] = display['equity_final'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "-")

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

            if 'original_air_date' in display.columns:
                try:
                    display['original_air_date'] = pd.to_datetime(display['original_air_date'], errors='coerce')
                    display = display.sort_values(by=['original_air_date'], ascending=False)
                except Exception:
                    pass

            if 'staging_id' in display.columns:
                try:
                    display['_stg_int'] = display['staging_id'].apply(lambda x: int(x) if (pd.notnull(x) and str(x).isdigit()) else -1)
                    display = display.sort_values(by=['original_air_date' if 'original_air_date' in display.columns else '_stg_int', '_stg_int'], ascending=[False, False])
                    display.drop(columns=['_stg_int'], inplace=True, errors='ignore')
                except Exception:
                    pass

            desired_columns = ['Company', 'Season', 'Episode', 'Asked (L)', 'Invested (L)', 'Equity (%)']
            display_cols = [col for col in desired_columns if col in display.columns]
            display_final = display[display_cols].copy()

            id_col = None
            for candidate in ('staging_id', 'id', 'deal_id'):
                if candidate in display.columns:
                    id_col = candidate
                    break

            def _parse_id(x):
                try:
                    if pd.isnull(x):
                        return ""
                    if isinstance(x, (int, float)):
                        return int(x)
                    s = str(x).strip()
                    return int(s) if s.isdigit() else s
                except Exception:
                    return str(x)

            if id_col:
                display_final['Id'] = display[id_col].apply(_parse_id)
                cols_without_id = [c for c in display_cols if c != id_col]
                ordered_cols = ['Id'] + cols_without_id
                display_final = display_final[ordered_cols]
            else:
                display_final = display_final.reset_index(drop=True)
                display_final.index = range(1, len(display_final) + 1)
                display_final = display_final.reset_index().rename(columns={'index': 'Id'})
                final_cols = ['Id'] + display_cols
                display_final = display_final[final_cols]

            st.dataframe(display_final, use_container_width=True)

            st.download_button("Download recent deals CSV", display_final.to_csv(index=False), file_name="recent_deals.csv", mime="text/csv")
            if filters.get("view_sql"):
                st.code(recent_deals_sql)
        else:
            st.info("No recent deals available.")
    except Exception as e:
        st.warning("Recent deals load issue: " + str(e))


    st.markdown("### Quick Insights")
    insight_cols = st.columns(3)
    try:
        top_sector_sql = """
            SELECT COALESCE(sector,'Unknown') AS sector, SUM(COALESCE(invested_amount,0)) AS total_invested
            FROM public.deals
            GROUP BY COALESCE(sector,'Unknown')
            ORDER BY total_invested DESC
            LIMIT 1
        """
        top_sector_df = cached_query(top_sector_sql, ())
        top_sector = top_sector_df.iloc[0]['sector'] if not top_sector_df.empty else "N/A"
    except Exception:
        top_sector = "N/A"

    try:
        if 'kpi' in locals():
            avg_ticket_val = kpi.avg_deal_size
        else:
            avg_ticket_sql = "SELECT AVG(COALESCE(invested_amount,0)) AS avg_ticket FROM public.deals"
            avg_ticket_df = cached_query(avg_ticket_sql, ())
            avg_ticket_val = avg_ticket_df.iloc[0]['avg_ticket'] if not avg_ticket_df.empty else None
    except Exception:
        avg_ticket_val = None

    try:
        funded_rates_sql = """
            SELECT season, SUM(CASE WHEN invested_amount IS NOT NULL THEN 1 ELSE 0 END)*1.0/NULLIF(COUNT(*),0) AS funded_rate
            FROM public.deals
            GROUP BY season
            ORDER BY season
        """
        funded_rates = cached_query(funded_rates_sql, ())
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

    insight_cols[0].markdown(f"<div style='color:#9D8C5A;font-weight:700'>Most Capital Invested</div>", unsafe_allow_html=True)
    insight_cols[0].write(top_sector)
    if insight_cols[0].button("Explore related myth"):
        st.session_state["navigate_to"] = {"page":"Myth Buster"}

    insight_cols[1].markdown(f"<div style='color:#9D8C5A;font-weight:700'>Average Ticket Size</div>", unsafe_allow_html=True)
    insight_cols[1].write(format_lakhs(avg_ticket_val) if avg_ticket_val is not None else "N/A")

    insight_cols[2].markdown(f"<div style='color:#9D8C5A;font-weight:700'>Funded Rate Trend</div>", unsafe_allow_html=True)
    insight_cols[2].write(funded_text)
