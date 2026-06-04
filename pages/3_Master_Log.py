import streamlit as st
import pandas as pd
import gspread
import json
from datetime import datetime

# --- CONFIG & AUTH ---
st.set_page_config(page_title="Master Log", layout="wide")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1ipB1DaIdX_BS_0iSWRHMwHcP-wEpfu2pZzFT3nJtlho/edit?gid=0#gid=0"

# --- FUNCTIONS DEFINED FIRST ---
def get_gspread_client():
    creds_dict = json.loads(st.secrets["google_api"]["credentials"])
    return gspread.service_account_from_dict(creds_dict)

def load_log_data():
    try:
        gc = get_gspread_client()
        return pd.DataFrame(gc.open_by_url(SHEET_URL).sheet1.get_all_records())
    except Exception as e:
        return pd.DataFrame()

def get_eta_status(eta_date):
    try:
        days_diff = (eta_date - datetime.now().date()).days
        if days_diff < 0: return "⚠️ Overdue", "#FF4500"
        if 0 <= days_diff <= 5: return "🔴 Urgent", "#FF0000"
        if 6 <= days_diff <= 14: return "🟡 Upcoming", "#FFD700"
        return "🟢 On Track", "#008000"
    except: return "TBD", "#808080"

# --- MAIN EXECUTION ---
st.title("🗄️ Master Log: Logistics Control Tower")

# Call the function here, after all definitions
df = load_log_data()

if df.empty:
    st.info("No data found in the Master Log.")
else:
    for idx, row in df.iterrows():
        raw_eta = row.get("ETA")
        timestamp = pd.to_datetime(raw_eta, errors='coerce')
        current_date = timestamp.date() if not pd.isna(timestamp) else datetime.now().date()
        
        status_label, status_color = get_eta_status(current_date)
        
        header_text = (f"📦 CTN: {row.get('CTN Number', 'N/A')} | {status_label} | ETA: {current_date} | "
                       f"Cont: {row.get('Container #', 'N/A')} | Org: {row.get('Origin', 'N/A')} | "
                       f"Lgd: {row.get('Lodged', 'N/A')} | NALDO: {row.get('NALDO', 'N/A')}")
        
        with st.expander(header_text):
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1: st.text_input("Container #", value=str(row.get("Container #", "")), key=f"cont_{idx}")
            with c2: st.selectbox("Origin", ["USA", "China", "Brazil", "UK", "Canada"], key=f"orig_{idx}")
            with c3: st.date_input("ETA", value=current_date, key=f"eta_{idx}")
            with c4: st.radio("Lodged", ["Yes", "No"], horizontal=True, key=f"lodged_{idx}")
            with c5: st.radio("NALDO Goods", ["Yes", "No"], horizontal=True, key=f"naldo_{idx}")
            
            st.write("---")
            st.subheader("Document Vault (View & Print)")
            grid = st.columns(5)
            
            vault_cols = ["Commercial Invoice", "CARICOM Invoice", "Sequential Packing List", "Official Duties Assessment", "Bill of Lading Scan"]
            for i, col_name in enumerate(vault_cols):
                with grid[i]:
                    st.markdown(f"**{col_name}**")
                    file_url = row.get(col_name)
                    if file_url and str(file_url).startswith("http"):
                        st.link_button(f"👁️ View/Print", url=file_url, key=f"view_{idx}_{i}")
                    else:
                        st.file_uploader(f"Upload {col_name}", key=f"up_{idx}_{i}", label_visibility="collapsed")
            
            if st.button("Save Shipment Updates", key=f"save_{idx}"):
                st.success("Changes captured!")