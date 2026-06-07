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
# 1. SETUP
# ==========================================
st.set_page_config(page_title="Meridian Logistics", page_icon="📦", layout="wide")

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
# 3. HELPER FUNCTIONS (FULL VERSION)
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
    except Exception as e: return pd.DataFrame(columns=ALL_LOG_COLUMNS)

def save_log_data(df):
    ws = get_gspread_client().open_by_url(SHEET_URL).sheet1
    ws.clear()
    df_reordered = df.reindex(columns=ALL_LOG_COLUMNS).fillna("")
    ws.update([df_reordered.columns.values.tolist()] + df_reordered.values.tolist())

def get_eta_status(eta_date, shipment_status):
    if shipment_status == "Delivered": return "✅ DELIVERED", "#00b050"
    try:
        days = (pd.to_datetime(eta_date).date() - datetime.now().date()).days
        if days < 0: return "⚠️ Overdue", "#FF4500"
        if 0 <= days <= 5: return "🔴 Urgent", "#FF0000"
        return "🟢 On Track", "#008000"
    except: return "TBD", "#808080"

# ==========================================
# 4. VIEWS
# ==========================================
def render_master_log():
    st.subheader("🗄️ System Workspace Overview")
    df = load_log_data()
    for idx, row in df.iterrows():
        m61_id = str(row.get('M61 ID', 'N/A'))
        header_text = f"📦 CTNS: {row.get('TOTAL CTNS', '0')} | {row.get('Status', 'Active')} | Client: {row.get('Client', 'Unassigned')} | Inv: {row.get('Invoice#', 'Pending')} | {m61_id}"
        with st.expander(header_text):
            c1, c2, c3 = st.columns(3)
            new_cont = c1.text_input("Container #", value=row.get("Container #", ""), key=f"cont_{m61_id}")
            new_stat = c2.selectbox("Status", ["Active", "Delivered"], key=f"stat_{m61_id}")
            if st.button("💾 Save", key=f"save_{m61_id}"):
                df_u = load_log_data()
                df_u.at[idx, "Container #"] = new_cont
                save_log_data(df_u)
                st.rerun()

def render_admin_tracker():
    st.subheader("⚙️ Active File Processor Matrix")
    st.write("Intake logic active.")

# ==========================================
# 5. MAIN
# ==========================================
st.title("🚢 Meridian Command Console")
col_trigger, col_selector = st.columns([1, 1.5])

with col_trigger:
    if st.button("➕ Create Empty Shipment Shell"):
        df = load_log_data()
        nums = [int(re.findall(r'\d+', x)[0]) for x in df["M61 ID"].astype(str) if re.findall(r'\d+', x)]
        new_id = f"M61-{max(nums + [1000]) + 1}"
        df = pd.concat([df, pd.DataFrame([{"M61 ID": new_id, "Status": "Active"}])], ignore_index=True)
        save_log_data(df)
        st.session_state["target_m61_id"] = new_id
        st.rerun()

with col_selector:
    df = load_log_data()
    options = ["-- Choose Active Shell --"] + [f"📦 CTNS: {r.get('TOTAL CTNS', '0')} | Client: {r.get('Client', 'Unassigned')} | {r.get('M61 ID', '')}" for _, r in df.iterrows()]
    selected = st.selectbox("Workspace", options, label_visibility="collapsed")
    if selected != "-- Choose Active Shell --":
        st.session_state["target_m61_id"] = selected.split(" | ")[-1]

nav = st.radio("Modules", ["📋 Master Dashboard Workstation", "📦 File Template Processor Matrix"], horizontal=True)
if nav == "📋 Master Dashboard Workstation": render_master_log()
else: render_admin_tracker()
