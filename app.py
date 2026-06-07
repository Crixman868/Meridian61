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
# 1. GLOBAL SETUP & CONSTANTS
# ==========================================
st.set_page_config(page_title="Meridian Logistics", page_icon="📦", layout="wide")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1wUBZSnB7cJ2T5_iY5_POpfsNmZn0INGj08EdcLc7TsQ/edit?usp=sharing"
ROOT_FOLDER_ID = "1CITSPAI-BoFeQQLLkmeoX2wkjunTbpGm"
ALL_COUNTRIES = ["", "USA", "China", "UK", "Canada", "Brazil", "Mexico", "Panama", "Japan", "Germany", "India", "France", "Italy", "South Korea", "Spain", "Australia", "Taiwan", "Netherlands", "Vietnam", "Malaysia", "Singapore", "South Africa", "UAE", "Saudi Arabia", "Switzerland", "Sweden", "Poland", "Belgium", "Thailand", "Indonesia", "Turkey", "Philippines", "Ireland", "Other"]
ALL_LOG_COLUMNS = ["M61 ID", "TOTAL CTNS", "Status", "NALDO", "ETA", "BL#", "Container #", "Client", "Origin", "Invoice#", "Shipper's Invoice", "Shipper's Packing list", "Com Invoice", "Caricom invoice", "Packing List", "Duties Calculation", "Doc Status", "Notes", "Tracker Document", "Other Documents", "Miscellaneous Supporting Doc"]
SYSTEM_DOCS = ["Com Invoice", "Caricom invoice", "Packing List", "Duties Calculation"]
EXTERNAL_DOCS = ["BL#", "Shipper's Invoice", "Shipper's Packing list", "Tracker Document", "Other Documents", "Miscellaneous Supporting Doc"]
ALL_DOCS = SYSTEM_DOCS + EXTERNAL_DOCS

st.markdown("""
<style>
    .stApp { background-color: #ffffff; background-image: linear-gradient(45deg, #f8f9fa 25%, transparent 25%, transparent 75%, #f8f9fa 75%, #f8f9fa), linear-gradient(45deg, #f8f9fa 25%, transparent 25%, transparent 75%, #f8f9fa 75%, #f8f9fa); background-size: 20px 20px; background-position: 0 0, 10px 10px; }
    [data-testid="stExpander"] { background-color: #ffffff !important; border: 1px solid #e2e8f0; border-radius: 6px; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.04); margin-bottom: 10px; }
    [data-testid="stExpander"] summary p { font-weight: 600 !important; color: #1e293b !important; font-size: 1.05rem !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. HELPER FUNCTIONS (FROM PERFECT BASE)
# ==========================================
def get_gspread_client():
    creds_dict = json.loads(st.secrets["google_api"]["credentials"])
    return gspread.authorize(BotCredentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.readonly"]))

def get_drive_service():
    token_dict = json.loads(st.secrets["google_drive_human"]["token"])
    return build('drive', 'v3', credentials=HumanCredentials.from_authorized_user_info(token_dict))

def load_log_data():
    try: 
        ws = get_gspread_client().open_by_url(SHEET_URL).sheet1
        all_records = ws.get_all_records()
        return pd.DataFrame(all_records) if all_records else pd.DataFrame(columns=ALL_LOG_COLUMNS)
    except: return pd.DataFrame(columns=ALL_LOG_COLUMNS)

def save_log_data(df):
    ws = get_gspread_client().open_by_url(SHEET_URL).sheet1
    ws.clear()
    df_reordered = df.reindex(columns=ALL_LOG_COLUMNS).fillna("")
    ws.update([df_reordered.columns.values.tolist()] + df_reordered.values.tolist())

def get_eta_status(eta_date, shipment_status):
    if shipment_status == "Delivered": return "✅ DELIVERED", "#00b050"
    return "🟢 Active", "#008000"

def generate_html_document(title, inv_no, date, client, c_addr, supplier, s_profile, bl, total_ctns, df, total_val, additional_notes="", is_caricom=False):
    if is_caricom:
        desc = f"{additional_notes} as per invoice # {inv_no}, dated: {date}"
        return f"<html><body><h1>{title}</h1><p><b>Description:</b> {desc}</p></body></html>"
    return f"<html><body><h1>{title}</h1></body></html>"

# ==========================================
# 3. MASTER DASHBOARD (ORIGINAL)
# ==========================================
def render_master_log():
    st.subheader("🗄️ System Workspace Overview")
    df = load_log_data()
    for idx, row in df.iterrows():
        m61_id = str(row.get('M61 ID', 'N/A'))
        header = f"📦 CTNS: {row.get('TOTAL CTNS', '0')} | {row.get('Client', 'N/A')} | {m61_id}"
        with st.expander(header):
            c1, c2 = st.columns(2)
            new_cont = c1.text_input("Container #", value=row.get("Container #", ""), key=f"cont_{idx}")
            new_stat = c2.selectbox("Status", ["Active", "Delivered"], index=0 if row.get("Status") != "Delivered" else 1, key=f"stat_{idx}")
            if st.button("💾 Save", key=f"save_{idx}"):
                df.at[idx, "Container #"] = new_cont
                df.at[idx, "Status"] = new_stat
                save_log_data(df)
                st.rerun()

# ==========================================
# 4. FILE PROCESSOR (SCOPE 2 INTEGRATION)
# ==========================================
def render_admin_tracker():
    st.subheader("⚙️ Active File Processor Matrix")
    client = st.text_input("Client Name", key="p_client")
    invoice_num = st.text_input("Invoice Number", key="p_inv")
    additional_notes = st.text_area("Cargo Notes", key="p_notes")
    
    if st.button("⚡ Generate Commercial & CARICOM Invoices Only", key="p_btn_generate"):
        html = generate_html_document("CARICOM Invoice", invoice_num, "07-06-2026", client, "", "", {}, "", 0, pd.DataFrame(), 0, additional_notes=additional_notes, is_caricom=True)
        st.write(html, unsafe_allow_html=True)

# ==========================================
# 5. MAIN
# ==========================================
st.title("🚢 Meridian Command Console")
if st.button("➕ Create Empty Shipment Shell"):
    df = load_log_data()
    next_num = max([int(re.findall(r'\d+', str(x))[0]) for x in df["M61 ID"] if re.findall(r'\d+', str(x))] + [1000]) + 1
    df = pd.concat([df, pd.DataFrame([{"M61 ID": f"M61-{next_num}", "Status": "Active"}])], ignore_index=True)
    save_log_data(df)
    st.rerun()

nav = st.radio("Modules", ["📋 Master Dashboard Workstation", "📦 File Template Processor Matrix"], horizontal=True)
if nav == "📋 Master Dashboard Workstation": render_master_log()
else: render_admin_tracker()
