import re
import pandas as pd
import numpy as np
from pathlib import Path

RAW = Path(__file__).parent / "sharktank_data.csv"
DEALS_OUT = Path(__file__).parent / "deals_clean.csv"
INV_OUT = Path(__file__).parent / "deal_investors_clean.csv"

# --- Helper parsers ---
def parse_amount(s):
    """Parse messy monetary text into numeric INR value (float)."""
    if s is None:
        return np.nan
    s = str(s).strip()
    if s == "" or s.lower() in {"nan", "none", "n/a", "-"}:
        return np.nan
    s_low = s.lower()
    # remove common currency tokens
    s_low = s_low.replace("₹", " ").replace("inr", " ").replace("rs.", " ").replace("rs", " ")
    # normalize commas and multiple spaces
    s_low = s_low.replace(",", " ")
    s_low = re.sub(r"\s+", " ", s_low).strip()
    # find first number token
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)", s_low)
    if not m:
        return np.nan
    num = float(m.group(1))
    # detect multipliers
    if "crore" in s_low or "cr" in s_low:
        num = num * 10_000_000  # crore -> 10^7
    elif "lakh" in s_low or "lac" in s_low:
        num = num * 100_000      # lakh -> 10^5
    elif re.search(r"\bk\b", s_low) or s_low.endswith("k"):
        num = num * 1_000
    return num

def parse_percent(s):
    """Parse percent like '12%' or '12.5' into float (12.0 or 12.5)."""
    if s is None:
        return np.nan
    s = str(s).strip()
    if s == "" or s.lower() in {"nan", "none", "n/a", "-"}:
        return np.nan
    s = s.replace("%", "").replace(",", "").strip()
    try:
        return float(s)
    except:
        # fallback: find number
        m = re.search(r"([0-9]+(?:\.[0-9]+)?)", s)
        return float(m.group(1)) if m else np.nan

def parse_int(s):
    try:
        return int(float(str(s).strip()))
    except:
        return np.nan

def parse_bool(s):
    if s is None:
        return 0
    s = str(s).strip().lower()
    if s in {"yes", "true", "1", "y", "t"}:
        return 1
    return 0

def parse_date(s):
    try:
        return pd.to_datetime(s, errors="coerce").date()
    except:
        return None

def parse_float_or_nan(s):
    """Safely convert a string to float, returning NaN on failure."""
    try:
        return float(str(s))
    except (ValueError, TypeError):
        return np.nan

# --- Load raw CSV ---
raw = pd.read_csv(RAW, dtype=str, keep_default_na=False).fillna("")
# create a stable staging id (1-based)
raw["staging_id"] = range(1, len(raw) + 1)

# --- Build deals dataframe (one row per pitch) ---
deals = pd.DataFrame()
deals["staging_id"] = raw["staging_id"]
deals["company"] = raw.get("Startup Name", "")
deals["season"] = raw.get("Season Number", "").apply(lambda x: ("Season " + x.strip()) if str(x).strip() != "" else None)
deals["episode_number"] = raw.get("Episode Number", "").apply(parse_int)
deals["pitch_number"] = raw.get("Pitch Number", "").apply(parse_int)
deals["season_start"] = raw.get("Season Start", "").apply(parse_date)
deals["season_end"] = raw.get("Season End", "").apply(parse_date)
deals["original_air_date"] = raw.get("Original Air Date", "").apply(parse_date)
deals["episode_title"] = raw.get("Episode Title", "")
deals["anchor"] = raw.get("Anchor", "")
deals["sector"] = raw.get("Industry", "")
deals["business_description"] = raw.get("Business Description", "")
deals["company_website"] = raw.get("Company Website", "")
deals["started_in"] = raw.get("Started in", "")
deals["founder_count"] = raw.get("Number of Presenters", "").apply(parse_int)
deals["male_presenters"] = raw.get("Male Presenters", "").apply(parse_int)
deals["female_presenters"] = raw.get("Female Presenters", "").apply(parse_int)
deals["transgender_presenters"] = raw.get("Transgender Presenters", "").apply(parse_int)
deals["couple_presenters"] = raw.get("Couple Presenters", "").apply(parse_bool)
deals["pitchers_average_age"] = raw.get("Pitchers Average Age", "").apply(parse_float_or_nan)
deals["pitchers_city"] = raw.get("Pitchers City", "")
deals["pitchers_state"] = raw.get("Pitchers State", "")
deals["yearly_revenue"] = raw.get("Yearly Revenue", "").apply(parse_amount)
deals["monthly_sales"] = raw.get("Monthly Sales", "").apply(parse_amount)
deals["gross_margin"] = raw.get("Gross Margin", "").apply(parse_percent)
deals["net_margin"] = raw.get("Net Margin", "").apply(parse_percent)
deals["ebitda"] = raw.get("EBITDA", "").apply(parse_amount)
deals["cash_burn"] = raw.get("Cash Burn", "").apply(parse_amount)
deals["skus"] = raw.get("SKUs", "").apply(parse_int)
deals["has_patents"] = raw.get("Has Patents", "").apply(parse_bool)
deals["bootstrapped"] = raw.get("Bootstrapped", "").apply(parse_bool)
deals["part_of_match_off"] = raw.get("Part of Match off", "").apply(parse_bool)
deals["asked_amount"] = raw.get("Original Ask Amount", "").apply(parse_amount)
deals["equity_asked"] = raw.get("Original Offered Equity", "").apply(parse_percent)
deals["valuation_requested"] = raw.get("Valuation Requested", "").apply(parse_amount)
deals["received_offer"] = raw.get("Received Offer", "")
deals["accepted_offer"] = raw.get("Accepted Offer", "")
deals["invested_amount"] = raw.get("Total Deal Amount", "").apply(parse_amount)
deals["equity_final"] = raw.get("Total Deal Equity", "").apply(parse_percent)
deals["total_deal_debt"] = raw.get("Total Deal Debt", "").apply(parse_amount)
deals["deal_valuation"] = raw.get("Deal Valuation", "").apply(parse_amount)
deals["number_of_sharks_in_deal"] = raw.get("Number of Sharks in Deal", "").apply(parse_int)
deals["deal_has_conditions"] = raw.get("Deal Has Conditions", "").apply(parse_bool)
deals["royalty_percentage"] = raw.get("Royalty Percentage", "").apply(parse_percent)
deals["royalty_recouped_amount"] = raw.get("Royalty Recouped Amount", "").apply(parse_amount)
deals["advisory_shares_equity"] = raw.get("Advisory Shares Equity", "").apply(parse_percent)
# presence flags
deals["namita_present"] = raw.get("Namita Present", "").apply(parse_bool)
deals["vineeta_present"] = raw.get("Vineeta Present", "").apply(parse_bool)
deals["anupam_present"] = raw.get("Anupam Present", "").apply(parse_bool)
deals["aman_present"] = raw.get("Aman Present", "").apply(parse_bool)
deals["peyush_present"] = raw.get("Peyush Present", "").apply(parse_bool)
deals["ritesh_present"] = raw.get("Ritesh Present", "").apply(parse_bool)
deals["amit_present"] = raw.get("Amit Present", "").apply(parse_bool)
deals["guest_present"] = raw.get("Guest Present", "").apply(parse_bool)

# --- Build deal_investors dataframe (one row per investor per pitch) ---
investor_names = ["Namita", "Vineeta", "Anupam", "Aman", "Peyush", "Ritesh", "Amit"]
rows = []
for _, r in raw.iterrows():
    sid = r["staging_id"]
    # named sharks
    for inv in investor_names:
        amt_col = f"{inv} Investment Amount"
        eq_col = f"{inv} Investment Equity"
        debt_col = f"{inv} Debt Amount"
        amt = parse_amount(r.get(amt_col, ""))
        eq = parse_percent(r.get(eq_col, ""))
        debt = parse_amount(r.get(debt_col, ""))
        if not (np.isnan(amt) and np.isnan(eq) and np.isnan(debt)):
            rows.append({
                "staging_id": sid,
                "investor": inv,
                "invested_amount": amt if not np.isnan(amt) else None,
                "invested_equity": eq if not np.isnan(eq) else None,
                "invested_debt": debt if not np.isnan(debt) else None
            })
    # guest investor (name may be in 'Invested Guest Name')
    guest_name = r.get("Invested Guest Name", "")
    guest_amt = parse_amount(r.get("Guest Investment Amount", ""))
    guest_eq = parse_percent(r.get("Guest Investment Equity", ""))
    guest_debt = parse_amount(r.get("Guest Debt Amount", ""))
    if not (np.isnan(guest_amt) and np.isnan(guest_eq) and np.isnan(guest_debt)):
        inv_name = guest_name.strip() if guest_name.strip() != "" else "Guest"
        rows.append({
            "staging_id": sid,
            "investor": inv_name,
            "invested_amount": guest_amt if not np.isnan(guest_amt) else None,
            "invested_equity": guest_eq if not np.isnan(guest_eq) else None,
            "invested_debt": guest_debt if not np.isnan(guest_debt) else None
        })

deal_investors = pd.DataFrame(rows)

# --- Save outputs ---
deals.to_csv(DEALS_OUT, index=False)
deal_investors.to_csv(INV_OUT, index=False)

print(f"Wrote cleaned deals to: {DEALS_OUT}")
print(f"Wrote cleaned deal_investors to: {INV_OUT}")
