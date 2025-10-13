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

# -------------------------
# Database URL resolution + engine creation
# -------------------------
import urllib.parse

def _get_database_url():
    """
    Resolve database connection URL from environment variables or Streamlit secrets.

    Returns:
      - full DB URL string (e.g. postgresql://user:pass@host:port/dbname) or None
    NOTE:
      we intentionally do NOT accept a short 'database' value (like 'postgres') as a valid URL.
      This avoids errors like "Could not parse SQLAlchemy URL from string 'postgres'".
    """
    # 1) env vars (fast path)
    env_val = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if env_val:
        return env_val

    # 2) try Streamlit secrets (only available at runtime on Streamlit)
    try:
        import streamlit as st  # type: ignore
    except Exception:
        st = None

    if st is None:
        return None

    # direct top-level keys preferred
    for key in ("DATABASE_URL", "database_url"):
        if key in st.secrets:
            cand = st.secrets[key]
            # accept only full URLs with scheme
            if isinstance(cand, str) and "://" in cand:
                return cand

    # nested conventional layout: st.secrets["connections"]["supabase"]["database_url"]
    try:
        cs = st.secrets.get("connections", {}).get("supabase")
        if isinstance(cs, dict):
            cand = cs.get("database_url") or cs.get("DATABASE_URL")
            if isinstance(cand, str) and "://" in cand:
                return cand
    except Exception:
        pass

    # dotted key layout: st.secrets["connections.supabase"]
    try:
        cs = st.secrets.get("connections.supabase")
        if isinstance(cs, dict):
            cand = cs.get("database_url") or cs.get("DATABASE_URL")
            if isinstance(cand, str) and "://" in cand:
                return cand
    except Exception:
        pass

    # last resort: recursive search for any full URL-like value
    def _recursive_find_full_url(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str) and "://" in v:
                    # prefer keys containing "db" or "database" first
                    if any(part in k.lower() for part in ("db", "database", "url")):
                        return v
                    # otherwise keep scanning
                    candidate = _recursive_find_full_url(v)
                    if candidate:
                        return candidate
                elif isinstance(v, dict):
                    candidate = _recursive_find_full_url(v)
                    if candidate:
                        return candidate
        return None

    found = _recursive_find_full_url(st.secrets)
    if found:
        return found

    # If we get here, maybe st.secrets had a short "database" key (like "postgres").
    # Return None so caller can raise a clear error.
    return None


def create_real_engine():
    """
    Create and return a real SQLAlchemy engine or raise a clear error if DB URL missing/invalid.
    """
    db_url = _get_database_url()
    if not db_url:
        # Helpful debugging message listing where short values may exist in secrets
        example_msg = (
            "DATABASE_URL is not set or the provided secret is not a full connection URL.\n"
            "Please add a top-level secret named DATABASE_URL (or connections.supabase.database_url) with\n"
            "the full connection string, e.g.:\n\n"
            "  postgresql://<username>:<percent-encoded-password>@<host>:<port>/<dbname>\n\n"
            "Important: if your password contains special characters like '@' encode it using percent-encoding\n"
            "for URLs (e.g. '@' -> '%40'). In Python you can do:\n"
            "  import urllib.parse\n"
            "  urllib.parse.quote_plus('yourpassword')\n\n"
            "Example (do NOT paste your real password here):\n"
            "  postgresql://postgres.rfbtjnijjbbdzhddarpr:shark%40catalyst1@aws-1-ap-south-1.pooler.supabase.com:6543/postgres\n"
        )
        raise RuntimeError(example_msg)

    # Basic sanity check: url-like string must contain '://'
    if "://" not in db_url:
        raise RuntimeError(
            "Found a candidate DB value but it does not look like a full URL. "
            "Provide DATABASE_URL as a full SQLAlchemy/postgres URL (postgresql://user:pass@host:port/dbname)."
        )

    # create engine
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
