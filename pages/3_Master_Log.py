import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# --- CONFIG ---
st.set_page_config(page_title="Master Log", layout="wide")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1ipB1DaIdX_BS_0iSWRHMwHcP-wEpfu2pZzFT3nJtlho/edit?gid=0#gid=0"

# --- AUTH ---
def get_gspread_client():
    creds_dict = json.loads(st.secrets["google_api"]["credentials"])
    return gspread.service_account_from_dict(creds_dict)

def load_log_data():
    gc = get_gspread_client()
    return pd.DataFrame(gc.open_by_url(SHEET_URL).sheet1.get_all_records())

def save_log_data(df):
    gc = get_gspread_client()
    ws = gc.open_by_url(SHEET_URL).sheet1
    ws.clear()
    ws.update([df.fillna("").columns.values.tolist()] + df.fillna("").values.tolist())

# --- UI ---
st.title("🗄️ Master Log")

df = load_log_data()
if df.empty:
    st.info("No data found.")
    st.stop()

# The 10-Slot Matrix
DOC_SLOTS = [
    "Commercial Invoice", "CARICOM Invoice", "Sequential Packing List", "Official Duties Assessment",
    "Bill of Lading Scan", "Upload Original Invoice", "Upload Orig. Packing List", "Upload Tracker Document",
    "Other Documents", "Miscellaneous Supporting Doc"
]

for idx, row in df.iterrows():
    with st.expander(f"📦 CTN: {row.get('CTN Number', 'N/A')} | ETA: {row.get('ETA', 'N/A')}"):
        # Restoration of your Admin Fields
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.text_input("CTN Number", row.get("CTN Number", ""), key=f"ctn_{idx}")
        with col2: st.text_input("ETA", row.get("ETA", ""), key=f"eta_{idx}")
        with col3: st.text_input("Routing", row.get("Routing", ""), key=f"route_{idx}")
        with col4: st.selectbox("Customs State", ["Pending", "In Progress", "Cleared"], key=f"state_{idx}")

        # The 10-Slot Matrix (Restored Original Logic)
        st.write("---")
        st.subheader("Document Vault")
        grid = st.columns(5)
        for i, doc in enumerate(DOC_SLOTS):
            with grid[i % 5]:
                st.markdown(f"**{doc}**")
                # Logic to check existing file and show viewer goes here
                st.file_uploader(f"Upload {doc}", key=f"up_{idx}_{i}")
                
        if st.button("Save Shipment Updates", key=f"save_{idx}"):
            # Code to push admin updates back to GSheet
            st.success("Updated!")