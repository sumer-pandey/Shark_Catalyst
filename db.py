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
import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import os

# ----------------------------------------------------------------------
# FIX 1: Use st.connection() to manage pooling, connection, and secrets
# ----------------------------------------------------------------------

# @st.cache_resource is no longer needed on the connection setup itself
def get_connection():
    # Attempt to use the native st.connection object defined in secrets
    try:
        # The 'supabase' name matches the [connections.supabase] in secrets.toml
        conn = st.connection("supabase", type="sql")
        return conn
    except Exception:
        # Fallback for local development where st.secrets is not fully available
        # We simulate the connection object if running locally via environment variables
        
        # We need psycopg2-compatible connection args
        conn_args = {
            "host": os.getenv("DB_HOST"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "dbname": os.getenv("DB_NAME"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "sslmode": os.getenv("DB_SSLMODE", "require")
        }
        
        # We return the actual psycopg2 connection for local consistency
        return psycopg2.connect(**conn_args)


# ----------------------------------------------------------------------
# FIX 2: Simplify run_query to handle both st.connection and local psycopg2
# ----------------------------------------------------------------------

@st.cache_data(ttl=600)
def run_query(sql, params=None):
    conn_obj = get_connection()
    
    # Check if the connection object is the Streamlit SQLConnection wrapper
    if hasattr(conn_obj, 'query'):
        # Use Streamlit's built-in query method which handles fetching/caching/closing
        # Note: Streamlit's query uses pandas.read_sql internally
        df = conn_obj.query(sql, params=params, ttl=600)
        return df
    else:
        # Use direct psycopg2 connection (fallback for local use)
        conn = conn_obj
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params or ())
                if cur.description:
                    rows = cur.fetchall()
                    return pd.DataFrame(rows)
                else:
                    conn.commit()
                    return pd.DataFrame()
        finally:
            # We explicitly close here ONLY for the local psycopg2 connection
            if conn:
                conn.close()