# pages/equity.py
import streamlit as st
from utils import cached_query, format_currency
import pandas as pd
import numpy as np
import plotly.express as px

def get_sectors():
    df = cached_query("SELECT DISTINCT sector FROM deals ORDER BY sector")
    return df['sector'].dropna().tolist()

def get_investors():
    df = cached_query("SELECT DISTINCT investor FROM deal_investors ORDER BY investor")
    return df['investor'].dropna().tolist()

def compute_postmoney_from_equity(amount, equity_pct):
    """
    Given amount invested and equity percentage (e.g. 10 for 10%), compute:
    - post_money = amount / (equity_pct/100)
    - pre_money = post_money - amount
    Note: this function expects 'amount' in the same units as the UI inputs (we now use lakhs).
    """
    try:
        if equity_pct is None or equity_pct <= 0:
            return None, None
        post = amount / (equity_pct / 100.0)
        pre = post - amount
        return pre, post
    except Exception:
        return None, None

def compute_implied_equity(amount, pre_money):
    """
    Given amount and pre-money, compute implied equity% = amount / (pre_money + amount) * 100
    """
    try:
        if pre_money is None:
            return None
        post = pre_money + amount
        if post == 0:
            return None
        return (amount / post) * 100.0
    except Exception:
        return None

# compatibility_score intentionally kept (unused) for future use
def compatibility_score(offered_amount, offered_equity_pct, investor):
    """
    Compute a compatibility score 0-100 between a founder's offer and the investor's historical behaviour.
    Uses vw_investor_summary (median equity and avg_ticket). Weighted: equity 0.6, amount 0.4.
    Kept here for future features; not used in the UI per current requirements.
    """
    if not investor:
        return None
    try:
        row = cached_query("SELECT median_invested_equity, avg_ticket FROM vw_investor_summary WHERE investor = :investor", {"investor": investor})
        if row.empty:
            return None
        r = row.iloc[0]
        median_equity = r.median_invested_equity if not pd.isnull(r.median_invested_equity) else None
        avg_ticket = r.avg_ticket if not pd.isnull(r.avg_ticket) else None

        # equity score
        if median_equity and offered_equity_pct is not None:
            equity_diff_ratio = min(abs(offered_equity_pct - median_equity) / max(median_equity, 1), 1.0)
            equity_score = 100.0 * (1 - equity_diff_ratio)
        else:
            equity_score = 50.0

        # amount score
        if avg_ticket and offered_amount is not None:
            amount_diff_ratio = min(abs(offered_amount - avg_ticket) / max(avg_ticket, 1), 1.0)
            amount_score = 100.0 * (1 - amount_diff_ratio)
        else:
            amount_score = 50.0

        score = 0.6 * equity_score + 0.4 * amount_score
        return int(round(score))
    except Exception:
        return None

def page_equity(filters):
    # st.title("Equity & Valuation Calculator")
    st.markdown("<h1 style='margin:0;padding:0'>Financial Modeling</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='margin:0;padding:0'>Equity & Valuation Calculator</h3>", unsafe_allow_html=True)
    season = filters.get("season", "All")

    # --- Helper: format amounts assumed to be in lakhs (L) ---
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
            if v >= 100:  # 100 L == 1 Cr
                crores = v / 100.0
                return f"{crores:.2f} Cr ({int(round(v)):,} L)"
            if v.is_integer():
                return f"{int(v):,} L"
            return f"{v:,.2f} L"
        except Exception:
            return str(val)

    # Inputs: founder inputs (amounts in lakhs)
    with st.form("equity_form"):
        st.markdown(f"<h3 style='color:#9D8C5A'>Founder inputs</h3>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)

        # NOTE: amounts on this app are shown/entered in lakhs (L)
        sector = col1.selectbox("Sector", [""] + get_sectors())
        asked_amount = col1.number_input("Amount requested (L)", min_value=0.0, value=10.0, step=1.0, format="%.2f")
        equity_offered = col1.number_input("Equity offered (%)", min_value=0.0, max_value=100.0, value=10.0, step=0.1)

        mode = col2.radio("Valuation input mode", ["Infer pre/post-money from amount & equity", "I will provide Pre-money value"])
        pre_money = None
        if mode == "I will provide Pre-money value":
            pre_money = col2.number_input("Pre-money valuation (L)", min_value=0.0, value=0.0, step=1.0, format="%.2f")

        desired = col2.radio("Input type", ["Founder asks (pre/post implied)", "I want Post-money target"])
        # optional: choose an investor to compare to (kept but compatibility removed)
        investor = col3.selectbox("Compare to investor (optional)", [""] + get_investors())

        submitted = st.form_submit_button("Calculate")

    # Upon submit, compute valuations and outputs
    if submitted:
        # compute pre/post based on mode & inputs
        if mode == "I will provide Pre-money value" and pre_money and pre_money > 0:
            # values are in lakhs
            post_money = pre_money + asked_amount
            implied_equity = compute_implied_equity(asked_amount, pre_money)
            inferred_pre_money = pre_money
            inferred_post_money = post_money
        else:
            inferred_pre_money, inferred_post_money = compute_postmoney_from_equity(asked_amount, equity_offered)
            implied_equity = equity_offered  # founder offered equity

        # show instant results (formatted in lakhs)
        st.markdown(f"<h3 style='color:#9D8C5A'>Instant result</h3>", unsafe_allow_html=True)
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Pre-money (L)", format_lakhs(inferred_pre_money))
        col_b.metric("Post-money (L)", format_lakhs(inferred_post_money))
        dilution = equity_offered if equity_offered else (implied_equity if implied_equity else 0)
        col_c.metric("Founder ownership after deal", f"{100 - dilution:.2f}%")

        # Cap table — friendly view
        st.markdown("### Cap Table — Before & After")
        founders_pct_before = 100.0
        investors_pct_before = 0.0
        founders_pct_after = 100.0 - dilution
        investors_pct_after = dilution

        cap_before = pd.DataFrame([{"Entity":"Founders", "Ownership (%)": founders_pct_before},
                                   {"Entity":"Investors", "Ownership (%)": investors_pct_before}])
        cap_after = pd.DataFrame([{"Entity":"Founders", "Ownership (%)": founders_pct_after},
                                  {"Entity":"Investors", "Ownership (%)": investors_pct_after}])

        col1, col2 = st.columns(2)
        col1.write("Before deal")
        cap_before['Ownership (%)'] = cap_before['Ownership (%)'].apply(lambda x: f"{x:.2f}%")
        cap_before.index = range(1, len(cap_before) + 1)
        col1.dataframe(cap_before, use_container_width=True)

        col2.write("After deal")
        cap_after['Ownership (%)'] = cap_after['Ownership (%)'].apply(lambda x: f"{x:.2f}%")
        cap_after.index = range(1, len(cap_after) + 1)
        col2.dataframe(cap_after, use_container_width=True)

        # Scenario slider: range of equity % and show dilution vs founder ownership
        st.markdown("### Scenario: Equity range analysis")
        scen_min, scen_max = st.slider("Equity % range to simulate", 1.0, 50.0, (max(1.0, equity_offered - 5.0), min(50.0, equity_offered + 5.0)), step=0.5)
        scen_points = np.linspace(scen_min, scen_max, num=40)
        df_scen = pd.DataFrame({"equity_pct": scen_points})
        df_scen["post_money"] = df_scen["equity_pct"].apply(lambda ep: (asked_amount / (ep/100.0)) if ep>0 else np.nan)
        df_scen["founder_ownership_pct"] = 100.0 - df_scen["equity_pct"]
        fig = px.line(df_scen, x="equity_pct", y="founder_ownership_pct", title="Founder ownership vs Equity % accepted", markers=False)
        fig.update_layout(xaxis_title="Equity offered (%)", yaxis_title="Founder ownership (%)", height=420)
        st.plotly_chart(fig, use_container_width=True)

        # Comparable deals (SQL-driven) — friendly table
        st.markdown("### Comparable Deals")
        if not sector:
            st.info("Select a sector to find comparable deals.")
        else:
            try:
                comps = cached_query("""SELECT company, season, invested_amount, equity_final FROM deals
                                     WHERE sector = :sector AND invested_amount BETWEEN :amt * 0.5
                                     AND :amt * 1.5 AND (:season = 'All' OR season = :season)
                                     ORDER BY ABS(invested_amount - :amt)  -- Find closest ticket size LIMIT 5 """, 
                                     {"sector": sector, "amt": asked_amount, "season": season})
                
                # --- Fetch investors for comps (SQLite compatible aggregation) ---
                if not comps.empty:
                    # Ensure 'id' column is available from the simplified query
                    # The query in Line 236 replacement needs to include 'id' (which it does not explicitly in the previous step, so we assume it's available or should be included in the select * in the new query)
                    ids = comps['id'].astype(int).tolist()
                    ids_csv = ",".join(str(int(x)) for x in ids)
                    inv_sql_comps = f"""
                    SELECT d.id as deal_id,
                    GROUP_CONCAT(di2.investor, ', ') AS investors
                    FROM deals d
                    JOIN deal_investors di2 ON di2.deal_id = d.id
                    WHERE d.id IN ({ids_csv})
                    GROUP BY d.id;
                    """
                    inv_map_comps = cached_query(inv_sql_comps)
                    if not inv_map_comps.empty:
                        inv_map_comps = inv_map_comps.set_index('deal_id')['investors'].to_dict()
                        comps['investors'] = comps['id'].apply(lambda i: inv_map_comps.get(i, ""))
                    else:
                        comps['investors'] = ""
                # --- End Investor Fetch ---

                # comps = cached_query("EXEC dbo.sp_comps_by_sector @sector = :sector, @target_amount = :amt, @season = :season, @limit = :limit",
                #                      {"sector": sector, "amt": asked_amount, "season": season, "limit": 5})
                if comps is None or comps.empty:
                    st.info("No comparable deals found in this sector.")
                else:
                    comps_display = comps.copy()
                    # invested amount formatting (lakhs)
                    if 'invested_amount' in comps_display.columns:
                        comps_display['invested_amount'] = comps_display['invested_amount'].apply(lambda x: format_lakhs(x) if pd.notnull(x) and x!=0 else "-")
                    # normalize investor lists (split combined strings into cleaned individual names)
                    # if 'investors' in comps_display.columns:
                    #     def normalize_inv(cell):
                    #         if not cell or pd.isnull(cell):
                    #             return ""
                    #         parts = [p.strip() for p in str(cell).replace(';',',').split(',') if p.strip()]
                    #         seen = []
                    #         for p in parts:
                    #             if p not in seen:
                    #                 seen.append(p)
                    #         return ", ".join(seen)
                    #     comps_display['investors'] = comps_display['investors'].apply(normalize_inv)
                    # rename columns to friendly names

                    if 'investors' not in comps_display.columns:
                        comps_display['investors'] = ''
                    
                    sim_rename = {}
                    if 'company' in comps_display.columns: sim_rename['company'] = 'Company'
                    if 'season' in comps_display.columns: sim_rename['season'] = 'Season'
                    if 'invested_amount' in comps_display.columns: sim_rename['invested_amount'] = 'Invested (L)'
                    if 'equity_final' in comps_display.columns: sim_rename['equity_final'] = 'Equity (%)'
                    if 'investors' in comps_display.columns: sim_rename['investors'] = 'Investors'
                    comps_display.rename(columns=sim_rename, inplace=True)
                    comps_display.index = range(1, len(comps_display) + 1)
                    cols_to_show = [c for c in ['Company','Season','Invested (L)','Equity (%)','Investors'] if c in comps_display.columns]
                    st.dataframe(comps_display[cols_to_show], use_container_width=True)
            except Exception as e:
                st.warning("Could not fetch comparables: " + str(e))

        # Auto-fill mechanism removed (per requirement): no "use comp" buttons.

        # Investor compatibility removed (per requirement).

        # Explanation static box (styled)
        st.markdown(f"<h3 style='color:#9D8C5A'>Explanation</h3>", unsafe_allow_html=True)
        st.write("""
        Equity calculations (brief): 
        - If an investor gives ₹A for E% equity, the **post-money valuation** implied is A / (E/100).
        - **Pre-money valuation** = post-money − A.
        - Founder ownership after the deal = 100% − E%.
        This calculator shows these values and lets you compare counteroffers and similar historical deals to justify terms.
        """)
