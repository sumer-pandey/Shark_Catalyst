# db.py
import os
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# ---------- Config from env ----------
USE_SQLITE = os.getenv("USE_SQLITE", "0") in ("1", "true", "True")
SQLITE_PATH = os.getenv("SQLITE_PATH", "data/sharktank.db")

# MSSQL config (only used if USE_SQLITE is false)
MSSQL_DRIVER = os.getenv("MSSQL_DRIVER", "ODBC Driver 18 for SQL Server")
MSSQL_SERVER = os.getenv("MSSQL_SERVER", "localhost\\SQLEXPRESS")
MSSQL_DATABASE = os.getenv("MSSQL_DB", "sharktank")
MSSQL_UID = os.getenv("MSSQL_UID", "")
MSSQL_PWD = os.getenv("MSSQL_PWD", "")
MSSQL_ENCRYPT = os.getenv("MSSQL_ENCRYPT", "no")
MSSQL_CONN = os.getenv("MSSQL_CONN")  # optional full connection string

_engine = None

def get_engine():
    """
    Returns a SQLAlchemy engine.
    Priority:
      1) USE_SQLITE env var -> SQLite
      2) MSSQL_CONN env var -> use directly
      3) Build SQL Server connection from MSSQL_* env vars
    """
    global _engine
    if _engine is not None:
        return _engine

    if USE_SQLITE:
        conn_str = f"sqlite:///{SQLITE_PATH}"
        _engine = create_engine(conn_str, connect_args={"check_same_thread": False})
        return _engine

    # If FULL connection provided
    if MSSQL_CONN:
        _engine = create_engine(MSSQL_CONN)
        return _engine

    # Build pyodbc connection string
    driver = MSSQL_DRIVER
    server = MSSQL_SERVER
    database = MSSQL_DATABASE
    uid = MSSQL_UID
    pwd = MSSQL_PWD
    encrypt = MSSQL_ENCRYPT

    if uid and pwd:
        params = f"DRIVER={driver};SERVER={server};DATABASE={database};UID={uid};PWD={pwd};Encrypt={encrypt};TrustServerCertificate=Yes"
    else:
        # Trusted Windows Authentication
        params = f"DRIVER={driver};SERVER={server};DATABASE={database};Trusted_Connection=Yes;Encrypt={encrypt};TrustServerCertificate=Yes"

    odbc_conn_str = "mssql+pyodbc:///?odbc_connect=" + quote_plus(params)
    _engine = create_engine(odbc_conn_str, fast_executemany=True)
    return _engine

def run_query(sql: str, params: dict = None, read_sql_kwargs: dict = None) -> pd.DataFrame:
    """
    Run a read-only SQL query (or stored-proc call) and return a pandas DataFrame.
    - sql: SQL text. Use SQLAlchemy text() style for params, e.g. "EXEC dbo.sp_name @p = :p"
    - params: dict of parameters
    - read_sql_kwargs: extra kwargs passed to pandas.read_sql_query
    """
    engine = get_engine()
    read_sql_kwargs = read_sql_kwargs or {}
    try:
        # Use sqlalchemy.text to allow parameter binding
        return pd.read_sql_query(text(sql), con=engine, params=params or {}, **read_sql_kwargs)
    except Exception as e:
        # Provide informative error for debugging
        raise RuntimeError(f"run_query failed. SQL: {sql[:200]}... Error: {e}") from e
