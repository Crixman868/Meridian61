import streamlit as st
import pandas as pd
from app import load_log_data, get_eta_status, ALL_DOCS
from datetime import datetime

st.set_page_config(page_title="Staff Dashboard", layout="wide")

# This ensures the dashboard uses your existing app logic 
# without you needing to change a single line in app.py.
