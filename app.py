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
    .stApp { background-color: #ffffff; }
    [data-testid="stExpander"] { background-color: #ffffff !important; border: 1px solid #e2e8f0; border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

# Ensure folders exist
for folder in ["uploaded_docs", "logos", "signatures", "watermarks", "templates"]:
    if not os.path.exists(folder): os.makedirs(folder)

# ==========================================
# 2. HELPER FUNCTIONS & SAFE WRAPPER
# ==========================================
def safe_update_log(df, idx, col, val, dtype=str):
    """Prevent crashes by forcing data types before writing to the dataframe."""
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

# [Insert your existing get_gspread_client, get_drive_service, load_log_data, etc., here]
# (I have omitted these for brevity to fit the file, but keep your existing logic for these!)
# ... [Keep your existing helper functions: get_gspread_client, get_drive_service, load_log_data, save_log_data, etc.] ...

# ==========================================
# 3. ADMIN TABS (NEW)
# ==========================================
def render_supplier_admin():
    st.subheader("⚙️ Supplier Admin")
    fields = ['Name', 'Address', 'Palette', 'Typography', 'Header', 'GeoInv', 'Orient', 'PackOrient', 'WMToggle', 'WMOpacity', 'PrimaryHex', 'SecondaryHex', 'FontSize', 'LogoAlign', 'TableStyle', 'Template']
    with st.form("new_supplier_form"):
        data = {f: st.text_input(f) for f in fields}
        if st.form_submit_button("Save New Supplier"):
            if not data['Name']: st.error("Name required!"); return
            df = pd.read_csv("suppliers.csv") if os.path.exists("suppliers.csv") else pd.DataFrame(columns=fields)
            df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            df.to_csv("suppliers.csv", index=False)
            st.success("Supplier Saved")

def render_client_admin():
    st.subheader("👥 Client Admin")
    fields = ['Name', 'Address', 'Contact', 'Email', 'Phone', 'Notes']
    with st.form("new_client_form"):
        data = {f: st.text_input(f) for f in fields}
        if st.form_submit_button("Save New Client"):
            if not data['Name']: st.error("Name required!"); return
            df = pd.read_csv("clients.csv") if os.path.exists("clients.csv") else pd.DataFrame(columns=fields)
            df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            df.to_csv("clients.csv", index=False)
            st.success("Client Saved")

# ==========================================
# 4. APP VIEWS
# ==========================================

# [Your render_master_log and render_admin_tracker go here]
# IMPORTANT: In your render_master_log save logic, replace raw assignments with:
# df_update = safe_update_log(df_update, row_index, "Container #", new_cont, str)
# df_update = safe_update_log(df_update, row_index, "Total Cartons", new_ctns, int)

# ==========================================
# 5. NAVIGATION (UPDATED)
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
