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
# 1. SETUP & SAFETY WRAPPER (DO NOT REMOVE)
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
        st.warning(f"Format mismatch in '{col}': {e}.")
        df.at[idx, col] = 0 if dtype in [int, float] else ""
        return df

# ==========================================
# 2. YOUR ORIGINAL HELPER FUNCTIONS
# ==========================================
# (These remain identical to your original code)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1wUBZSnB7cJ2T5_iY5_POpfsNmZn0INGj08EdcLc7TsQ/edit?usp=sharing"
ROOT_FOLDER_ID = "1CITSPAI-BoFeQQLLkmeoX2wkjunTbpGm"
LOG_COLUMNS = ["Row_UID", "Invoice No", "Client Name", "Container #", "Country of Origin", "ETA", "Lodged Status", "Shipment Status", "NALDO", "Total Cartons", "Commercial Invoice", "CARICOM Invoice", "Sequential Packing List", "Official Duties Assessment", "Bill of Lading Scan", "Original Invoice", "Original Packing List", "Tracker Document", "Other Documents", "Miscellaneous Supporting Doc"]

def get_gspread_client():
    creds_dict = json.loads(st.secrets["google_api"]["credentials"])
    creds = BotCredentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.readonly"])
    return gspread.authorize(creds)

def load_log_data():
    try: 
        ws = get_gspread_client().open_by_url(SHEET_URL).sheet1
        records = ws.get_all_records()
        df = pd.DataFrame(records) if records else pd.DataFrame(columns=LOG_COLUMNS)
        for col in LOG_COLUMNS:
            if col not in df.columns: df[col] = ""
        return df
    except Exception as e: 
        st.error(f"Failed to load data: {e}")
        return pd.DataFrame(columns=LOG_COLUMNS)

def save_log_data(df):
    ws = get_gspread_client().open_by_url(SHEET_URL).sheet1
    ws.clear()
    df = df[LOG_COLUMNS]
    ws.update([df.fillna("").columns.values.tolist()] + df.fillna("").values.tolist())
    return True

# ... [Keep all your original helper functions: upload_system_pdf_to_drive, upload_physical_file_to_drive, get_eta_status, get_img_b64, get_entity_profile, get_supplier_mapping, save_supplier_mapping, generate_html_document, create_print_button, display_html_preview] ...

# ==========================================
# 3. ADMIN TABS (NEW)
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
# 4. ORIGINAL APP VIEWS (MASTER LOG & TRACKER)
# ==========================================
# [Paste your original render_master_log and render_admin_tracker here]
# IMPORTANT: In your render_master_log 'Save' button, change your lines to use the wrapper:
# df_update = safe_update_log(df_update, row_index, "Container #", new_cont, str)

# ==========================================
# 5. NAVIGATION (FINAL)
# ==========================================
nav_selection = st.sidebar.radio("Navigation", ["📋 Master Log", "📦 Master Tracker", "⚙️ Supplier Admin", "👥 Client Admin"])

if nav_selection == "📋 Master Log": render_master_log()
elif nav_selection == "📦 Master Tracker": render_admin_tracker()
elif nav_selection == "⚙️ Supplier Admin": render_supplier_admin()
elif nav_selection == "👥 Client Admin": render_client_admin()
