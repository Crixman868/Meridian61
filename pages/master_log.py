import streamlit as st

# --- PERSISTENCE CHECK ---
if st.query_params.get("logged_in") != "true":
    st.switch_page("app.py")

# --- LOGOUT ---
if st.sidebar.button("Logout"):
    st.query_params.clear()
    st.switch_page("app.py")

# --- YOUR EXISTING LOG CODE ---
st.title("📋 Master Log")
import pandas as pd
import gspread
import json
import os
import re
import tempfile
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials as HumanCredentials
from google.oauth2.service_account import Credentials as BotCredentials
from googleapiclient.http import MediaFileUpload

# --- CONFIG & AUTH ---
st.set_page_config(page_title="Master Log", layout="wide")

# --- UI AESTHETICS: PREDOMINANTLY WHITE & GEOMETRIC ---
st.markdown("""
<style>
    /* White background with subtle geometric shading */
    .stApp {
        background-color: #ffffff;
        background-image: 
            linear-gradient(45deg, #f8f9fa 25%, transparent 25%, transparent 75%, #f8f9fa 75%, #f8f9fa), 
            linear-gradient(45deg, #f8f9fa 25%, transparent 25%, transparent 75%, #f8f9fa 75%, #f8f9fa);
        background-size: 20px 20px;
        background-position: 0 0, 10px 10px;
    }
    
    /* Clean, crisp expander modules */
    [data-testid="stExpander"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.04);
        margin-bottom: 10px;
    }
    
    /* Emphasizing the Header Text for the Shopfloor */
    [data-testid="stExpander"] summary p {
        font-weight: 600 !important;
        color: #1e293b !important;
        font-size: 1.05rem !important;
    }

    /* --- THE INVISIBLE TEXT FIX FOR MOBILE --- */
    /* Forces all text inside the expanders to be dark, ignoring mobile dark mode */
    [data-testid="stExpander"] p, 
    [data-testid="stExpander"] h3, 
    [data-testid="stExpander"] h4, 
    [data-testid="stExpander"] h5 {
        color: #1e293b !important;
    }
</style>
""", unsafe_allow_html=True)

SHEET_URL = "https://docs.google.com/spreadsheets/d/1ipB1DaIdX_BS_0iSWRHMwHcP-wEpfu2pZzFT3nJtlho/edit?gid=0#gid=0"
ROOT_FOLDER_ID = "19pHVBp63Y2j8y5BKPujV78rbwBVeYuBk"

# --- SECURITY BOUNCER ---
# 1. Ensure user is logged in
if "logged_in" not in st.session_state or st.session_state["logged_in"] == False:
    st.error("🚨 Access Denied. Please log in through the Secure Gatekeeper.")
    st.stop()

# 2. Identify role
is_admin = st.session_state.get("is_admin", False)

# Expanded Logistics Country List
ALL_COUNTRIES = [
    "", "USA", "China", "UK", "Canada", "Brazil", "Mexico", "Japan", "Germany", 
    "India", "France", "Italy", "South Korea", "Spain", "Australia", "Taiwan", 
    "Netherlands", "Vietnam", "Malaysia", "Singapore", "South Africa", "UAE", 
    "Saudi Arabia", "Switzerland", "Sweden", "Poland", "Belgium", "Thailand", 
    "Indonesia", "Turkey", "Philippines", "Ireland", "Other"
]

# --- HYBRID AUTHENTICATION ---
def get_gspread_client():
    # 🤖 BOT CONNECTION (NEVER EXPIRES) - Used for Sheets
    creds_dict = json.loads(st.secrets["google_api"]["credentials"])
    creds = BotCredentials.from_service_account_info(
        creds_dict, 
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.readonly"]
    )
    return gspread.authorize(creds)

def get_drive_service():
    # 👤 HUMAN CONNECTION (REQUIRES REFRESH) - Used for Drive Uploads
    token_dict = json.loads(st.secrets["google_drive_human"]["token"])
    creds = HumanCredentials.from_authorized_user_info(token_dict)
    return build('drive', 'v3', credentials=creds)

def upload_physical_file_to_drive(uploaded_file, file_name, client_name, invoice_no):
    if not uploaded_file: return None
    try:
        drive = get_drive_service()
        folders = drive.files().list(q=f"name='{client_name}' and '{ROOT_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false", fields="files(id, name)").execute().get('files', [])
        client_folder_id = folders[0]['id'] if folders else drive.files().create(body={"name": client_name, "parents": [ROOT_FOLDER_ID], "mimeType": "application/vnd.google-apps.folder"}).execute()['id']
        
        inv_folders = drive.files().list(q=f"name='{invoice_no}' and '{client_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false", fields="files(id, name)").execute().get('files', [])
        inv_folder_id = inv_folders[0]['id'] if inv_folders else drive.files().create(body={"name": invoice_no, "parents": [client_folder_id], "mimeType": "application/vnd.google-apps.folder"}).execute()['id']
        
        file_ext = os.path.splitext(uploaded_file.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_file.write(uploaded_file.getvalue())
            temp_path = temp_file.name

        file_metadata = {'name': file_name, 'parents': [inv_folder_id]}
        media = MediaFileUpload(temp_path, resumable=True)
        file = drive.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        
        os.remove(temp_path)
        return file.get('webViewLink')
    except Exception as e:
        st.error(f"Drive Upload Error: {e}")
        return None

def load_log_data():
    try: return pd.DataFrame(get_gspread_client().open_by_url(SHEET_URL).sheet1.get_all_records())
    except Exception as e: 
        st.error(f"Failed to load data: {e}")
        return pd.DataFrame()

def save_log_data(df):
    try:
        ws = get_gspread_client().open_by_url(SHEET_URL).sheet1
        ws.clear()
        ws.update([df.fillna("").columns.values.tolist()] + df.fillna("").values.tolist())
        return True
    except Exception as e:
        st.error(f"Failed to sync with Google Sheets: {e}")
        return False

def get_eta_status(eta_date, shipment_status):
    if shipment_status == "Delivered":
        return "✅ DELIVERED", "#00b050"
    try:
        days_diff = (eta_date - datetime.now().date()).days
        if days_diff < 0: return "⚠️ Overdue", "#FF4500"
        if 0 <= days_diff <= 5: return "🔴 Urgent", "#FF0000"
        if 6 <= days_diff <= 14: return "🟡 Upcoming", "#FFD700"
        return "🟢 On Track", "#008000"
    except: return "TBD", "#808080"

# --- UI & LOGIC ---
st.title("🗄️ Master Log: Logistics Control Tower")

df = load_log_data()

if df.empty:
    st.warning("No data found in the Master Log.")
else:
    SYSTEM_DOCS = ["Commercial Invoice", "CARICOM Invoice", "Sequential Packing List", "Official Duties Assessment"]
    EXTERNAL_DOCS = ["Bill of Lading Scan", "Original Invoice", "Original Packing List", "Tracker Document", "Other Documents", "Miscellaneous Supporting Doc"]
    ALL_DOCS = SYSTEM_DOCS + EXTERNAL_DOCS

    for idx, row in df.iterrows():
        inv_no = str(row.get('Invoice No', 'N/A'))
        client_name = str(row.get('Client Name', 'Unknown Client'))
        ship_status = str(row.get("Shipment Status", "Active"))
        
        # Pulling the newly mapped Total Cartons metric safely
        total_cartons = str(row.get("Total Cartons", "N/A"))
        
        raw_eta = row.get("ETA")
        timestamp = pd.to_datetime(raw_eta, errors='coerce')
        current_date = timestamp.date() if not pd.isna(timestamp) else datetime.now().date()
        status_label, _ = get_eta_status(current_date, ship_status)
        
        naldo_val = str(row.get("NALDO", "No")).strip().upper()
        naldo_display = f"🔴 NALDO: YES" if naldo_val == "YES" else f"⚪ NALDO: NO"
        
        # --- SHOPFLOOR HEADER LAYOUT ---
        # Order: Cartons -> Status -> ETA -> Client -> Origin -> Lodged -> NALDO -> Invoice
        header_text = (f"📦 TOTAL CTNS: {total_cartons} | {status_label} | ETA: {current_date} | "
                       f"Client: {client_name} | Origin: {row.get('Country of Origin', 'N/A')} | "
                       f"Lodged: {row.get('Lodged Status', 'N/A')} | {naldo_display} | INV: {inv_no}")

        with st.expander(header_text):
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            
            if is_admin:
                with col1: new_cont = st.text_input("Container #", value=str(row.get("Container #", "")), key=f"cont_{idx}")
                with col2: new_orig = st.selectbox("Country of Origin", ALL_COUNTRIES, index=ALL_COUNTRIES.index(row.get("Country of Origin", "")) if row.get("Country of Origin", "") in ALL_COUNTRIES else 0, key=f"orig_{idx}")
                with col3: new_eta = st.date_input("ETA", value=current_date, key=f"eta_{idx}")
                with col4: new_lodg = st.radio("Lodged", ["Yes", "No"], index=0 if row.get("Lodged Status") == "Yes" else 1, horizontal=True, key=f"lodged_{idx}")
                with col5: new_stat = st.selectbox("Shipment Status", ["Active", "Delivered"], index=0 if ship_status != "Delivered" else 1, key=f"stat_{idx}")
                with col6: new_naldo = st.radio("NALDO Code", ["Yes", "No"], index=0 if naldo_val == "YES" else 1, horizontal=True, key=f"naldo_{idx}")
            else:
                with col1: st.markdown(f"**Container #:**<br>{row.get('Container #', 'N/A')}", unsafe_allow_html=True)
                with col2: st.markdown(f"**Origin:**<br>{row.get('Country of Origin', 'N/A')}", unsafe_allow_html=True)
                with col3: st.markdown(f"**ETA:**<br>{current_date}", unsafe_allow_html=True)
                with col4: st.markdown(f"**Lodged:**<br>{row.get('Lodged Status', 'No')}", unsafe_allow_html=True)
                with col5: st.markdown(f"**Status:**<br>{ship_status}", unsafe_allow_html=True)
                with col6: st.markdown(f"**NALDO Code:**<br>{'Yes' if naldo_val == 'YES' else 'No'}", unsafe_allow_html=True)
            
            st.write("---")
            st.subheader("Document Vault (10-Slot Matrix)")
            
            grid = st.columns(5)
            upload_cache = {} 

            for i, slot in enumerate(ALL_DOCS):
                with grid[i % 5]:
                    st.markdown(f"**{slot}**")
                    file_link = str(row.get(slot, ""))
                    
                    if file_link.startswith("http"):
                        clean_link = file_link
                        match = re.search(r'/d/([a-zA-Z0-9_-]+)', file_link)
                        if match:
                            file_id = match.group(1)
                            clean_link = f"https://drive.google.com/uc?export=download&id={file_id}"
                        st.link_button("📄 View Document", url=clean_link, key=f"view_{idx}_{i}", use_container_width=True)
                    else:
                        st.button("Pending Upload", disabled=True, key=f"pend_{idx}_{i}", use_container_width=True)
                    
                    if is_admin and slot in EXTERNAL_DOCS:
                        uploaded_file = st.file_uploader(f"Upload {slot}", key=f"up_{idx}_{i}", label_visibility="collapsed")
                        if uploaded_file:
                            upload_cache[slot] = uploaded_file
            
            if is_admin:
                if st.button("💾 Save Shipment Updates", key=f"save_{idx}", type="primary"):
                    with st.spinner("Processing updates..."):
                        df_update = load_log_data()
                        row_index = df_update.index[df_update['Invoice No'].astype(str) == inv_no].tolist()[0]
                        df_update.at[row_index, "Container #"] = new_cont
                        df_update.at[row_index, "Country of Origin"] = new_orig
                        df_update.at[row_index, "ETA"] = str(new_eta)
                        df_update.at[row_index, "Lodged Status"] = new_lodg
                        df_update.at[row_index, "Shipment Status"] = new_stat
                        df_update.at[row_index, "NALDO"] = new_naldo
                        for slot_name, up_file in upload_cache.items():
                            doc_filename = f"{inv_no}_{slot_name.replace(' ', '_')}.pdf"
                            new_link = upload_physical_file_to_drive(up_file, doc_filename, client_name, inv_no)
                            if new_link: df_update.at[row_index, slot_name] = new_link
                        if save_log_data(df_update):
                            st.success("✅ Updates saved!")
                            st.rerun()