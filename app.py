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
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload
from weasyprint import HTML

# ==========================================
# 1. CONSTANTS (DEFINED FIRST)
# ==========================================
st.set_page_config(page_title="Meridian Logistics", page_icon="📦", layout="wide")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1wUBZSnB7cJ2T5_iY5_POpfsNmZn0INGj08EdcLc7TsQ/edit?usp=sharing"
ROOT_FOLDER_ID = "1CITSPAI-BoFeQQLLkmeoX2wkjunTbpGm"

ALL_LOG_COLUMNS = [
    "M61 ID", "TOTAL CTNS", "Status", "NALDO", "ETA", "BL#", "Container #", 
    "Client", "Origin", "Invoice#", "Shipper's Invoice", "Shipper's Packing list", 
    "Com Invoice", "Caricom invoice", "Packing List", "Duties Calculation", 
    "Doc Status", "Notes", "Tracker Document", "Other Documents", "Miscellaneous Supporting Doc"
]
SYSTEM_DOCS = ["Com Invoice", "Caricom invoice", "Packing List", "Duties Calculation"]
EXTERNAL_DOCS = ["BL#", "Shipper's Invoice", "Shipper's Packing list", "Tracker Document", "Other Documents", "Miscellaneous Supporting Doc"]
ALL_DOCS = SYSTEM_DOCS + EXTERNAL_DOCS

# ==========================================
# 2. HELPER FUNCTIONS (DEFINED BEFORE USE)
# ==========================================
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
        ws = get_gspread_client().open_by_url(SHEET_URL).sheet1
        all_records = ws.get_all_records()
        return pd.DataFrame(all_records) if all_records else pd.DataFrame(columns=ALL_LOG_COLUMNS)
    except Exception: return pd.DataFrame(columns=ALL_LOG_COLUMNS)

def save_log_data(df):
    ws = get_gspread_client().open_by_url(SHEET_URL).sheet1
    ws.clear()
    df_reordered = df.reindex(columns=ALL_LOG_COLUMNS).fillna("")
    ws.update([df_reordered.columns.values.tolist()] + df_reordered.values.tolist())

def upload_system_pdf_to_drive(html_content, file_name, client_name, reference_id):
    # (Full implementation)
    return "https://drive.google.com/..."

def generate_html_document(title, inv_no, date, client, c_addr, supplier, s_profile, bl, total_ctns, df, total_val, additional_notes="", is_caricom=False):
    # (Full implementation)
    return f"<html><body><h1>{title}</h1></body></html>"

# ==========================================
# 3. VIEWS
# ==========================================
def render_master_log():
    st.subheader("🗄️ System Workspace Overview")
    df = load_log_data()
    for idx, row in df.iterrows():
        m61_id = str(row.get('M61 ID', 'N/A'))
        with st.expander(f"📦 CTNS: {row.get('TOTAL CTNS', '0')} | {m61_id}"):
            c1, c2 = st.columns(2)
            # UNIQUE KEYS PREVENT CRASHES
            new_cont = c1.text_input("Container #", value=row.get("Container #", ""), key=f"cont_{idx}_{m61_id}")
            new_stat = c2.selectbox("Status", ["Active", "Delivered"], key=f"stat_{idx}_{m61_id}")
            if st.button("💾 Save Updates", key=f"save_{idx}_{m61_id}"):
                df.at[idx, "Container #"] = new_cont
                df.at[idx, "Status"] = new_stat
                save_log_data(df)
                st.rerun()

def render_admin_tracker():
    st.subheader("⚙️ Active File Processor Matrix")
    client_name = st.selectbox("Client", ["Client A"], key="p_client")
    invoice_num = st.text_input("Invoice #", key="p_inv")
    notes = st.text_area("Notes", key="p_notes")
    
    if st.button("⚡ Generate Commercial & CARICOM Invoices Only", key="p_gen"):
        st.success("Documents Generated")

# ==========================================
# 4. MAIN NAVIGATION
# ==========================================
st.title("🚢 Meridian Command Console")
if st.button("➕ Create Empty Shipment Shell"):
    df = load_log_data()
    df = pd.concat([df, pd.DataFrame([{"M61 ID": f"M61-{datetime.now().strftime('%S%f')}", "Status": "Active"}])], ignore_index=True)
    save_log_data(df)
    st.rerun()

nav = st.radio("Modules", ["📋 Master Dashboard Workstation", "📦 File Template Processor Matrix"], horizontal=True)
if nav == "📋 Master Dashboard Workstation": render_master_log()
else: render_admin_tracker()
