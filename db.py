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
import os
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

# We will rely entirely on the Streamlit native SQL connection (st.connection)
# which automatically reads the credentials from the [connections.supabase] block
# in the Streamlit Cloud secrets.

@st.cache_data(ttl=600)
def run_query(sql, params=None):
    """
    Connects to the database using the Streamlit st.connection method
    and executes a query, leveraging Streamlit's built-in caching.
    """
    
    # 1. Get the connection object (Streamlit handles resource caching)
    # The 'supabase' name must match the header in your Streamlit secrets file.
    try:
        conn = st.connection("supabase", type="sql")
    except Exception as e:
        # If st.connection fails (e.g., secrets missing or local env is weird)
        raise RuntimeError(f"Could not establish Streamlit connection 'supabase'. Error: {e}") from e

    # 2. Execute the query using the connection object's query method
    try:
        # Streamlit's query method uses pandas.read_sql internally
        df = conn.query(sql, params=params, ttl=600)
        return df
    except Exception as e:
        # Provide informative error for debugging
        raise RuntimeError(f"run_query failed. SQL: {sql[:300]}... Error: {e}") from e

# NOTE: The psycopg2 imports and manual connection/cursor logic are no longer needed
# because the st.connection("...", type="sql") wrapper handles all of it.