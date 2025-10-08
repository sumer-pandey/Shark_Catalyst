# pages/deals.py
import streamlit as st
from utils import cached_query, format_currency
import pandas as pd

st.set_page_config(layout="wide")

def _get_min_max(column, season):
    row = cached_query(f"SELECT MIN({column}) AS mn, MAX({column}) AS mx FROM dbo.deals WHERE (:season = 'All' OR season = :season)", {"season": season})
    if row is None or row.empty:
        return 0, 0
    return (row.iloc[0].mn or 0), (row.iloc[0].mx or 0)

def page_deals(filters):
    st.title("Deal Explorer")
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


    quick_search = filters.get("quick_search", "").strip()

    # Check for prefill from other pages (Myth Buster sets this)
    prefill = None
    if "deal_filters_prefill" in st.session_state:
        prefill = st.session_state.pop("deal_filters_prefill", None)

    # --- Sidebar-esque filter area (top of page) ---
    
    with st.expander("Advanced filters", expanded=True):
        # Row 1
        cols1 = st.columns(4)
        seasons_opts = ["All", "Season 1", "Season 2", "Season 3", "Season 4"]
        sel_season_default_index = 0
        if prefill and "season" in prefill and prefill["season"] in seasons_opts:
            sel_season_default_index = seasons_opts.index(prefill["season"])
        sel_season = cols1[0].selectbox("Season (repeat)", seasons_opts, index=sel_season_default_index)

        # Sectors
        sectors_df = cached_query("SELECT DISTINCT sector FROM dbo.deals WHERE sector IS NOT NULL ORDER BY sector")
        sector_opts = sectors_df['sector'].dropna().tolist() if not sectors_df.empty else []
        sel_sectors_default = prefill.get("sectors", []) if prefill and "sectors" in prefill else []
        sel_sectors = cols1[1].multiselect("Sector (multi)", options=sector_opts, default=sel_sectors_default)

        # Investors — fix: split comma-separated values into individual names and sort
        inv_raw_df = cached_query("SELECT DISTINCT investor FROM dbo.deal_investors WHERE investor IS NOT NULL ORDER BY investor")
        inv_opts = []
        try:
            if not inv_raw_df.empty:
                raw_list = inv_raw_df['investor'].dropna().tolist()
                inv_set = set()
                for s in raw_list:
                    # split on comma and semicolon to handle combined strings
                    parts = [p.strip() for seg in [s] for p in seg.replace(';',',').split(',') if p.strip()]
                    inv_set.update(parts)
                inv_opts = sorted(inv_set)
        except Exception:
            inv_opts = []
        sel_investors_default = prefill.get("investors", []) if prefill and "investors" in prefill else []
        sel_investors = cols1[2].multiselect("Investor(s)", options=inv_opts, default=sel_investors_default)

        # Funded flag
        sel_funded_default = "Any"
        if prefill and "funded" in prefill:
            if prefill["funded"] is True:
                sel_funded_default = "Funded"
            elif prefill["funded"] is False:
                sel_funded_default = "Not Funded"
        sel_funded = cols1[3].selectbox("Funded?", ["Any", "Funded", "Not Funded"], index=["Any","Funded","Not Funded"].index(sel_funded_default))

        # Row 2
        cols2 = st.columns(4)
        # invested amount range (DB min/max)
        min_inv, max_inv = _get_min_max("invested_amount", sel_season)
        if max_inv <= 0:
            max_inv = 1000000
        sel_min_inv_default = int(prefill.get("min_invested", min_inv)) if prefill and "min_invested" in prefill else int(min_inv)
        sel_max_inv_default = int(prefill.get("max_invested", max_inv)) if prefill and "max_invested" in prefill else int(max_inv)
        sel_min_inv, sel_max_inv = cols2[0].slider("Invested amount range (₹)", 0, int(max_inv*2), (sel_min_inv_default, sel_max_inv_default), step=10000)

        # asked amount range
        min_ask, max_ask = _get_min_max("asked_amount", sel_season)
        if max_ask <= 0:
            max_ask = 1000000
        sel_min_ask_default = int(prefill.get("min_asked", min_ask)) if prefill and "min_asked" in prefill else int(min_ask)
        sel_max_ask_default = int(prefill.get("max_asked", max_ask)) if prefill and "max_asked" in prefill else int(max_ask)
        sel_min_ask, sel_max_ask = cols2[1].slider("Asked amount range (₹)", 0, int(max_ask*2), (sel_min_ask_default, sel_max_ask_default), step=10000)

        # city / metro
        sel_city_type_default = prefill.get("city_type", "All") if prefill else "All"
        sel_city_type = cols2[2].selectbox("City type", ["All", "Metro", "Non-metro"], index=["All","Metro","Non-metro"].index(sel_city_type_default))

        # min founder count
        max_founders_row = cached_query("SELECT MAX(ISNULL(founder_count,0)) AS mx FROM dbo.deals")
        max_founders = int(max_founders_row.iloc[0].mx or 5) if not max_founders_row.empty else 5
        sel_min_founder_default = int(prefill.get("min_founder_count", 0)) if prefill else 0
        sel_min_founder = cols2[3].slider("Min founder count", 0, max(10, max_founders), sel_min_founder_default, step=1)

        # Row 3
        cols3 = st.columns(4)
        sel_female_default = "Any"
        if prefill and "female_presenter" in prefill:
            sel_female_default = "Yes" if prefill["female_presenter"] else "No"
        sel_female = cols3[0].selectbox("Female founder present?", ["Any", "Yes", "No"], index=["Any","Yes","No"].index(sel_female_default))

        # Sort mapping — user-friendly labels mapped to backend fields
        sort_map = {
            "Invested amount (L)": "invested_amount",
            "Asked amount (L)": "asked_amount",
            "Deal date": "deal_date",
            "Equity (%)": "equity_final"
        }
        # figure default when prefill contains backend name
        sort_label_default = next((k for k,v in sort_map.items() if v == (prefill.get("sort_by") if prefill else None)), "Invested amount (L)")
        sort_by_label = cols3[1].selectbox("Sort by", list(sort_map.keys()), index=list(sort_map.keys()).index(sort_label_default))
        sort_by = sort_map.get(sort_by_label, "invested_amount")

        # Sort direction label mapping
        sort_dir_map = {"Descending":"DESC", "Ascending":"ASC"}
        sort_dir_label_default = "Descending" if (prefill and prefill.get("sort_dir","DESC") == "DESC") else "Descending"
        sort_dir_label = cols3[2].selectbox("Sort order", list(sort_dir_map.keys()), index=list(sort_dir_map.keys()).index(sort_dir_label_default))
        sort_dir = sort_dir_map.get(sort_dir_label, "DESC")

        # page size control
        page_size_default = int(prefill.get("page_size", 25)) if prefill and "page_size" in prefill else 25
        page_size = cols3[3].selectbox("Page size", [10, 25, 50, 100], index=[10,25,50,100].index(page_size_default))


    # ensure st.session_state offset exists
    if "deals_offset" not in st.session_state:
        st.session_state["deals_offset"] = 0

    # Reset offset if filters changed — track last filters
    current_filters_key = str((sel_season, tuple(sel_sectors), tuple(sel_investors), sel_funded, sel_min_inv, sel_max_inv, sel_min_ask, sel_max_ask, sel_city_type, sel_min_founder, sel_female, sort_by, sort_dir))
    if st.session_state.get("deals_last_filters") != current_filters_key:
        st.session_state["deals_offset"] = 0
        st.session_state["deals_last_filters"] = current_filters_key

    # map selections to proc params
    sector_csv = ",".join(sel_sectors) if sel_sectors else None
    investor_csv = ",".join(sel_investors) if sel_investors else None
    funded_flag = -1
    if sel_funded == "Funded":
        funded_flag = 1
    elif sel_funded == "Not Funded":
        funded_flag = 0

    female_flag = -1
    if sel_female == "Yes": female_flag = 1
    elif sel_female == "No": female_flag = 0

    # call server-side stored proc
    try:
        df = cached_query(
            "EXEC dbo.sp_deals_search_ext @season = :season, @sector_csv = :sector_csv, @investor_csv = :investor_csv, @min_invested = :min_inv, @max_invested = :max_inv, @funded_flag = :funded_flag, @city_type = :city_type, @min_founder_count = :min_founder, @female_flag = :female_flag, @sort_by = :sort_by, @sort_dir = :sort_dir, @limit = :limit, @offset = :offset",
            {
                "season": sel_season,
                "sector_csv": sector_csv,
                "investor_csv": investor_csv,
                "min_inv": sel_min_inv,
                "max_inv": sel_max_inv,
                "funded_flag": funded_flag,
                "city_type": sel_city_type,
                "min_founder": sel_min_founder,
                "female_flag": female_flag,
                "sort_by": sort_by,
                "sort_dir": sort_dir,
                "limit": page_size,
                "offset": int(st.session_state["deals_offset"])
            }
        )
    except Exception as e:
        st.error("Search failed (server): " + str(e))
        return

    # quick-search client-side filtering on the returned page
    if quick_search:
        mask = df.apply(lambda r: r.astype(str).str.contains(quick_search, case=False, na=False).any(), axis=1)
        df = df[mask]

    # fetch investor lists for the current page rows
    if not df.empty:
        ids = df['id'].astype(int).tolist()
        ids_csv = ",".join(str(int(x)) for x in ids)
        inv_sql = f"""
        SELECT d.id as deal_id,
          (SELECT STUFF((SELECT ',' + di2.investor FROM dbo.deal_investors di2 WHERE di2.deal_id = d.id FOR XML PATH('')),1,1,'')) AS investors
        FROM dbo.deals d
        WHERE d.id IN ({ids_csv});
        """
        try:
            inv_map = cached_query(inv_sql)
            if not inv_map.empty:
                inv_map = inv_map.set_index('deal_id')['investors'].to_dict()
                df['investors'] = df['id'].apply(lambda i: inv_map.get(i, ""))
            else:
                df['investors'] = ""
        except Exception as e:
            df['investors'] = ""
    else:
        df['investors'] = []

    current_page = int(st.session_state["deals_offset"] / page_size) + 1
    st.markdown(f"<h2 style='color:#E0E0E0'>Results - (Page {current_page})</h2>", unsafe_allow_html=True)

    if df.empty:
        st.info("No deals found with the applied filters.")
    else:
        disp = df.copy()
        # format monetary fields (assumed in lakhs)
        if 'asked_amount' in disp.columns:
            disp['asked_amount'] = disp['asked_amount'].apply(lambda x: format_lakhs(x) if pd.notnull(x) and x != 0 else "-")
        if 'invested_amount' in disp.columns:
            disp['invested_amount'] = disp['invested_amount'].apply(lambda x: format_lakhs(x) if pd.notnull(x) and x != 0 else "-")
        if 'equity_final' in disp.columns:
            disp['equity_final'] = disp['equity_final'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "-")

        # friendly column names (only rename columns that exist)
        rename_map = {
            'id':'ID',
            'company':'Company',
            'sector':'Sector',
            'season':'Season',
            'episode_number':'Episode',
            'asked_amount':'Asked (L)',
            'invested_amount':'Invested (L)',
            'equity_final':'Equity (%)',
            'investors':'Investors',
            'pitchers_city':'City'
        }
        rename_actual = {k:v for k,v in rename_map.items() if k in disp.columns}
        disp.rename(columns=rename_actual, inplace=True)

        # Restrict to only shown columns, for consistent display/download
        ordered_cols = ['ID','Company','Sector','Season','Episode','Asked (L)','Invested (L)','Equity (%)','Investors','City']
        display_present = [c for c in ordered_cols if c in disp.columns]
        disp = disp[display_present]

        # 1-based index for user-friendly numbering and assign index name
        disp.index = range(1, len(disp) + 1)
        disp.index.name = "Row"

        st.dataframe(disp, use_container_width=True)

        csv_data = disp.to_csv(index=False)
        st.download_button("Download current page CSV", csv_data, file_name="deals_page.csv", mime="text/csv", key=f"download_deals_page_offset_{st.session_state['deals_offset']}")

        colp = st.columns([1,1,6])
        with colp[0]:
            if st.button("Prev") and st.session_state["deals_offset"] >= page_size:
                st.session_state["deals_offset"] -= page_size
                # update URL query params using the current (non-deprecated) API
                st.query_params(_deals_offset=st.session_state["deals_offset"])
        with colp[1]:
            if st.button("Next"):
                st.session_state["deals_offset"] += page_size
                st.query_params(_deals_offset=st.session_state["deals_offset"])

        st.markdown("---")
        st.markdown(f"<h3 style='color:#E0E0E0'>Deal Details</h3>", unsafe_allow_html=True)
        # company selection with id annotation for clarity (shows "Company Name (ID:123)")
        detail_options = []
        for _, row in df[['id','company']].iterrows():
            cid = int(row['id'])
            name = row['company'] if pd.notnull(row['company']) else f"Deal {cid}"
            detail_options.append(f"{name} (ID:{cid})")
        selected_option = st.selectbox("Select company (ID)", options=detail_options)
        selected_id = None
        if selected_option:
            # parse ID from the selected string
            try:
                selected_id = int(selected_option.split("ID:")[-1].strip().rstrip(')'))
            except Exception:
                selected_id = None

        if selected_id:
            try:
                detail_sql = "SELECT * FROM dbo.deals WHERE id = :did"
                detail = cached_query(detail_sql, {"did": int(selected_id)})
                if not detail.empty:
                    d = detail.iloc[0].to_dict()
                    st.markdown(f"### {d.get('company','-')} (Deal ID: {d.get('id')})")
                    st.write("Season:", d.get('season'), " Episode:", d.get('episode_number'))
                    st.write("City:", d.get('pitchers_city'))
                    st.write("Asked:", format_lakhs(d.get('asked_amount')), " Invested:", format_lakhs(d.get('invested_amount')))
                    st.write("Equity asked:", (f"{d.get('equity_asked'):.2f}%" if d.get('equity_asked') is not None else "-"), " Equity given:", (f"{d.get('equity_final'):.2f}%" if d.get('equity_final') is not None else "-"))
                    st.write("Founder count:", d.get('founder_count'), " Female presenters:", d.get('female_presenters'))
                    st.markdown("**Business description**")
                    st.write(d.get('business_description','-'))

                    inv_sql2 = """
                    SELECT STUFF((SELECT ',' + di2.investor FROM dbo.deal_investors di2 WHERE di2.deal_id = d.id FOR XML PATH('')),1,1,'') AS investors
                    FROM dbo.deals d WHERE d.id = :did;
                    """
                    inv_row = cached_query(inv_sql2, {"did": int(selected_id)})
                    if not inv_row.empty:
                        st.write("Investors:", inv_row.iloc[0].investors or "-")

                    sector = d.get('sector')
                    invested_amt = d.get('invested_amount') or 0
                    if sector:
                        sim_df = cached_query("EXEC dbo.sp_similar_deals @sector = :sector, @target_amount = :amt, @limit = 5", {"sector": sector, "amt": invested_amt, "limit": 5})
                        st.subheader("Similar deals")
                        if not sim_df.empty:
                            # format similar deals columns
                            if 'invested_amount' in sim_df.columns:
                                sim_df['invested_amount'] = sim_df['invested_amount'].apply(lambda x: format_lakhs(x) if pd.notnull(x) and x!=0 else "-")
                            if 'equity_final' in sim_df.columns:
                                sim_df['equity_final'] = sim_df['equity_final'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "-")
                            # friendly column names
                            sim_rename = {}
                            if 'company' in sim_df.columns: sim_rename['company'] = 'Company'
                            if 'season' in sim_df.columns: sim_rename['season'] = 'Season'
                            if 'invested_amount' in sim_df.columns: sim_rename['invested_amount'] = 'Invested (L)'
                            if 'equity_final' in sim_df.columns: sim_rename['equity_final'] = 'Equity (%)'
                            sim_df.rename(columns=sim_rename, inplace=True)
                            sim_df.index = range(1, len(sim_df) + 1)
                            st.dataframe(sim_df[[c for c in ['Company','Season','Invested (L)','Equity (%)'] if c in sim_df.columns]], use_container_width=True)
                        else:
                            st.info("No similar deals found.")
                    else:
                        st.info("Sector not available for similar-deals lookup.")

                    st.download_button("Download deal detail (CSV)", pd.DataFrame([d]).to_csv(index=False), file_name=f"deal_{selected_id}.csv", mime="text/csv", key=f"download_deal_{selected_id}")
                else:
                    st.info("No detail found for selected deal.")
            except Exception as ex:
                st.error("Could not load deal detail: " + str(ex))

