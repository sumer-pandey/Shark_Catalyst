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
# os/psycopg2 imports are no longer strictly needed for deployed app but
# keeping them commented out for reference is fine.

# ----------------------------------------------------------------------
# FINAL FIX: Explicitly specify the driver for st.connection
# ----------------------------------------------------------------------

# db.py (Final Fix for parameters)

@st.cache_data(ttl=600)
def run_query(sql, params=None):
    """
    Connects to the database using the Streamlit st.connection method
    and executes a query, leveraging Streamlit's built-in caching.
    """
    try:
        conn = st.connection(
            "supabase", 
            type="sql",
            dialect="postgresql" 
        )
    except Exception as e:
        raise RuntimeError(f"Could not establish Streamlit connection 'supabase'. Check secrets file and database credentials. Error: {e}") from e

    # Execute the query using the connection object's query method
    try:
        # CRITICAL FIX: Ensure params is always a tuple for positional placeholders (%s)
        # If params is None, use an empty tuple: ()
        # If params is a list/tuple, use it directly.
        final_params = params if params is not None else () 
        
        df = conn.query(sql, params=final_params, ttl=600) # Use the sanitized params
        return df
    except Exception as e:
        # Provide informative error for debugging
        raise RuntimeError(f"run_query failed. SQL: {sql[:300]}... Error: {e}") from e