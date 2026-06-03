import streamlit as st
import pandas as pd
import gspread
import json
from datetime import datetime

# --- CONFIG & AUTH ---
st.set_page_config(page_title="Master Log", layout="wide")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1ipB1DaIdX_BS_0iSWRHMwHcP-wEpfu2pZzFT3nJtlho/edit?gid=0#gid=0"

def get_gspread_client():
    creds_dict = json.loads(st.secrets["google_api"]["credentials"])
    return gspread.service_account_from_dict(creds_dict)

def load_log_data():
    try:
        gc = get_gspread_client()
        return pd.DataFrame(gc.open_by_url(SHEET_URL).sheet1.get_all_records())
    except: return pd.DataFrame()

# --- HELPER: ETA LOGIC (Now accepts a dynamic date) ---
def get_eta_status(eta_date):
    try:
        days_diff = (eta_date - datetime.now().date()).days
        if days_diff < 0: return "⚠️ Overdue", "#FF4500"
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
    # Parse date or default to today
    raw_eta = row.get("ETA")
    timestamp = pd.to_datetime(raw_eta, errors='coerce')
    current_date = timestamp.date() if not pd.isna(timestamp) else datetime.now().date()
    
    # Shipment Expander
    with st.expander(f"📦 CTN: {row.get('CTN Number', 'N/A')} | ETA: {row.get('ETA', 'N/A')}"):
        
        # 1. Admin Fields
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1: cont = st.text_input("Container #", value=str(row.get("Container #", "")), key=f"cont_{idx}")
        with c2: orig = st.selectbox("Origin", ["USA", "China", "Brazil", "UK", "Canada"], key=f"orig_{idx}")
        with c3: new_eta = st.date_input("ETA", value=current_date, key=f"eta_{idx}")
        with c4: lodged = st.radio("Lodged", ["Yes", "No"], horizontal=True, key=f"lodged_{idx}")
        with c5: naldo = st.radio("NALDO Goods", ["Yes", "No"], horizontal=True, key=f"naldo_{idx}")
        
        # 2. Dynamic Status (Calculated instantly based on date_input)
        status_label, status_color = get_eta_status(new_eta)
        st.markdown(f"**Status:** :{status_color}[{status_label}]")

        # 3. Document Vault
        st.write("---")
        st.subheader("Document Vault")
        grid = st.columns(5)
        for i, doc in enumerate(DOC_SLOTS):
            with grid[i % 5]:
                st.markdown(f"**{doc}**")
                st.file_uploader(f"Upload", key=f"up_{idx}_{i}")
        
        if st.button("Save Shipment Updates", key=f"save_{idx}"):
            st.success("Changes captured!")