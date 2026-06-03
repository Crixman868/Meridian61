import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import base64
import gspread
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import jinja2
import re
# from xhtml2pdf import pisa  <-- COMMENTED OUT TO FIX DEPLOYMENT

st.set_page_config(page_title="Master Tracker", page_icon="📦", layout="wide")

# ==========================================
# ☁️ CLOUD DATABASE & VAULT SETTINGS
# ==========================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1ipB1DaIdX_BS_0iSWRHMwHcP-wEpfu2pZzFT3nJtlho/edit?gid=0#gid=0"
DRIVE_FOLDER_ID = "19pHVBp63Y2j8y5BKPujV78rbwBVeYuBk"
SCOPES = ['https://www.googleapis.com/auth/drive']

# --- SECURITY GATEKEEPER VALIDATION ---
# Ensure this matches your Gatekeeper login state key
if "logged_in" not in st.session_state or st.session_state["logged_in"] == False:
    st.error("🚨 Access Denied. Please log in through the Secure Gatekeeper.")
    st.stop()

st.title("📦 Command Console: Master Tracker")

DOC_DIR = "uploaded_docs"
for folder in [DOC_DIR, "logos", "signatures", "watermarks", "templates"]:
    if not os.path.exists(folder): 
        os.makedirs(folder)

# --- NATIVE BROWSER PRINT UTILITY ENGINE ---
def create_print_button(html_content, button_label):
    escaped_html = html_content.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "")
    components_code = f"""
    <div style="display: flex; justify-content: center; margin-bottom: 8px;">
        <button onclick="triggerSystemPrint()" style="
            width: 100%;
            background-color: #2b2b2b;
            color: white;
            border: 1px solid #4a4a4a;
            padding: 10px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
            font-size: 14px;
            transition: background-color 0.2s;
        " onmouseover="this.style.backgroundColor='#444444'" onmouseout="this.style.backgroundColor='#2b2b2b'">🖨️ {button_label}</button>
    </div>
    <script>
        function triggerSystemPrint() {{
            var printWindow = window.open('', '_blank', 'height=700,width=900');
            printWindow.document.write('{escaped_html}');
            printWindow.document.close();
            printWindow.focus();
            setTimeout(function() {{
                printWindow.print();
                printWindow.close();
            }}, 400);
        }}
    </script>
    """
    components.html(components_code, height=55)

# --- PDF CANVAS VIEWER ENGINE ---
def display_pdf(pdf_bytes, raw_html=None):
    if raw_html:
        preview_html = f'<div style="background-color: white; padding: 40px; margin: 10px auto; border-radius: 5px; box-shadow: 0px 4px 10px rgba(0,0,0,0.1); max-width: 900px; color: #333333;">{raw_html}</div>'
        components.html(preview_html, height=750, scrolling=True)
        return
    st.warning("PDF Viewer is currently offline (PDF engine migration in progress).")

# --- VAULT RUNTIME ENGINES ---
def get_or_create_client_folder(drive_service, client_name, parent_id):
    safe_client = client_name.replace("'", "\\'")
    query = f"name='{safe_client}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
    response = drive_service.files().list(q=query, fields='files(id)').execute()
    folders = response.get('files', [])
    if not folders:
        return drive_service.files().create(body={'name': client_name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_id]}, fields='id').execute().get('id')
    return folders[0].get('id')

def upload_file_to_drive(drive_service, file_bytes, filename, folder_id):
    safe_file = filename.replace("'", "\\'")
    query = f"name='{safe_file}' and '{folder_id}' in parents and trashed=false"
    response = drive_service.files().list(q=query, fields='files(id)').execute()
    for f in response.get('files', []): 
        drive_service.files().delete(fileId=f.get('id')).execute()
    media = MediaIoBaseUpload(io.BytesIO(bytes(file_bytes)), mimetype='application/pdf', resumable=True)
    return drive_service.files().create(body={'name': filename, 'parents': [folder_id]}, media_body=media, fields='webViewLink').execute().get('webViewLink', '')

def load_log_data():
    try:
        # Note: In production, switch this to use st.secrets if possible
        df = pd.DataFrame(gspread.service_account(filename="credentials.json").open_by_url(SHEET_URL).sheet1.get_all_records())
        return df if not df.empty else pd.DataFrame()
    except: return pd.DataFrame()

def save_log_data(df):
    ws = gspread.service_account(filename="credentials.json").open_by_url(SHEET_URL).sheet1
    ws.clear()
    ws.update([df.fillna("").columns.values.tolist()] + df.fillna("").values.tolist())

def get_img_b64(path):
    if os.path.exists(path):
        with open(path, "rb") as f: return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
    return None

def get_entity_profile(file_name, entity_name):
    profile = {"Name": entity_name, "Address": "Main Office Hub", "Template": "classic.html"}
    if os.path.exists(file_name) and os.path.getsize(file_name) > 0:
        df = pd.read_csv(file_name)
        match = df[df["Name"] == entity_name]
        if not match.empty:
            for col in df.columns: 
                profile[col] = match.iloc[0][col]
    return profile

def get_supplier_mapping(supplier):
    if os.path.exists("supplier_mappings.csv") and os.path.getsize("supplier_mappings.csv") > 0:
        df = pd.read_csv("supplier_mappings.csv")
        match = df[df["Supplier"] == supplier]
        if not match.empty: return match.iloc[0]["DescCol"], match.iloc[0]["QtyCol"], match.iloc[0]["PriceCol"]
    return "-- Select --", "-- Select --", "-- Select --"

def save_supplier_mapping(supplier, desc, qty, price):
    df = pd.read_csv("supplier_mappings.csv") if os.path.exists("supplier_mappings.csv") else pd.DataFrame(columns=["Supplier", "DescCol", "QtyCol", "PriceCol"])
    df = df[df["Supplier"] != supplier]
    df = pd.concat([df, pd.DataFrame([{"Supplier": supplier, "DescCol": desc, "QtyCol": qty, "PriceCol": price}])], ignore_index=True)
    df.to_csv("supplier_mappings.csv", index=False)

# --- DOCUMENT FACTORY ENGINE ---
def generate_html_pdf(title, inv_no, date, client, c_addr, supplier, s_profile, bl, total_ctns, df, total_val, freight=None, additional_notes="", payment_terms="", signatory_position="", is_packing=False, is_caricom=False, is_duties=False, duty_data=None):
    st.warning("PDF Engine is currently being upgraded. Document content preview available below.")
    # Return placeholder data for now so the app doesn't crash
    return b"", "<h1>PDF generation temporarily disabled for platform maintenance.</h1>"

# --- REGISTRY SELECTION DICTIONARIES ---
client_options = ["Select a Client..."] + sorted(pd.read_csv("clients.csv")["Name"].dropna().tolist()) if os.path.exists("clients.csv") and os.path.getsize("clients.csv") > 0 else ["Select a Client..."]
supplier_options = ["Select a Supplier..."] + sorted(pd.read_csv("suppliers.csv")["Name"].dropna().tolist()) if os.path.exists("suppliers.csv") and os.path.getsize("suppliers.csv") > 0 else ["Select a Supplier..."]

st.write("---")
# ... (The rest of your UI code remains exactly as you had it below this line)