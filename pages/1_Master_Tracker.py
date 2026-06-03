import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import base64
import gspread
import json
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import jinja2
import re

# ==========================================
# ☁️ CONFIGURATION & SECURITY
# ==========================================
st.set_page_config(page_title="Master Tracker", page_icon="📦", layout="wide")

# Connect to Google Vault via st.secrets
def get_gspread_client():
    creds_dict = json.loads(st.secrets["google_api"]["credentials"])
    return gspread.service_account_from_dict(creds_dict)

SHEET_URL = "https://docs.google.com/spreadsheets/d/1ipB1DaIdX_BS_0iSWRHMwHcP-wEpfu2pZzFT3nJtlho/edit?gid=0#gid=0"
DRIVE_FOLDER_ID = "19pHVBp63Y2j8y5BKPujV78rbwBVeYuBk"

# --- SECURITY GATEKEEPER VALIDATION ---
if "logged_in" not in st.session_state or st.session_state["logged_in"] == False:
    st.error("🚨 Access Denied. Please log in through the Secure Gatekeeper.")
    st.stop()

st.title("📦 Command Console: Master Tracker")

# Setup Directories
DOC_DIR = "uploaded_docs"
for folder in [DOC_DIR, "logos", "signatures", "watermarks", "templates"]:
    if not os.path.exists(folder): os.makedirs(folder)

# --- PDF GENERATOR STUB (Paused for deployment stability) ---
def generate_html_pdf(title, inv_no, date, client, c_addr, supplier, s_profile, bl, total_ctns, df, total_val, freight=None, additional_notes="", payment_terms="", signatory_position="", is_packing=False, is_caricom=False, is_duties=False, duty_data=None):
    st.warning("PDF Engine is currently being upgraded. Document preview available below.")
    return b"", "<h1>PDF generation disabled for maintenance.</h1>"

# --- HELPER FUNCTIONS ---
def display_pdf(pdf_bytes, raw_html=None):
    if raw_html:
        preview_html = f'<div style="background-color: white; padding: 40px; margin: 10px auto; border-radius: 5px; box-shadow: 0px 4px 10px rgba(0,0,0,0.1); max-width: 900px; color: #333333;">{raw_html}</div>'
        components.html(preview_html, height=750, scrolling=True)
    else:
        st.warning("PDF Viewer is offline.")

def get_entity_profile(file_name, entity_name):
    profile = {"Name": entity_name, "Address": "Main Office Hub", "Template": "classic.html"}
    if os.path.exists(file_name):
        df = pd.read_csv(file_name)
        match = df[df["Name"] == entity_name]
        if not match.empty:
            for col in df.columns: profile[col] = match.iloc[0][col]
    return profile

# --- MAIN UI ---
client_file = "clients.csv"
supplier_file = "suppliers.csv"

client_options = ["Select a Client..."] + sorted(pd.read_csv(client_file)["Name"].dropna().tolist()) if os.path.exists(client_file) else ["Select a Client..."]
supplier_options = ["Select a Supplier..."] + sorted(pd.read_csv(supplier_file)["Name"].dropna().tolist()) if os.path.exists(supplier_file) else ["Select a Supplier..."]

st.write("---")
col1, col2 = st.columns([1, 1.3])

with col1:
    st.subheader("Data Intake & Matrix Mapping")
    client_name = st.selectbox("Client Workspace", client_options)
    supplier_name = st.selectbox("Supplier Profile", supplier_options)
    
    uploaded_file = st.file_uploader("Drop Raw Vendor Spreadsheet (CSV or Excel)", type=["csv", "xlsx"])
    
    # Placeholder for the rest of your form fields
    invoice_num = st.text_input("Invoice Number", value="269698487")
    st.write("*(Form functionality enabled)*")

with col2:
    st.subheader("Automated Document Delivery Streams")
    if uploaded_file:
        st.success("File uploaded. Ready for processing.")
    else:
        st.info("Please upload a file to begin.")