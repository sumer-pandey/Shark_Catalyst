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


# db.py - Using Supabase native client (no DATABASE_URL needed)
import os
import pandas as pd
import streamlit as st
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor

_CONNECTION_PARAMS: Optional[dict] = None

def _get_connection_params():
    """
    Get database connection parameters from Streamlit secrets or environment.
    NO DATABASE_URL parsing - just direct parameters.
    """
    global _CONNECTION_PARAMS
    
    if _CONNECTION_PARAMS is not None:
        return _CONNECTION_PARAMS
    
    params = {}
    
    # Try Streamlit secrets first
    try:
        if "connections" in st.secrets and "supabase" in st.secrets["connections"]:
            supabase = st.secrets["connections"]["supabase"]
            
            # Direct mapping from secrets
            params["host"] = supabase.get("host")
            params["port"] = int(supabase.get("port", 5432))
            params["database"] = supabase.get("database") or supabase.get("dbname")
            params["user"] = supabase.get("user")
            params["password"] = supabase.get("password")
            params["sslmode"] = supabase.get("sslmode", "require")
            
            # Validate we got everything
            required = ["host", "database", "user", "password"]
            if all(params.get(k) for k in required):
                _CONNECTION_PARAMS = params
                return params
    except Exception as e:
        pass
    
    # Fallback to environment variables
    params["host"] = os.getenv("DB_HOST") or os.getenv("SUPABASE_HOST")
    params["port"] = int(os.getenv("DB_PORT", "5432"))
    params["database"] = os.getenv("DB_NAME") or os.getenv("SUPABASE_DB")
    params["user"] = os.getenv("DB_USER") or os.getenv("SUPABASE_USER")
    params["password"] = os.getenv("DB_PASSWORD") or os.getenv("SUPABASE_PASSWORD")
    params["sslmode"] = os.getenv("DB_SSLMODE", "require")
    
    # Validate
    required = ["host", "database", "user", "password"]
    if not all(params.get(k) for k in required):
        missing = [k for k in required if not params.get(k)]
        raise RuntimeError(
            f"Missing database connection parameters: {', '.join(missing)}\n\n"
            f"Please add to Streamlit Secrets:\n"
            f"[connections.supabase]\n"
            f"host = \"your-host.supabase.com\"\n"
            f"port = 6543\n"
            f"database = \"postgres\"\n"
            f"user = \"postgres.yourproject\"\n"
            f"password = \"your_password\"\n"
        )
    
    _CONNECTION_PARAMS = params
    return params

def get_connection():
    """Get a raw psycopg2 connection."""
    params = _get_connection_params()
    return psycopg2.connect(**params)

def run_query(sql: str, params=None, fetch=True, row_limit=None):
    """
    Execute SQL and return DataFrame.
    
    Args:
        sql: SQL query string
        params: Query parameters (tuple, list, dict)
        fetch: If True, return DataFrame for SELECT queries
        row_limit: Max rows to return
    
    Returns:
        pandas DataFrame
    """
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        if params is None:
            cur.execute(sql)
        elif isinstance(params, list) and all(isinstance(p, (tuple, dict)) for p in params):
            cur.executemany(sql, params)
        elif isinstance(params, list):
            cur.execute(sql, tuple(params))
        else:
            cur.execute(sql, params)
        
        if fetch and cur.description:
            rows = cur.fetchall()
            if row_limit and len(rows) > row_limit:
                rows = rows[:row_limit]
            return pd.DataFrame(rows)
        else:
            conn.commit()
            return pd.DataFrame()
    
    except Exception as e:
        short_sql = sql[:400] if len(sql) > 400 else sql
        raise RuntimeError(
            f"Query failed.\n"
            f"SQL: {short_sql}\n"
            f"Params: {type(params).__name__ if params else 'None'}\n"
            f"Error: {str(e)}"
        ) from e
    
    finally:
        if cur:
            try:
                cur.close()
            except:
                pass
        if conn:
            try:
                conn.close()
            except:
                pass

# Backwards compatibility
def get_engine():
    """Legacy function - returns connection params instead."""
    return _get_connection_params()

class _ConnectionProxy:
    """Proxy for backwards compatibility with engine.connect() style code."""
    
    def connect(self):
        return get_connection()
    
    def raw_connection(self):
        return get_connection()

engine = _ConnectionProxy()