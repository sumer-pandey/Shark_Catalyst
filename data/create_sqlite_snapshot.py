# create_sqlite_snapshot.py
import pandas as pd
import sqlite3
from pathlib import Path

DATA_DIR = Path("data")
DEALS_CSV = DATA_DIR / "deals_clean.csv"
INV_CSV = DATA_DIR / "deal_investors_clean.csv"
OUT_DB = DATA_DIR / "sharktank.db"

assert DEALS_CSV.exists(), f"{DEALS_CSV} missing"
assert INV_CSV.exists(), f"{INV_CSV} missing"

df_deals = pd.read_csv(DEALS_CSV)
df_inv = pd.read_csv(INV_CSV)

conn = sqlite3.connect(OUT_DB)
df_deals.to_sql("deals", conn, index=False, if_exists="replace")
df_inv.to_sql("deal_investors", conn, index=False, if_exists="replace")
conn.close()
print("SQLite snapshot created at:", OUT_DB)
