import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import base64
import gspread
import json
import jinja2
import re
import tempfile
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials as HumanCredentials
from google.oauth2.service_account import Credentials as BotCredentials
from googleapiclient.http import MediaFileUpload
from weasyprint import HTML

# ==========================================
# 1. SETUP & SAFETY WRAPPER
# ==========================================
st.set_page_config(page_title="Meridian Command Console", page_icon="📦", layout="wide")

def safe_update_log(df, idx, col, val, dtype=str):
    try:
        if dtype == int: clean_val = int(float(val)) if val and str(val).strip() else 0
        elif dtype == float: clean_val = float(val) if val and str(val).strip() else 0.0
        else: clean_val = str(val) if val else ""
        df.at[idx, col] = clean_val
        return df
    except Exception as e:
        st.warning(f"Format mismatch in '{col}': {e}. Value set to default.")
        df.at[idx, col] = 0 if dtype in [int, float] else ""
        return df

st.markdown("""
<style>
    .stApp { background-color: #ffffff; background-image: linear-gradient(45deg, #f8f9fa 25%, transparent 25%, transparent 75%, #f8f9fa 75%, #f8f9fa), linear-gradient(45deg, #f8f9fa 25%, transparent 25%, transparent 75%, #f8f9fa 75%, #f8f9fa); background-size: 20px 20px; background-position: 0 0, 10px 10px; }
    [data-testid="stExpander"] { background-color: #ffffff !important; border: 1px solid #e2e8f0; border-radius: 6px; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.04); margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. ADMIN TABS (NEW)
# ==========================================
def render_supplier_admin():
    st.subheader("⚙️ Supplier Admin")
    fields = ['Name', 'Address', 'Palette', 'Typography', 'Header', 'GeoInv', 'Orient', 'PackOrient', 'WMToggle', 'WMOpacity', 'PrimaryHex', 'SecondaryHex', 'FontSize', 'LogoAlign', 'TableStyle', 'Template']
    with st.form("new_supplier_form"):
        data = {f: st.text_input(f) for f in fields}
        if st.form_submit_button("Save New Supplier"):
            if not data['Name']: st.error("Name is required!"); return
            df = pd.read_csv("suppliers.csv") if os.path.exists("suppliers.csv") else pd.DataFrame(columns=fields)
            df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            df.to_csv("suppliers.csv", index=False)
            st.success("Supplier Saved")

def render_client_admin():
    st.subheader("👥 Client Admin")
    fields = ['Name', 'Address', 'Contact', 'Email', 'Phone', 'Notes']
    with st.form("new_client_form"):
        data = {f: st.text_input(f) for f in fields}
        if st.form_submit_button("Save New Client"):
            if not data['Name']: st.error("Name is required!"); return
            df = pd.read_csv("clients.csv") if os.path.exists("clients.csv") else pd.DataFrame(columns=fields)
            df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            df.to_csv("clients.csv", index=False)
            st.success("Client Saved")

# ==========================================
# 3. ORIGINAL FUNCTIONS (PRESERVED)
# ==========================================
# [Here is your original helper function section]
SHEET_URL = "https://docs.google.com/spreadsheets/d/1wUBZSnB7cJ2T5_iY5_POpfsNmZn0INGj08EdcLc7TsQ/edit?usp=sharing"
ROOT_FOLDER_ID = "1CITSPAI-BoFeQQLLkmeoX2wkjunTbpGm"
LOG_COLUMNS = ["Row_UID", "Invoice No", "Client Name", "Container #", "Country of Origin", "ETA", "Lodged Status", "Shipment Status", "NALDO", "Total Cartons", "Commercial Invoice", "CARICOM Invoice", "Sequential Packing List", "Official Duties Assessment", "Bill of Lading Scan", "Original Invoice", "Original Packing List", "Tracker Document", "Other Documents", "Miscellaneous Supporting Doc"]

# ... [PASTE YOUR ORIGINAL HELPER FUNCTIONS HERE: get_gspread_client, load_log_data, save_log_data, etc.] ...

# ==========================================
# 4. ORIGINAL APP VIEWS (RE-ENABLED)
# ==========================================
# [PASTE YOUR ORIGINAL render_master_log AND render_admin_tracker HERE]

# ==========================================
# 5. NAVIGATION (FINAL)
# ==========================================
nav_selection = st.sidebar.radio("Navigation", ["📋 Master Log", "📦 Master Tracker", "⚙️ Supplier Admin", "👥 Client Admin"])

if nav_selection == "📋 Master Log": render_master_log()
elif nav_selection == "📦 Master Tracker": render_admin_tracker()
elif nav_selection == "⚙️ Supplier Admin": render_supplier_admin()
elif nav_selection == "👥 Client Admin": render_client_admin()
