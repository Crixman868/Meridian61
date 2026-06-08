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

COMPANY_LOGO_PATH = "company_logo.png" 

st.markdown("""
<style>
    .stApp {
        background-color: #ffffff;
        background-image: 
            linear-gradient(45deg, #f8f9fa 25%, transparent 25%, transparent 75%, #f8f9fa 75%, #f8f9fa), 
            linear-gradient(45deg, #f8f9fa 25%, transparent 25%, transparent 75%, #f8f9fa 75%, #f8f9fa);
        background-size: 20px 20px;
        background-position: 0 0, 10px 10px;
    }
    [data-testid="stExpander"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.04);
        margin-bottom: 10px;
    }
    [data-testid="stExpander"] summary p {
        font-weight: 600 !important;
        color: #1e293b !important;
        font-size: 1.05rem !important;
    }
    [data-testid="stExpander"] p, 
    [data-testid="stExpander"] h3, 
    [data-testid="stExpander"] h4, 
    [data-testid="stExpander"] h5 {
        color: #1e293b !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONSTANTS & DATA SCHEMA
# ==========================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1wUBZSnB7cJ2T5_iY5_POpfsNmZn0INGj08EdcLc7TsQ/edit?usp=sharing"
ROOT_FOLDER_ID = "1CITSPAI-BoFeQQLLkmeoX2wkjunTbpGm"

ALL_COUNTRIES = ["", "USA", "China", "UK", "Canada", "Brazil", "Mexico", "Panama", "Japan", "Germany", "India", "France", "Italy", "South Korea", "Spain", "Australia", "Taiwan", "Netherlands", "Vietnam", "Malaysia", "Singapore", "South Africa", "UAE", "Saudi Arabia", "Switzerland", "Sweden", "Poland", "Belgium", "Thailand", "Indonesia", "Turkey", "Philippines", "Ireland", "Other"]
SYSTEM_DOCS = ["Commercial Invoice", "CARICOM Invoice", "Sequential Packing List", "Official Duties Assessment"]
EXTERNAL_DOCS = ["Bill of Lading Scan", "Original Invoice", "Original Packing List", "Tracker Document", "Other Documents", "Miscellaneous Supporting Doc"]
ALL_DOCS = SYSTEM_DOCS + EXTERNAL_DOCS
LOG_COLUMNS = ["Row_UID", "Invoice No", "Client Name", "Container #", "Country of Origin", "ETA", "Lodged Status", "Shipment Status", "NALDO", "Total Cartons", "Commercial Invoice", "CARICOM Invoice", "Sequential Packing List", "Official Duties Assessment", "Bill of Lading Scan", "Original Invoice", "Original Packing List", "Tracker Document", "Other Documents", "Miscellaneous Supporting Doc"]

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def get_gspread_client():
    creds_dict = json.loads(st.secrets["google_api"]["credentials"])
    creds = BotCredentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.readonly"])
    return gspread.authorize(creds)

def get_drive_service():
    token_dict = json.loads(st.secrets["google_drive_human"]["token"])
    creds = HumanCredentials.from_authorized_user_info(token_dict)
    return build('drive', 'v3', credentials=creds)

def load_log_data():
    try: 
        ws = get_gspread_client().open_by_url(SHEET_URL).sheet1
        records = ws.get_all_records()
        df = pd.DataFrame(records) if records else pd.DataFrame(columns=LOG_COLUMNS)
        for col in LOG_COLUMNS:
            if col not in df.columns: df[col] = ""
        return df
    except Exception as e: 
        st.error(f"Failed to load data: {e}"); return pd.DataFrame(columns=LOG_COLUMNS)

def save_log_data(df):
    try:
        ws = get_gspread_client().open_by_url(SHEET_URL).sheet1
        ws.clear()
        df = df[LOG_COLUMNS]
        ws.update([df.fillna("").columns.values.tolist()] + df.fillna("").values.tolist())
        return True
    except Exception as e: st.error(f"Failed to sync: {e}"); return False

# --- SHEET-BASED ADMIN HELPERS ---
def load_admin_data(tab_name):
    try:
        ws = get_gspread_client().open_by_url(SHEET_URL).worksheet(tab_name)
        return pd.DataFrame(ws.get_all_records())
    except: return pd.DataFrame()

def save_admin_data(df, tab_name):
    ws = get_gspread_client().open_by_url(SHEET_URL).worksheet(tab_name)
    ws.clear()
    ws.update([df.columns.values.tolist()] + df.fillna("").values.tolist())

# --- REST OF ORIGINAL HELPERS ---
def upload_system_pdf_to_drive(html_content, file_name, client_name, invoice_no):
    if not html_content: return "Pending Upload"
    try:
        drive = get_drive_service()
        safe_client_name = str(client_name).replace("'", "\\'")
        safe_invoice_no = str(invoice_no).replace("'", "\\'")
        folders = drive.files().list(q=f"name='{safe_client_name}' and '{ROOT_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false", fields="files(id, name)").execute().get('files', [])
        client_folder_id = folders[0]['id'] if folders else drive.files().create(body={"name": client_name, "parents": [ROOT_FOLDER_ID], "mimeType": "application/vnd.google-apps.folder"}).execute()['id']
        inv_folders = drive.files().list(q=f"name='{safe_invoice_no}' and '{client_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false", fields="files(id, name)").execute().get('files', [])
        inv_folder_id = inv_folders[0]['id'] if inv_folders else drive.files().create(body={"name": str(invoice_no), "parents": [client_folder_id], "mimeType": "application/vnd.google-apps.folder"}).execute()['id']
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            temp_pdf_path = temp_pdf.name
        HTML(string=html_content).write_pdf(temp_pdf_path)
        pdf_media = MediaFileUpload(temp_pdf_path, mimetype='application/pdf', resumable=True)
        existing_files = drive.files().list(q=f"name='{file_name}' and '{inv_folder_id}' in parents and trashed=false", fields="files(id, webViewLink)").execute().get('files', [])
        if existing_files:
            file_id = existing_files[0]['id']
            final_pdf = drive.files().update(fileId=file_id, media_body=pdf_media, fields='id, webViewLink').execute()
        else:
            pdf_metadata = {'name': file_name, 'parents': [inv_folder_id]}
            final_pdf = drive.files().create(body=pdf_metadata, media_body=pdf_media, fields='id, webViewLink').execute()
        os.remove(temp_pdf_path)
        return final_pdf.get('webViewLink', 'Upload Failed')
    except Exception as e:
        st.error(f"PDF Engine Error: {e}"); return "Upload Failed"

def upload_physical_file_to_drive(uploaded_file, file_name, client_name, invoice_no):
    if not uploaded_file: return None
    try:
        drive = get_drive_service()
        safe_client_name = str(client_name).replace("'", "\\'")
        safe_invoice_no = str(invoice_no).replace("'", "\\'")
        folders = drive.files().list(q=f"name='{safe_client_name}' and '{ROOT_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false", fields="files(id, name)").execute().get('files', [])
        client_folder_id = folders[0]['id'] if folders else drive.files().create(body={"name": client_name, "parents": [ROOT_FOLDER_ID], "mimeType": "application/vnd.google-apps.folder"}).execute()['id']
        inv_folders = drive.files().list(q=f"name='{safe_invoice_no}' and '{client_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false", fields="files(id, name)").execute().get('files', [])
        inv_folder_id = inv_folders[0]['id'] if inv_folders else drive.files().create(body={"name": str(invoice_no), "parents": [client_folder_id], "mimeType": "application/vnd.google-apps.folder"}).execute()['id']
        file_ext = os.path.splitext(uploaded_file.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_file.write(uploaded_file.getvalue())
            temp_path = temp_file.name
        media = MediaFileUpload(temp_path, resumable=True)
        existing_files = drive.files().list(q=f"name='{file_name}' and '{inv_folder_id}' in parents and trashed=false", fields="files(id, webViewLink)").execute().get('files', [])
        if existing_files:
            file_id = existing_files[0]['id']
            file = drive.files().update(fileId=file_id, media_body=media, fields='id, webViewLink').execute()
        else:
            file_metadata = {'name': file_name, 'parents': [inv_folder_id]}
            file = drive.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        os.remove(temp_path)
        return file.get('webViewLink')
    except Exception as e:
        st.error(f"Drive Upload Error: {e}"); return None

def get_eta_status(eta_date, shipment_status):
    if shipment_status == "Delivered": return "✅ DELIVERED", "#00b050"
    try:
        days_diff = (eta_date - datetime.now().date()).days
        if days_diff < 0: return "⚠️ OVERDUE", "#FF4500"
        if 0 <= days_diff <= 7: return "🔴 URGENT", "#FF0000"
        if 8 <= days_diff <= 14: return "🟡 APPROACHING", "#FFD700"
        return "🟢 IN TRANSIT", "#008000"
    except: return "TBD", "#808080"

def get_img_b64(path):
    if os.path.exists(path):
        with open(path, "rb") as f: return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
    return None

def get_entity_profile(tab_name, entity_name):
    profile = {"Name": entity_name, "Address": "Main Office Hub", "Template": "classic.html"}
    df = load_admin_data(tab_name)
    if not df.empty and "Name" in df.columns:
        match = df[df["Name"] == entity_name]
        if not match.empty:
            for col in df.columns: profile[col] = match.iloc[0][col]
    return profile

def get_supplier_mapping(supplier):
    df = load_admin_data("SupplierMappings")
    if not df.empty and supplier in df["Supplier"].values:
        match = df[df["Supplier"] == supplier]
        return match.iloc[0]["DescCol"], match.iloc[0]["QtyCol"], match.iloc[0]["PriceCol"]
    return "-- Select --", "-- Select --", "-- Select --"

def save_supplier_mapping(supplier, desc, qty, price):
    df = load_admin_data("SupplierMappings")
    df = df[df["Supplier"] != supplier]
    new_entry = pd.DataFrame([{"Supplier": supplier, "DescCol": desc, "QtyCol": qty, "PriceCol": price}])
    df = pd.concat([df, new_entry], ignore_index=True)
    save_admin_data(df, "SupplierMappings")

def generate_html_document(title, inv_no, date, client, c_addr, supplier, s_profile, bl, total_ctns, df, total_val, freight=None, additional_notes="", payment_terms="", signatory_position="", is_packing=False, is_caricom=False, is_duties=False, duty_data=None):
    logo_path = get_img_b64(f"logos/{s_profile.get('Name', '')}_logo.png")
    sig_path = get_img_b64(f"signatures/{s_profile.get('Name', '')}_sig.png")
    if is_packing:
        table_rows = ""
        for idx, row in df.iterrows():
            table_rows += f'<tr><td style="padding:10px; border:1px solid #ccc;">{row.get("SPECIFICATION OF COMMODITIES","N/A")}</td><td style="padding:10px; border:1px solid #ccc; text-align:center;">{row.get("CTNS NOS","N/A")}</td><td style="padding:10px; border:1px solid #ccc; text-align:center;">{row.get("TOTAL CTNS",0)}</td><td style="padding:10px; border:1px solid #ccc; text-align:right;">{int(row.get("QUANTITY",0)):,}</td></tr>'
        rendered_html = f'<html><body><h2>{title}</h2><p><b>Exporter:</b> {supplier}<br><b>Consignee:</b> {client}<br>{c_addr}</p><table border="1" width="100%" cellspacing="0" cellpadding="5"><thead><tr bgcolor="#f7f7f7"><th>Description</th><th>Carton Nos</th><th>Total Ctns</th><th>Qty</th></tr></thead><tbody>{table_rows}</tbody></table></body></html>'
    elif is_duties:
        duty_data = duty_data or {}
        rendered_html = f'<html><body><h2>{title}</h2><p><b>Invoice:</b> {inv_no}</p><p>Total Duty: ${duty_data.get("grand_total_ttd",0):,.2f} TTD</p></body></html>'
    else:
        template_env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath="./templates"))
        chosen_template = s_profile.get("Template", "classic.html")
        if not os.path.exists(f"./templates/{chosen_template}"): chosen_template = "classic.html"
        try: template = template_env.get_template(chosen_template)
        except: template = template_env.from_string("<h1>{{title}}</h1><p>{{client_name}}</p>")
        items = []
        for idx, row in df.iterrows():
            items.append({"Description": str(row["Description"])[:250], "Qty": f"{row.get('Qty', ''):,}", "Total": f"{row.get('Total Foreign (USD)', ''):.2f}"})
        rendered_html = template.render({"title": title, "inv_no": inv_no, "client_name": client, "items": items})
    return rendered_html

def display_html_preview(raw_html):
    preview_html = f'<div style="background-color: white; padding: 40px; margin: 10px auto; border-radius: 5px; box-shadow: 0px 4px 10px rgba(0,0,0,0.1); max-width: 900px; color: #333333;">{raw_html}</div>'
    components.html(preview_html, height=750, scrolling=True)

# ==========================================
# 4. ADMIN RENDERERS
# ==========================================
def render_supplier_admin():
    st.subheader("⚙️ Supplier Admin")
    fields = ['Name', 'Address', 'Palette', 'Typography', 'Header', 'GeoInv', 'Orient', 'PackOrient', 'WMToggle', 'WMOpacity', 'PrimaryHex', 'SecondaryHex', 'FontSize', 'LogoAlign', 'TableStyle', 'Template']
    with st.form("new_supplier_form"):
        data = {f: st.text_input(f) for f in fields}
        if st.form_submit_button("Save New Supplier"):
            if not data['Name']: st.error("Name required!"); return
            df = load_admin_data("Suppliers")
            df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            save_admin_data(df, "Suppliers")
            st.success("Supplier Saved")

def render_client_admin():
    st.subheader("👥 Client Admin")
    fields = ['Name', 'Address', 'Contact', 'Email', 'Phone', 'Notes']
    with st.form("new_client_form"):
        data = {f: st.text_input(f) for f in fields}
        if st.form_submit_button("Save New Client"):
            if not data['Name']: st.error("Name required!"); return
            df = load_admin_data("Clients")
            df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            save_admin_data(df, "Clients")
            st.success("Client Saved")

def render_master_log():
    st.title("🗄️ Master Log: Logistics Control Tower")
    df = load_log_data()
    if df.empty:
        st.info("No data found.")
    else:
        for idx, row in df.iterrows():
            row_uid = str(row.get('Row_UID', ''))
            if not row_uid.strip(): continue 
            with st.expander(f"INV: {row.get('Invoice No')} | {row.get('Client Name')}"):
                new_cont = st.text_input("Container #", value=str(row.get("Container #", "")), key=f"cont_{idx}")
                if st.button("💾 Save Updates", key=f"save_{idx}", type="primary"):
                    df_update = load_log_data()
                    row_index = df_update.index[df_update['Row_UID'].astype(str).str.strip() == row_uid.strip()].tolist()[0]
                    df_update.at[row_index, "Container #"] = new_cont
                    save_log_data(df_update)
                    st.rerun()

def render_admin_tracker():
    st.title("📦 Command Console: Master Tracker")
    active_shell_uid = st.session_state.get("active_shell_uid", "")
    if not active_shell_uid:
        st.warning("Select a Workspace.")
        return
    st.write("Tracker module active.")

# ==========================================
# 5. NAVIGATION (FINAL - NO SIDEBAR)
# ==========================================
col_nav1, col_nav2, col_nav3, col_nav4 = st.columns(4)
with col_nav1:
    if st.button("📋 Master Log"): st.session_state["nav"] = "Log"
with col_nav2:
    if st.button("📦 Master Tracker"): st.session_state["nav"] = "Tracker"
with col_nav3:
    if st.button("⚙️ Supplier Admin"): st.session_state["nav"] = "Supplier"
with col_nav4:
    if st.button("👥 Client Admin"): st.session_state["nav"] = "Client"

st.write("---")
# Workspace Router
col_create, col_select = st.columns([1, 2])
with col_create:
    if st.button("➕ Create Empty Shipment Shell"):
        df_current = load_log_data()
        new_uid = f"UID-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        blank_row = {col: "" for col in LOG_COLUMNS}
        blank_row["Row_UID"] = new_uid
        blank_row["Invoice No"] = ""
        df_new = pd.concat([df_current, pd.DataFrame([blank_row])], ignore_index=True)
        if save_log_data(df_new):
            st.session_state["active_shell_uid"] = new_uid
            st.rerun()
with col_select:
    df_dropdown = load_log_data()
    dropdown_options = ["-- Choose Active Workspace --"]
    if not df_dropdown.empty:
        for _, r in df_dropdown.iterrows():
            dropdown_options.append(f"[{str(r.get('Row_UID','')).strip()}] INV: {str(r.get('Invoice No','')).strip()}")
    selected = st.selectbox("Select Target Workspace", dropdown_options)
    if selected != "-- Choose Active Workspace --":
        st.session_state["active_shell_uid"] = re.search(r'\[(.*?)\]', selected).group(1)

st.write("---")

nav = st.session_state.get("nav", "Log")
if nav == "Log": render_master_log()
elif nav == "Tracker": render_admin_tracker()
elif nav == "Supplier": render_supplier_admin()
elif nav == "Client": render_client_admin()
