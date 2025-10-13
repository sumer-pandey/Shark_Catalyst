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

# Do NOT create the engine at import time.
# Instead, create it lazily the first time someone needs it.
_ENGINE: Optional[Engine] = None

def _get_database_url():
    """
    Resolve the database connection URL from environment variables.
    Order of preference:
      1. DATABASE_URL environment variable
      2. SUPABASE_DB_URL environment variable (if you named it differently)
      3. Return None if not found
    NOTE: Do not hardcode credentials. Set these in your Streamlit Secrets / env.
    """
    return os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")

def get_engine():
    """
    Lazily create and return a SQLAlchemy engine. If DATABASE_URL is missing,
    raise a clear error instructing the deployer what to set.
    """
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE

    db_url = _get_database_url()
    if not db_url:
        # Clear, non-sensitive instruction for the user/deployer
        raise RuntimeError(
            "DATABASE_URL is not set. Set the DATABASE_URL environment variable "
            "or Streamlit secret (key: DATABASE_URL) to your Supabase/Postgres connection URL. "
            "Example value should look like: postgresql://user:password@host:5432/dbname (DO NOT hardcode credentials in code)."
        )

    # Create engine once (safe for app lifetime)
    _ENGINE = create_engine(db_url, pool_pre_ping=True)
    return _ENGINE

def run_query(sql: str, params=None, fetch=True, row_limit=None):
    """
    Execute SQL safely and return a pandas DataFrame (for SELECTs).
    See docstring in the main conversation for behavior.
    """
    conn = None
    cur = None
    try:
        engine = get_engine()
        conn = engine.raw_connection()
        cur = conn.cursor()

        # Param handling (robust)
        if params is None:
            cur.execute(sql)
        else:
            if isinstance(params, list):
                # If it's list-of-tuples or list-of-dicts -> executemany
                if all(isinstance(p, (tuple, dict)) for p in params):
                    cur.executemany(sql, params)
                else:
                    # treat as a single tuple of positional params
                    cur.execute(sql, tuple(params))
            else:
                # dict, tuple, scalar -> single execute
                cur.execute(sql, params)

        if fetch and cur.description:
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            if row_limit is not None and len(rows) > row_limit:
                rows = rows[:row_limit]
            df = pd.DataFrame(rows, columns=cols)
        else:
            # commit for non-select statements (defensive)
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
