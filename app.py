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
# 1. GLOBAL SETUP & CSS
# ==========================================
st.set_page_config(page_title="Meridian Command Console", page_icon="📦", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #ffffff; background-image: linear-gradient(45deg, #f8f9fa 25%, transparent 25%, transparent 75%, #f8f9fa 75%, #f8f9fa), linear-gradient(45deg, #f8f9fa 25%, transparent 25%, transparent 75%, #f8f9fa 75%, #f8f9fa); background-size: 20px 20px; background-position: 0 0, 10px 10px; }
    [data-testid="stExpander"] { background-color: #ffffff !important; border: 1px solid #e2e8f0; border-radius: 6px; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.04); margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. HELPER FUNCTIONS & SAFETY WRAPPER
# ==========================================

def safe_update_log(df, idx, col, val, dtype=str):
    """Safety Wrapper: Prevents crashes by forcing data types before writing to the dataframe."""
    try:
        if dtype == int:
            clean_val = int(float(val)) if val and str(val).strip() else 0
        elif dtype == float:
            clean_val = float(val) if val and str(val).strip() else 0.0
        else:
            clean_val = str(val) if val else ""
        df.at[idx, col] = clean_val
        return df
    except Exception as e:
        st.warning(f"Format mismatch in '{col}': {e}. Value set to default.")
        df.at[idx, col] = 0 if dtype in [int, float] else ""
        return df

# [PASTE YOUR EXISTING HELPER FUNCTIONS HERE: get_gspread_client, get_drive_service, load_log_data, save_log_data, etc.]
# (I am assuming these functions exist in your file; do not delete them)

# ==========================================
# 3. ADMIN TABS (NEW)
# ==========================================
def render_supplier_admin():
    st.subheader("⚙️ Supplier Admin")
    fields = ['Name', 'Address', 'Palette', 'Typography', 'Header', 'GeoInv', 'Orient', 'PackOrient', 'WMToggle', 'WMOpacity', 'PrimaryHex', 'SecondaryHex', 'FontSize', 'LogoAlign', 'TableStyle', 'Template']
    with st.form("new_supplier_form"):
        data = {f: st.text_input(f) for f in fields}
        if st.form_submit_button("Save New Supplier"):
            if not data['Name']: st.error("Name is required!"); return
            df = pd.read_csv("suppliers.csv") if os.path.exists("suppliers.csv") else pd.DataFrame(columns=fields)
            if data['Name'] in df['Name'].values: st.error("Supplier already exists!"); return
            df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            df.to_csv("suppliers.csv", index=False)
            st.success(f"Added {data['Name']} successfully!")

def render_client_admin():
    st.subheader("👥 Client Admin")
    fields = ['Name', 'Address', 'Contact', 'Email', 'Phone', 'Notes']
    with st.form("new_client_form"):
        data = {f: st.text_input(f) for f in fields}
        if st.form_submit_button("Save New Client"):
            if not data['Name']: st.error("Name is required!"); return
            df = pd.read_csv("clients.csv") if os.path.exists("clients.csv") else pd.DataFrame(columns=fields)
            if data['Name'] in df['Name'].values: st.error("Client already exists!"); return
            df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            df.to_csv("clients.csv", index=False)
            st.success(f"Added {data['Name']} successfully!")

# ==========================================
# 4. APP VIEWS
# ==========================================

# [INSERT YOUR RENDER_MASTER_LOG & RENDER_ADMIN_TRACKER FUNCTIONS HERE]

# IMPORTANT: In your render_master_log, replace your save logic button with this:
"""
if st.button("💾 Save Shipment Updates", key=f"save_{idx}", type="primary"):
    with st.spinner("Processing updates..."):
        df_update = load_log_data()
        row_index = df_update.index[df_update['Row_UID'].astype(str).str.strip() == row_uid.strip()].tolist()[0]
        
        # USE SAFETY WRAPPER HERE:
        df_update = safe_update_log(df_update, row_index, "Container #", new_cont, str)
        df_update = safe_update_log(df_update, row_index, "Country of Origin", new_orig, str)
        df_update = safe_update_log(df_update, row_index, "ETA", str(new_eta), str)
        df_update = safe_update_log(df_update, row_index, "Lodged Status", new_lodg, str)
        df_update = safe_update_log(df_update, row_index, "Shipment Status", new_stat, str)
        df_update = safe_update_log(df_update, row_index, "NALDO", new_naldo, str)
        
        # ... (rest of your upload logic)
        save_log_data(df_update)
        st.success("✅ Updates saved!")
        st.rerun()
"""

# ==========================================
# 5. NAVIGATION
# ==========================================
nav_selection = st.sidebar.radio("Navigation", ["📋 Master Log", "📦 Master Tracker", "⚙️ Supplier Admin", "👥 Client Admin"])

if nav_selection == "📋 Master Log":
    render_master_log()
elif nav_selection == "📦 Master Tracker":
    render_admin_tracker()
elif nav_selection == "⚙️ Supplier Admin":
    render_supplier_admin()
elif nav_selection == "👥 Client Admin":
    render_client_admin()
