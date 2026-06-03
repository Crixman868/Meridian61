import streamlit as st
import pandas as pd
import gspread
import json
import io
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ==========================================
# ☁️ CONFIGURATION & SECURITY
# ==========================================
st.set_page_config(page_title="Meridian61 Control Tower", page_icon="🗼", layout="wide")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1ipB1DaIdX_BS_0iSWRHMwHcP-wEpfu2pZzFT3nJtlho/edit?gid=0#gid=0"
DRIVE_FOLDER_ID = "19pHVBp63Y2j8y5BKPujV78rbwBVeYuBk"
SCOPES = ['https://www.googleapis.com/auth/drive']

if "logged_in" not in st.session_state or st.session_state["logged_in"] == False:
    st.error("🚨 Access Denied.")
    st.stop()

# --- GOOGLE CONNECTIONS ---
def get_gspread_client():
    creds_dict = json.loads(st.secrets["google_api"]["credentials"])
    return gspread.service_account_from_dict(creds_dict)

def get_drive_service():
    token_dict = json.loads(st.secrets["google_drive"]["token"])
    creds = Credentials.from_authorized_user_info(token_dict, SCOPES)
    return build('drive', 'v3', credentials=creds)

def load_log_data():
    try:
        gc = get_gspread_client()
        return pd.DataFrame(gc.open_by_url(SHEET_URL).sheet1.get_all_records())
    except: return pd.DataFrame()

def save_log_data(df):
    gc = get_gspread_client()
    ws = gc.open_by_url(SHEET_URL).sheet1
    ws.clear()
    ws.update([df.fillna("").columns.values.tolist()] + df.fillna("").values.tolist())

# --- VAULT LOGIC ---
DOC_SLOTS = [
    "Commercial Invoice", "CARICOM Invoice", "Sequential Packing List", "Official Duties Assessment",
    "Bill of Lading Scan", "Upload Original Invoice", "Upload Orig. Packing List", "Upload Tracker Document",
    "Other Documents", "Miscellaneous Supporting Doc"
]

st.title("🗼 Meridian 61: Logistics Control Tower")

df_all = load_log_data()
if df_all.empty:
    st.info("No shipments found. Initialize from Master Tracker.")
    st.stop()

# Ensure all 10 slots exist
for doc in DOC_SLOTS:
    if doc not in df_all.columns: df_all[doc] = "Pending"

# Display Shipments (Reverse order: newest first)
for idx, row in df_all.iloc[::-1].iterrows():
    # Primary Control Tower View
    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns([1, 1, 1.5, 1, 1])
        with c1: st.metric("CTN #", row.get("CTN Number", "N/A"))
        with c2: st.metric("ETA", row.get("ETA", "TBD"))
        with c3: st.markdown(f"**Route:** {row.get('Origin', 'N/A')} ➡️ {row.get('Destination', 'N/A')}")
        with c4: st.button("🖨️ Print Records", key=f"print_{idx}")
        with c5: st.markdown(f"**Customs State:** {row.get('Customs State', 'Pending')}")

        # Vault Cache
        with st.expander("📂 Vault Cache (10-Slot Matrix)"):
            grid = st.columns(5)
            for i, doc in enumerate(DOC_SLOTS):
                with grid[i % 5]:
                    link = str(row.get(doc, "Pending"))
                    st.caption(f"{i+1}. {doc}")
                    if link.startswith("http"):
                        st.success("✅ Vaulted")
                        st.markdown(f"[🔗 View]({link})")
                    else:
                        st.warning("⏳ Pending")
                        up = st.file_uploader(f"Upload", type="pdf", key=f"up_{idx}_{i}")
                        if up:
                            # Direct upload logic here
                            link = "https://drive.google.com/..." # Simplified placeholder
                            df_all.at[idx, doc] = link
                            save_log_data(df_all)
                            st.rerun()

st.success("Control Tower Synced.")