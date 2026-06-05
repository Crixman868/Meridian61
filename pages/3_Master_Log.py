import streamlit as st
import pandas as pd
import gspread
import json
import os
import re
import tempfile
import base64
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload

# --- 1. CONFIG & AUTH ---
st.set_page_config(layout="wide")

# --- 2. SECURITY & SESSION LOCK ---
if not st.session_state.get("logged_in", False):
    st.switch_page("0_Gatekeeper.py")

is_admin = st.session_state.get("is_admin", False)

# --- 3. WATERMARK ENCODER ---
@st.cache_data
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

logo_base64 = get_base64_image("assets/logo.png")
if not logo_base64:
    logo_base64 = get_base64_image("logo.png")

# --- 4. BRANDING & DASHBOARD STYLING (THE UI SHELL) ---
sidebar_css = "[data-testid='stSidebar'] { display: none !important; }" if not is_admin else ""

st.markdown(f"""
    <style>
    {sidebar_css}
    .stApp {{
        background-color: #FFFFFF;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1440 900' preserveAspectRatio='xMidYMid slice'%3E%3Cellipse cx='720' cy='450' rx='900' ry='300' transform='rotate(-20 720 450)' fill='none' stroke='%23FF6700' stroke-width='80' stroke-opacity='0.06' /%3E%3Cellipse cx='720' cy='450' rx='900' ry='300' transform='rotate(-20 720 450)' fill='none' stroke='%23FF6700' stroke-width='4' stroke-opacity='0.35' /%3E%3C/svg%3E");
        background-attachment: fixed;
    }}
    .block-container {{
        background-color: #FFFFFF;
        padding: 40px !important;
        border-radius: 16px;
        box-shadow: 0px 15px 40px rgba(10, 34, 64, 0.08);
        border: 1px solid rgba(10, 34, 64, 0.05);
        margin-top: 40px;
        margin-bottom: 40px;
        z-index: 10;
        position: relative;
    }}
    .block-container::before {{
        content: "";
        position: absolute;
        top: 50%; left: 50%;
        transform: translate(-50%, -50%);
        width: 600px; height: 600px;
        background-image: url("data:image/png;base64,{logo_base64}");
        background-size: contain;
        background-repeat: no-repeat;
        opacity: 0.10;
        z-index: -1;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 5. LOGISTICS LOGIC (YOUR ORIGINAL FUNCTIONS) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1ipB1DaIdX_BS_0iSWRHMwHcP-wEpfu2pZzFT3nJtlho/edit?gid=0#gid=0"
ROOT_FOLDER_ID = "19pHVBp63Y2j8y5BKPujV78rbwBVeYuBk"
ALL_COUNTRIES = ["", "USA", "China", "UK", "Canada", "Brazil", "Mexico", "Japan", "Germany", "India", "France", "Italy", "South Korea", "Spain", "Australia", "Taiwan", "Netherlands", "Vietnam", "Malaysia", "Singapore", "South Africa", "UAE", "Saudi Arabia", "Switzerland", "Sweden", "Poland", "Belgium", "Thailand", "Indonesia", "Turkey", "Philippines", "Ireland", "Other"]

def get_creds():
    token_dict = json.loads(st.secrets["google_drive_human"]["token"])
    return Credentials.from_authorized_user_info(token_dict)

def get_gspread_client(): return gspread.authorize(get_creds())
def get_drive_service(): return build('drive', 'v3', credentials=get_creds())

def upload_physical_file_to_drive(uploaded_file, file_name, client_name, invoice_no):
    if not uploaded_file: return None
    try:
        drive = get_drive_service()
        folders = drive.files().list(q=f"name='{client_name}' and '{ROOT_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false").execute().get('files', [])
        client_folder_id = folders[0]['id'] if folders else drive.files().create(body={"name": client_name, "parents": [ROOT_FOLDER_ID], "mimeType": "application/vnd.google-apps.folder"}).execute()['id']
        inv_folders = drive.files().list(q=f"name='{invoice_no}' and '{client_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false").execute().get('files', [])
        inv_folder_id = inv_folders[0]['id'] if inv_folders else drive.files().create(body={"name": invoice_no, "parents": [client_folder_id], "mimeType": "application/vnd.google-apps.folder"}).execute()['id']
        file_ext = os.path.splitext(uploaded_file.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_file.write(uploaded_file.getvalue()); temp_path = temp_file.name
        file = drive.files().create(body={'name': file_name, 'parents': [inv_folder_id]}, media_body=MediaFileUpload(temp_path)).execute()
        os.remove(temp_path)
        return file.get('webViewLink')
    except Exception as e:
        st.error(f"Drive Upload Error: {e}"); return None

def load_log_data():
    try: return pd.DataFrame(get_gspread_client().open_by_url(SHEET_URL).sheet1.get_all_records())
    except: return pd.DataFrame()

def save_log_data(df):
    ws = get_gspread_client().open_by_url(SHEET_URL).sheet1
    ws.clear(); ws.update([df.fillna("").columns.values.tolist()] + df.fillna("").values.tolist()); return True

def get_eta_status(eta_date, shipment_status):
    if shipment_status == "Delivered": return "✅ DELIVERED", "#00b050"
    try:
        days_diff = (eta_date - datetime.now().date()).days
        if days_diff < 0: return "⚠️ Overdue", "#FF4500"
        if 0 <= days_diff <= 5: return "🔴 Urgent", "#FF0000"
        if 6 <= days_diff <= 14: return "🟡 Upcoming", "#FFD700"
        return "🟢 On Track", "#008000"
    except: return "TBD", "#808080"

# --- 6. UI CONTENT ---
st.title("🗄️ Master Log: Logistics Control Tower")
df = load_log_data()

if df.empty: st.warning("No data found.")
else:
    SYSTEM_DOCS = ["Commercial Invoice", "CARICOM Invoice", "Sequential Packing List", "Official Duties Assessment"]
    EXTERNAL_DOCS = ["Bill of Lading Scan", "Original Invoice", "Original Packing List", "Tracker Document", "Other Documents", "Miscellaneous Supporting Doc"]
    ALL_DOCS = SYSTEM_DOCS + EXTERNAL_DOCS

    for idx, row in df.iterrows():
        inv_no = str(row.get('Invoice No', 'N/A'))
        with st.expander(f"📦 CTN: {row.get('Total Cartons')} | {inv_no} | {row.get('Client Name')}"):
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            if is_admin:
                with col1: new_cont = st.text_input("Container #", value=str(row.get("Container #", "")), key=f"cont_{idx}")
                with col2: new_orig = st.selectbox("Country of Origin", ALL_COUNTRIES, index=ALL_COUNTRIES.index(row.get('Country of Origin', 'USA')) if row.get('Country of Origin') in ALL_COUNTRIES else 0, key=f"orig_{idx}")
                # ... (Additional Admin fields)
                if st.button("💾 Save Updates", key=f"save_{idx}", type="primary"):
                    st.success("Syncing...") # Add your sync logic here
            else:
                st.info("Read-only access")