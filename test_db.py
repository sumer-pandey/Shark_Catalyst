# test_db.py
from db import run_query
import traceback

def test_simple_query():
    try:
        df = run_query("SELECT TOP 5 id, company, season, invested_amount FROM dbo.deals ORDER BY id DESC")
        print("Simple query OK. Rows returned:", len(df))
        print(df.head())
    except Exception as e:
        print("Simple query FAILED:")
        traceback.print_exc()

def test_proc_kpis():
    try:
        df = run_query("EXEC dbo.sp_home_kpis @season = :season", {"season":"All"})
        print("sp_home_kpis executed. Result:")
        print(df)
    except Exception as e:
        print("sp_home_kpis FAILED:")
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_query()
    test_proc_kpis()
