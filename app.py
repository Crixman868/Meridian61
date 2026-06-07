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
# 1. SETUP & CSS
# ==========================================
st.set_page_config(page_title="Meridian Logistics", page_icon="📦", layout="wide")
COMPANY_LOGO_PATH = "company_logo.png"

st.markdown("""
<style>
    .stApp { background-color: #ffffff; }
    [data-testid="stExpander"] { background-color: #ffffff !important; border: 1px solid #e2e8f0; border-radius: 6px; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.04); margin-bottom: 10px; }
    [data-testid="stExpander"] summary p { font-weight: 600 !important; color: #1e293b !important; font-size: 1.05rem !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONSTANTS
# ==========================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1wUBZSnB7cJ2T5_iY5_POpfsNmZn0INGj08EdcLc7TsQ/edit?usp=sharing"
ROOT_FOLDER_ID = "1CITSPAI-BoFeQQLLkmeoX2wkjunTbpGm"
ALL_COUNTRIES = ["", "USA", "China", "UK", "Canada", "Brazil", "Mexico", "Panama", "Japan", "Germany", "India", "France", "Italy", "South Korea", "Spain", "Australia", "Taiwan", "Netherlands", "Vietnam", "Malaysia", "Singapore", "South Africa", "UAE", "Saudi Arabia", "Switzerland", "Sweden", "Poland", "Belgium", "Thailand", "Indonesia", "Turkey", "Philippines", "Ireland", "Other"]

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
# 3. HELPERS
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
    except Exception as e: 
        st.error(f"Failed to load: {e}")
        return pd.DataFrame(columns=ALL_LOG_COLUMNS)

def save_log_data(df):
    ws = get_gspread_client().open_by_url(SHEET_URL).sheet1
    ws.clear()
    df_reordered = df.reindex(columns=ALL_LOG_COLUMNS).fillna("")
    ws.update([df_reordered.columns.values.tolist()] + df_reordered.values.tolist())

# [Helper functions: upload_system_pdf_to_drive, upload_physical_file_to_drive, generate_html_document, etc., remain as established in previous approved code]
# NOTE: Ensure these are present in your app.py file

# ==========================================
# 4. VIEWS
# ==========================================

def render_master_log():
    st.subheader("🗄️ System Workspace Overview")
    df = load_log_data()
    for idx, row in df.iterrows():
        m61_id = str(row.get('M61 ID', 'N/A'))
        header_text = f"📦 CTNS: {row.get('TOTAL CTNS', '0')} | Status: {row.get('Status', 'Active')} | Client: {row.get('Client', 'Unassigned')} | Inv: {row.get('Invoice#', 'Pending')} | Cont: {row.get('Container #', 'Pending')} | {m61_id}"
        
        with st.expander(header_text):
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            new_cont = c1.text_input("Container #", value=row.get("Container #", ""), key=f"cont_{m61_id}")
            new_orig = c2.selectbox("Origin", ALL_COUNTRIES, index=ALL_COUNTRIES.index(row.get("Origin", "")) if row.get("Origin", "") in ALL_COUNTRIES else 0, key=f"orig_{m61_id}")
            new_eta = c3.date_input("ETA", value=datetime.now(), key=f"eta_{m61_id}")
            new_lodg = c4.radio("Doc Status", ["Yes", "No"], index=0 if row.get("Doc Status") == "Yes" else 1, horizontal=True, key=f"lodged_{m61_id}")
            new_stat = c5.selectbox("Status", ["Active", "Delivered"], key=f"stat_{m61_id}")
            new_naldo = c6.radio("NALDO", ["Yes", "No"], index=0 if row.get("NALDO") == "Yes" else 1, horizontal=True, key=f"naldo_{m61_id}")
            
            st.write("---")
            st.markdown("#### Document Control Matrix")
            grid = st.columns(5)
            for i, slot in enumerate(ALL_DOCS):
                with grid[i % 5]:
                    st.markdown(f"**{slot}**")
                    file_link = str(row.get(slot, "")).strip()
                    if file_link.startswith("http"): st.link_button("📄 View", url=file_link, use_container_width=True)
                    else: st.button("Pending", disabled=True, use_container_width=True)
            
            if st.button("💾 Save Shipment Updates", key=f"save_{m61_id}", type="primary"):
                df_u = load_log_data()
                df_u.at[idx, "Container #"] = new_cont
                # Update other fields...
                save_log_data(df_u)
                st.rerun()

# ==========================================
# 5. MAIN
# ==========================================
st.title("🚢 Meridian Command Console")
# [Ensure the Intake Pipeline and Dropdown Logic remain as approved]
