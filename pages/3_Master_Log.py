import streamlit as st
import pandas as pd
import gspread
import json
from datetime import datetime

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

# --- HELPER: ETA LOGIC ---
def get_eta_status(eta_str):
    try:
        eta_date = datetime.strptime(str(eta_str), "%Y-%m-%d").date()
        days_diff = (eta_date - datetime.now().date()).days
        if days_diff < 0: return "⚠️ Overdue", "#FF4500" # Caution/Red
        if 0 <= days_diff <= 5: return "🔴 Urgent", "#FF0000"
        if 6 <= days_diff <= 14: return "🟡 Upcoming", "#FFD700"
        return "🟢 On Track", "#008000"
    except: return "TBD", "#808080"

# --- UI ---
st.title("🗄️ Master Log: Logistics Control Tower")

df = load_log_data()
DOC_SLOTS = [
    "Commercial Invoice", "CARICOM Invoice", "Sequential Packing List", "Official Duties Assessment",
    "Bill of Lading Scan", "Upload Original Invoice", "Upload Orig. Packing List", "Upload Tracker Document",
    "Other Documents", "Miscellaneous Supporting Doc"
]

for idx, row in df.iterrows():
    status_label, status_color = get_eta_status(row.get('ETA'))
    
    with st.expander(f"📦 CTN: {row.get('CTN Number', 'N/A')} | ETA: {row.get('ETA', 'N/A')} : {status_label}"):
        
        # Admin Fields
        col1, col2, col3, col4 = st.columns(4)
        with col1: 
            st.text_input("Container #", value=row.get("Container #", ""), key=f"cont_{idx}")
        with col2: 
            st.selectbox("Country of Origin", ["USA", "China", "Brazil", "UK", "Canada"], key=f"orig_{idx}")
        with col3: 
            st.date_input("ETA", value=pd.to_datetime(row.get("ETA", datetime.now())).date(), key=f"eta_{idx}")
        with col4: 
            st.radio("Lodged Status", ["Yes", "No"], horizontal=True, key=f"lodged_{idx}")

        # Document Vault
        st.write("---")
        st.subheader("Document Vault")
        grid = st.columns(5)
        for i, doc in enumerate(DOC_SLOTS):
            with grid[i % 5]:
                st.markdown(f"**{doc}**")
                st.file_uploader(f"Upload", key=f"up_{idx}_{i}")