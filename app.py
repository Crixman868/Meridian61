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
# 1. GLOBAL SETUP
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
# 3. HELPER FUNCTIONS
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
    except: return pd.DataFrame(columns=ALL_LOG_COLUMNS)

def save_log_data(df):
    ws = get_gspread_client().open_by_url(SHEET_URL).sheet1
    ws.clear()
    df_reordered = df.reindex(columns=ALL_LOG_COLUMNS).fillna("")
    ws.update([df_reordered.columns.values.tolist()] + df_reordered.values.tolist())

def upload_system_pdf_to_drive(html_content, file_name, client_name, reference_id):
    if not html_content: return "Pending"
    try:
        drive = get_drive_service()
        folders = drive.files().list(q=f"name='{client_name}' and '{ROOT_FOLDER_ID}' in parents", fields="files(id)").execute().get('files', [])
        client_folder = folders[0]['id'] if folders else drive.files().create(body={"name": client_name, "parents": [ROOT_FOLDER_ID], "mimeType": "application/vnd.google-apps.folder"}).execute()['id']
        inv_folders = drive.files().list(q=f"name='{reference_id}' and '{client_folder}' in parents", fields="files(id)").execute().get('files', [])
        inv_folder = inv_folders[0]['id'] if inv_folders else drive.files().create(body={"name": reference_id, "parents": [client_folder], "mimeType": "application/vnd.google-apps.folder"}).execute()['id']
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            HTML(string=html_content).write_pdf(tmp.name)
            media = MediaFileUpload(tmp.name, mimetype='application/pdf')
            file = drive.files().create(body={'name': file_name, 'parents': [inv_folder]}, media_body=media, fields='webViewLink').execute()
            os.remove(tmp.name)
            return file.get('webViewLink')
    except: return "Failed"

def generate_html_document(title, inv_no, date, client, c_addr, supplier, s_profile, bl, total_ctns, df, total_val, freight=None, additional_notes="", is_caricom=False):
    if is_caricom:
        desc_text = f"{additional_notes} as per invoice # {inv_no}, dated: {date}"
        return f"<html><body><h2>{title}</h2><p><b>Description:</b> {desc_text}</p></body></html>"
    return f"<html><body><h1>{title}</h1></body></html>"

# ==========================================
# 4. VIEWS
# ==========================================
def render_master_log():
    st.subheader("🗄️ System Workspace Overview")
    df = load_log_data()
    for idx, row in df.iterrows():
        m61_id = str(row.get('M61 ID', ''))
        header = f"📦 CTNS: {row.get('TOTAL CTNS', '0')} | Client: {row.get('Client', 'N/A')} | {m61_id}"
        with st.expander(header):
            c1, c2 = st.columns(2)
            new_cont = c1.text_input("Container #", value=row.get("Container #", ""), key=f"cont_{idx}_{m61_id}")
            new_stat = c2.selectbox("Status", ["Active", "Delivered"], index=0 if row.get("Status") != "Delivered" else 1, key=f"stat_{idx}_{m61_id}")
            if st.button("💾 Save", key=f"save_{idx}_{m61_id}"):
                df_u = load_log_data()
                df_u.at[idx, "Container #"] = new_cont
                df_u.at[idx, "Status"] = new_stat
                save_log_data(df_u)
                st.rerun()

def render_admin_tracker():
    st.subheader("⚙️ Active File Processor Matrix")
    client = st.selectbox("Client", ["Select..."] + sorted(pd.read_csv("clients.csv")["Name"].tolist()))
    inv_no = st.text_input("Invoice Number")
    additional_notes = st.text_area("Cargo Notes")
    
    if st.button("⚡ Generate Commercial & CARICOM Invoices Only"):
        # CARICOM logic with embedded layout logic as approved
        html = generate_html_document("CARICOM Invoice", inv_no, "07-06-2026", client, "Addr", "Supplier", {}, "BL123", 10, pd.DataFrame(), 100, additional_notes=additional_notes, is_caricom=True)
        st.success("Invoices Generated")

# ==========================================
# 5. MAIN
# ==========================================
st.title("🚢 Meridian Command Console")
df = load_log_data()

# Create Shell
if st.button("➕ Create Empty Shipment Shell"):
    next_num = max([int(re.findall(r'\d+', str(x))[0]) for x in df["M61 ID"] if re.findall(r'\d+', str(x))] + [1000]) + 1
    df = pd.concat([df, pd.DataFrame([{"M61 ID": f"M61-{next_num}", "Status": "Active"}])], ignore_index=True)
    save_log_data(df)
    st.rerun()

# Workspace Dropdown (CTNS First)
options = ["-- Choose Active Shell --"] + [f"📦 CTNS: {r.get('TOTAL CTNS', '0')} | Client: {r.get('Client', 'N/A')} | {r.get('M61 ID', '')}" for _, r in df.iterrows()]
selected = st.selectbox("Workspace", options, label_visibility="collapsed")
if selected != "-- Choose Active Shell --": st.session_state["target_m61_id"] = selected.split(" | ")[-1]

nav = st.radio("Modules", ["📋 Master Dashboard Workstation", "📦 File Template Processor Matrix"], horizontal=True)
if nav == "📋 Master Dashboard Workstation": render_master_log()
else: render_admin_tracker()
