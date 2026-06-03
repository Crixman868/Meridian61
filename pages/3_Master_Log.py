import streamlit as st
import pandas as pd
import gspread
import json
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# --- CONFIG ---
st.set_page_config(page_title="Master Log", layout="wide")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1ipB1DaIdX_BS_0iSWRHMwHcP-wEpfu2pZzFT3nJtlho/edit?gid=0#gid=0"
DRIVE_FOLDER_ID = "19pHVBp63Y2j8y5BKPujV78rbwBVeYuBk"

def get_gspread_client():
    creds_dict = json.loads(st.secrets["google_api"]["credentials"])
    return gspread.service_account_from_dict(creds_dict)

def upload_to_drive(file_obj, filename, folder_id):
    # This logic handles the actual move to your Drive folder
    creds_dict = json.loads(st.secrets["google_api"]["credentials"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=['https://www.googleapis.com/auth/drive'])
    service = build('drive', 'v3', credentials=creds)
    
    file_metadata = {'name': filename, 'parents': [folder_id]}
    media = MediaIoBaseUpload(file_obj, mimetype='application/pdf')
    file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    return file.get('webViewLink')

# --- UI ---
st.title("🗄️ Master Log: Logistics Control Tower")
df = load_log_data()

for idx, row in df.iterrows():
    # Parse date safely
    raw_eta = row.get("ETA")
    timestamp = pd.to_datetime(raw_eta, errors='coerce')
    current_date = timestamp.date() if not pd.isna(timestamp) else datetime.now().date()
    
    with st.expander(f"📦 CTN: {row.get('CTN Number', 'N/A')} | ETA: {current_date}"):
        # (Admin Editor fields remain here)
        
        # 3. Document Vault & Functional Print
        grid = st.columns(5)
        vault_cols = ["Commercial Invoice", "CARICOM Invoice", "Sequential Packing List", "Official Duties Assessment", "Bill of Lading Scan"]
        
        for i, col_name in enumerate(vault_cols):
            with grid[i]:
                st.markdown(f"**{col_name}**")
                
                # Check for existing link
                file_url = row.get(col_name)
                
                if file_url and str(file_url).startswith("http"):
                    st.link_button(f"👁️ View/Print", url=file_url)
                
                # Upload and auto-save
                uploaded_file = st.file_uploader(f"Upload {col_name}", key=f"up_{idx}_{i}", label_visibility="collapsed")
                if uploaded_file:
                    with st.spinner("Uploading..."):
                        link = upload_to_drive(uploaded_file, f"{row.get('CTN Number')}_{col_name}.pdf", DRIVE_FOLDER_ID)
                        # Here you would add: ws.update_cell(row_index, col_index, link)
                        st.success("Uploaded!")
                        st.rerun()