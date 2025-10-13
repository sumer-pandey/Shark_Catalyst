# # db.py
# import os
# import pandas as pd
# import psycopg2
# from psycopg2.extras import RealDictCursor
# import streamlit as st # <-- CRITICAL: Import Streamlit to access secrets

# @st.cache_resource(ttl=3600)
# def get_connection():
#     # --- Determine source of credentials (Streamlit Cloud or Local Env) ---
    
#     # Check if the connection secrets are available (means running on Streamlit Cloud)
#     if "connections" in st.secrets and "supabase" in st.secrets["connections"]:
#         secrets = st.secrets["connections"]["supabase"]
#         host = secrets["host"]
#         port = int(secrets.get("port", 5432)) # Use .get for safety, convert to int
#         dbname = secrets["database"]
#         user = secrets["user"]
#         password = secrets["password"]
#         sslmode = secrets.get("sslmode", "require") # Added sslmode from your local env
#     else:
#         # Fallback to local environment variables
#         host = os.getenv("DB_HOST")
#         port = int(os.getenv("DB_PORT", "5432"))
#         dbname = os.getenv("DB_NAME")
#         user = os.getenv("DB_USER")
#         password = os.getenv("DB_PASSWORD")
#         sslmode = os.getenv("DB_SSLMODE", "require")

#     # --- Establish the connection ---
#     return psycopg2.connect(
#         host=host,
#         port=port,
#         dbname=dbname,
#         user=user,
#         password=password,
#         sslmode=sslmode
#     )

# def run_query(sql, params=None):
#     conn = None
#     try:
#         conn = get_connection()
#         with conn.cursor(cursor_factory=RealDictCursor) as cur:
#             cur.execute(sql, params or ())
#             if cur.description:
#                 rows = cur.fetchall()
#                 return pd.DataFrame(rows)
#             else:
#                 conn.commit()
#                 return pd.DataFrame()
#     except Exception as e:
#         # Include the SQL query in the error for better debugging
#         raise RuntimeError(f"run_query failed. SQL: {sql[:300]}... Error: {e}") from e
#     finally:
#         if conn:
#             conn.close()


# db.py
import os
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from typing import Optional

# -------------------------
# Lazy engine creation API
# -------------------------

_ENGINE: Optional[Engine] = None

def _get_database_url():
    """
    Resolve database connection URL from environment variables.
    """
    return os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")

def create_real_engine():
    """
    Create and return a real SQLAlchemy engine or raise a clear error if DB URL missing.
    """
    db_url = _get_database_url()
    if not db_url:
        raise RuntimeError(
            "DATABASE_URL is not set. Set the DATABASE_URL environment variable or Streamlit secret "
            "(key: DATABASE_URL) to your Supabase/Postgres connection URL (postgresql://user:pass@host:port/dbname)."
        )
    return create_engine(db_url, pool_pre_ping=True)

def get_engine() -> Engine:
    """
    Return a real SQLAlchemy engine, creating it if necessary.
    """
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = create_real_engine()
    return _ENGINE

# -------------------------
# Backwards-compatible 'engine' proxy
# -------------------------
class _LazyEngineProxy:
    """
    A small proxy object so other modules can `from db import engine`
    and use engine.connect(), engine.raw_connection(), etc., while delaying
    actual engine creation until first attribute access.
    """
    def __init__(self):
        self._real = None

    def _ensure(self):
        if self._real is None:
            self._real = get_engine()
        return self._real

    # Delegate common methods used by code
    def connect(self, *args, **kwargs):
        return self._ensure().connect(*args, **kwargs)

    def raw_connection(self, *args, **kwargs):
        return self._ensure().raw_connection(*args, **kwargs)

    def execute(self, *args, **kwargs):
        # SQLAlchemy 2.0 removed Engine.execute, but in case older code uses it:
        real = self._ensure()
        if hasattr(real, "execute"):
            return real.execute(*args, **kwargs)
        # fallback: use connection.execute
        conn = real.connect()
        try:
            return conn.execute(*args, **kwargs)
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def dispose(self):
        if self._real is not None:
            self._real.dispose()

    def __getattr__(self, name):
        # Delegate anything else to the real engine
        real = self._ensure()
        return getattr(real, name)

# Expose the proxy as `engine` so imports like `from db import engine` still work.
engine = _LazyEngineProxy()

# -------------------------
# Utility: run_query
# -------------------------
def run_query(sql: str, params=None, fetch=True, row_limit=None):
    """
    Execute SQL and return a pandas DataFrame for SELECTs.
    - sql: SQL string with positional (%s) or named params depending on DB driver used.
    - params: None, tuple/list, dict, or list-of-tuples/dicts for executemany.
    - fetch: if True and cursor.description present, return DataFrame, else return empty DataFrame.
    - row_limit: client-side cap on returned rows.

    Raises RuntimeError with the SQL snippet and original error for visibility.
    """
    conn = None
    cur = None
    try:
        # Use engine.raw_connection() to get a DB-API cursor for universal param behavior
        conn = engine.raw_connection()
        cur = conn.cursor()

        # Param handling:
        if params is None:
            cur.execute(sql)
        else:
            # If params is a list, check if it's a list of tuples/dicts (executemany)
            if isinstance(params, list):
                if all(isinstance(p, (tuple, dict)) for p in params):
                    cur.executemany(sql, params)
                else:
                    # It's a list but not list-of-tuples/dicts -> treat as single tuple
                    cur.execute(sql, tuple(params))
            else:
                # tuple, dict, scalar -> single execute
                cur.execute(sql, params)

        if fetch and cur.description:
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            if row_limit is not None and len(rows) > row_limit:
                rows = rows[:row_limit]
            df = pd.DataFrame(rows, columns=cols)
        else:
            # commit for non-selects if needed
            if not fetch:
                conn.commit()
            df = pd.DataFrame()

        return df

    except Exception as e:
        short_sql = sql if len(sql) < 400 else sql[:400] + "..."
        raise RuntimeError(f"run_query failed. SQL: {short_sql} ParamsType: {type(params).__name__} Error: {e}") from e

    finally:
        try:
            if cur is not None:
                cur.close()
        except Exception:
            pass
        try:
            if conn is not None:
                conn.close()
        except Exception:
            pass
