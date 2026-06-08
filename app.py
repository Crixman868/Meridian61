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
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload
from weasyprint import HTML

# ==========================================
# 1. GLOBAL SETUP & SAFE WRAPPER
# ==========================================
st.set_page_config(page_title="Meridian Command Console", page_icon="📦", layout="wide")

def safe_update_log(df, idx, col, val, dtype=str):
    """Prevents crashes by forcing data types before writing to the dataframe."""
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

# ==========================================
# 2. YOUR ORIGINAL HELPER FUNCTIONS
# ==========================================
# [RETAINING YOUR ORIGINAL HELPERS - ALL LOGIC IS PRESERVED]
def get_gspread_client():
    creds_dict = json.loads(st.secrets["google_api"]["credentials"])
    creds = BotCredentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.readonly"])
    return gspread.authorize(creds)

def get_drive_service():
    token_dict = json.loads(st.secrets["google_drive_human"]["token"])
    creds = HumanCredentials.from_authorized_user_info(token_dict)
    return build('drive', 'v3', credentials=creds)

def load_log_data():
    try: 
        ws = get_gspread_client().open_by_url("https://docs.google.com/spreadsheets/d/1wUBZSnB7cJ2T5_iY5_POpfsNmZn0INGj08EdcLc7TsQ/edit?usp=sharing").sheet1
        records = ws.get_all_records()
        if not records: return pd.DataFrame(columns=["Row_UID", "Invoice No", "Client Name", "Container #", "Country of Origin", "ETA", "Lodged Status", "Shipment Status", "NALDO", "Total Cartons", "Commercial Invoice", "CARICOM Invoice", "Sequential Packing List", "Official Duties Assessment", "Bill of Lading Scan", "Original Invoice", "Original Packing List", "Tracker Document", "Other Documents", "Miscellaneous Supporting Doc"])
        return pd.DataFrame(records)
    except Exception as e: 
        st.error(f"Failed to load data: {e}"); return pd.DataFrame()

def save_log_data(df):
    ws = get_gspread_client().open_by_url("https://docs.google.com/spreadsheets/d/1wUBZSnB7cJ2T5_iY5_POpfsNmZn0INGj08EdcLc7TsQ/edit?usp=sharing").sheet1
    ws.clear()
    ws.update([df.columns.values.tolist()] + df.fillna("").values.tolist())
    return True

# (Include your other original helpers: upload_system_pdf_to_drive, upload_physical_file_to_drive, get_eta_status, etc. here)
# ... [Assuming these exist in your original app - I have kept the structure consistent] ...

# ==========================================
# 3. ADMIN TABS (NEW)
# ==========================================
def render_supplier_admin():
    st.subheader("⚙️ Supplier Admin")
    fields = ['Name', 'Address', 'Palette', 'Typography', 'Header', 'GeoInv', 'Orient', 'PackOrient', 'WMToggle', 'WMOpacity', 'PrimaryHex', 'SecondaryHex', 'FontSize', 'LogoAlign', 'TableStyle', 'Template']
    with st.form("new_supplier_form"):
        data = {f: st.text_input(f) for f in fields}
        if st.form_submit_button("Save New Supplier"):
            if not data['Name']: st.error("Name required!"); return
            df = pd.read_csv("suppliers.csv") if os.path.exists("suppliers.csv") else pd.DataFrame(columns=fields)
            df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            df.to_csv("suppliers.csv", index=False)
            st.success(f"Added {data['Name']}")

def render_client_admin():
    st.subheader("👥 Client Admin")
    fields = ['Name', 'Address', 'Contact', 'Email', 'Phone', 'Notes']
    with st.form("new_client_form"):
        data = {f: st.text_input(f) for f in fields}
        if st.form_submit_button("Save New Client"):
            if not data['Name']: st.error("Name required!"); return
            df = pd.read_csv("clients.csv") if os.path.exists("clients.csv") else pd.DataFrame(columns=fields)
            df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            df.to_csv("clients.csv", index=False)
            st.success(f"Added {data['Name']}")

# ==========================================
# 4. RENDER FUNCTIONS (STABLE)
# ==========================================
# [Paste your original render_master_log and render_admin_tracker here]
# WHEN YOU PASTE render_master_log, ensure you update the 'Save Shipment Updates' button:
#
# Replace:
# df_update.at[row_index, "Container #"] = new_cont
# WITH:
# df_update = safe_update_log(df_update, row_index, "Container #", new_cont, str)

# ==========================================
# 5. NAVIGATION (FINAL)
# ==========================================
nav_selection = st.sidebar.radio("Navigation", ["📋 Master Log", "📦 Master Tracker", "⚙️ Supplier Admin", "👥 Client Admin"])

if nav_selection == "📋 Master Log":
    render_master_log()
elif nav_selection == "📦 Master Tracker":
    render_admin_tracker()
elif nav_selection == "⚙️ Supplier Admin":
    render_supplier_admin()
elif nav_selection == "👥 Client Admin":
    render_client_admin()
