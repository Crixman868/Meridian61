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
    except Exception as e:
        st.error(f"Error loading spreadsheet: {e}")
        return pd.DataFrame()

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

if df.empty:
    st.warning("No data found. Please check your sheet connection.")
else:
    # All 10 Document Slots as defined in our matrix
    DOC_SLOTS = [
        "Commercial Invoice", "CARICOM Invoice", "Sequential Packing List", "Official Duties Assessment",
        "Bill of Lading Scan", "Original Invoice", "Original Packing List", "Tracker Document",
        "Other Documents", "Miscellaneous Supporting Doc"
    ]

    for idx, row in df.iterrows():
        # Parse Date & Status
        raw_eta = row.get("ETA")
        timestamp = pd.to_datetime(raw_eta, errors='coerce')
        current_date = timestamp.date() if not pd.isna(timestamp) else datetime.now().date()
        status_label, status_color = get_eta_status(current_date)
        
        # Dashboard Header
        header_text = (f"📦 CTN: {row.get('Invoice No', 'N/A')} | {status_label} | ETA: {current_date} | "
                       f"Cont: {row.get('Container #', 'N/A')} | Org: {row.get('Country of Origin', 'N/A')} | "
                       f"Lgd: {row.get('Lodged Status', 'N/A')}")

        with st.expander(header_text):
            # Admin Fields (Data Entry)
            col1, col2, col3, col4 = st.columns(4)
            with col1: st.text_input("Container #", value=str(row.get("Container #", "")), key=f"cont_{idx}")
            with col2: st.selectbox("Country of Origin", ["USA", "CHINA", "BRAZIL", "UK", "CANADA"], key=f"orig_{idx}")
            with col3: st.date_input("ETA", value=current_date, key=f"eta_{idx}")
            with col4: st.radio("Lodged Status", ["Yes", "No"], horizontal=True, key=f"lodged_{idx}")
            
            st.write("---")
            st.subheader("Document Vault (10-Slot Matrix)")
            
            # 10-Slot Grid
            grid = st.columns(5)
            for i, slot in enumerate(DOC_SLOTS):
                with grid[i % 5]:
                    st.markdown(f"**{slot}**")
                    file_url = row.get(slot)
                    if file_url and str(file_url).startswith("http"):
                        st.link_button(f"👁️ View/Print", url=file_url, key=f"view_{idx}_{i}")
                    st.file_uploader(f"Upload {slot}", key=f"up_{idx}_{i}", label_visibility="collapsed")
            
            if st.button("Save Shipment Updates", key=f"save_{idx}"):
                st.success("Changes captured!")