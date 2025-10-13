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

_ENGINE: Optional[Engine] = None

def _get_database_url():
    """
    Get database URL from environment or Streamlit secrets.
    Priority order:
    1. Environment variable DATABASE_URL
    2. Streamlit secrets DATABASE_URL (top-level)
    3. Streamlit secrets connections.supabase.database_url
    """
    # Check environment first
    db_url = os.environ.get("DATABASE_URL")
    if db_url and "://" in db_url:
        return db_url
    
    # Try Streamlit secrets
    try:
        import streamlit as st
        
        # Top-level secret (RECOMMENDED)
        if "DATABASE_URL" in st.secrets:
            db_url = st.secrets["DATABASE_URL"]
            if isinstance(db_url, str) and "://" in db_url:
                return db_url
        
        # Nested secret (alternative)
        if "connections" in st.secrets and "supabase" in st.secrets["connections"]:
            supabase = st.secrets["connections"]["supabase"]
            if "database_url" in supabase:
                db_url = supabase["database_url"]
                if isinstance(db_url, str) and "://" in db_url:
                    return db_url
    except Exception:
        pass
    
    return None

def create_real_engine():
    """Create SQLAlchemy engine with proper error handling."""
    db_url = _get_database_url()
    
    if not db_url:
        raise RuntimeError(
            "DATABASE_URL is not set or the provided secret is not a full connection URL.\n\n"
            "Please add a secret named DATABASE_URL with the full connection string:\n"
            "postgresql://<username>:<percent-encoded-password>@<host>:<port>/<dbname>\n\n"
            "Important: Encode special characters in password using percent-encoding:\n"
            "  @ becomes %40\n"
            "  # becomes %23\n"
            "  $ becomes %24\n\n"
            "Example:\n"
            "DATABASE_URL = \"postgresql://postgres.user:pass%40word@host.supabase.com:6543/postgres\"\n\n"
            "Add this in Streamlit Cloud: App Settings → Secrets"
        )
    
    if "://" not in db_url:
        raise RuntimeError(
            f"Invalid DATABASE_URL format. Must be a full URL like:\n"
            f"postgresql://user:pass@host:port/dbname\n"
            f"Found: {db_url[:50]}..."
        )
    
    return create_engine(db_url, pool_pre_ping=True, pool_recycle=3600)

def get_engine() -> Engine:
    """Get or create SQLAlchemy engine."""
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = create_real_engine()
    return _ENGINE

class _LazyEngineProxy:
    """Lazy engine proxy for backwards compatibility."""
    def __init__(self):
        self._real = None
    
    def _ensure(self):
        if self._real is None:
            self._real = get_engine()
        return self._real
    
    def connect(self, *args, **kwargs):
        return self._ensure().connect(*args, **kwargs)
    
    def raw_connection(self, *args, **kwargs):
        return self._ensure().raw_connection(*args, **kwargs)
    
    def execute(self, *args, **kwargs):
        real = self._ensure()
        if hasattr(real, "execute"):
            return real.execute(*args, **kwargs)
        with real.connect() as conn:
            return conn.execute(*args, **kwargs)
    
    def dispose(self):
        if self._real is not None:
            self._real.dispose()
    
    def __getattr__(self, name):
        return getattr(self._ensure(), name)

engine = _LazyEngineProxy()

def run_query(sql: str, params=None, fetch=True, row_limit=None):
    """
    Execute SQL and return DataFrame.
    
    Args:
        sql: SQL query string
        params: Query parameters (tuple, list, dict, or list of tuples/dicts)
        fetch: If True, return DataFrame for SELECT queries
        row_limit: Max rows to return
    
    Returns:
        pandas DataFrame
    """
    conn = None
    cur = None
    try:
        conn = engine.raw_connection()
        cur = conn.cursor()
        
        if params is None:
            cur.execute(sql)
        elif isinstance(params, list) and all(isinstance(p, (tuple, dict)) for p in params):
            cur.executemany(sql, params)
        elif isinstance(params, list):
            cur.execute(sql, tuple(params))
        else:
            cur.execute(sql, params)
        
        if fetch and cur.description:
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            if row_limit and len(rows) > row_limit:
                rows = rows[:row_limit]
            return pd.DataFrame(rows, columns=cols)
        else:
            if not fetch:
                conn.commit()
            return pd.DataFrame()
    
    except Exception as e:
        short_sql = sql[:400] if len(sql) > 400 else sql
        raise RuntimeError(
            f"Query failed.\n"
            f"SQL: {short_sql}\n"
            f"Params: {type(params).__name__}\n"
            f"Error: {e}"
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