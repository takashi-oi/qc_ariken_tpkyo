import os
import sys

print("=== ENVIRONMENT CHECK ===")
print(f"Python Executable: {sys.executable}")
print(f"Current Working Directory: {os.getcwd()}")
print(f"System Path: {sys.path}")

try:
    import duckdb

    print(f"SUCCESS: DuckDB found (Version: {duckdb.__version__})")
except ImportError as e:
    print(f"FAILURE: DuckDB not found. Error: {e}")

try:
    import streamlit

    print(f"SUCCESS: Streamlit found (Version: {streamlit.__version__})")
except ImportError as e:
    print(f"FAILURE: Streamlit not found. Error: {e}")
print("=========================")
