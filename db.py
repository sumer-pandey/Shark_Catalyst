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


# db.py  <-- edit this file
import pandas as pd
from sqlalchemy import create_engine
import os

# your DB URL (should come from env or dotenv as before)
DATABASE_URL = os.environ.get("DATABASE_URL")  # keep your existing pattern

# create engine once (reuse across calls)
_engine = create_engine(DATABASE_URL, pool_pre_ping=True)

def run_query(sql: str, params=None, fetch=True, row_limit=None):
    """
    Execute SQL safely and return a pandas DataFrame (for SELECTs).
    - sql: SQL statement using psycopg2 paramstyle (%s) OR named styles (it will work).
    - params:
        None -> single execute without params
        dict -> single execute with named params
        tuple -> single execute with positional params
        list:
          - list of tuples/dicts -> executemany
          - otherwise -> treat as a single positional param sequence and call execute(sql, tuple(params))
    Returns:
        pandas.DataFrame for SELECTs, or an empty DataFrame if nothing returned.
    Raises RuntimeError on failure with helpful message.
    """
    conn = None
    cur = None
    try:
        # use raw DB-API connection from SQLAlchemy so psycopg2 paramstyle %s works
        conn = _engine.raw_connection()
        cur = conn.cursor()

        # Normalized param handling:
        if params is None:
            cur.execute(sql)
        else:
            # If params is a list:
            if isinstance(params, list):
                # if list-of-tuples or list-of-dicts -> executemany
                if all(isinstance(p, (tuple, dict)) for p in params):
                    cur.executemany(sql, params)
                else:
                    # treat as a single tuple of positional params (common case where caller passed a list)
                    cur.execute(sql, tuple(params))
            else:
                # params is tuple, dict, or scalar -> single execute
                # Note: scalar values (int/str) will still work if DB API accepts them as second arg
                cur.execute(sql, params)

        # If the statement returns rows, fetch them and build DataFrame
        if fetch:
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchall() if cur.description else []
            # optional row cap
            if row_limit is not None and len(rows) > row_limit:
                rows = rows[:row_limit]
            df = pd.DataFrame(rows, columns=cols)
        else:
            # for non-select statements
            conn.commit()
            df = pd.DataFrame()

        # final cleanup
        return df

    except Exception as e:
        # include a concise snippet of the SQL in the error so logs help debugging
        short_sql = sql if len(sql) < 400 else sql[:400] + "..."
        raise RuntimeError(f"run_query failed. SQL: {short_sql} Params: {type(params).__name__} Error: {e}") from e

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
