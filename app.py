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
st.set_page_config(page_title="Meridian Logistics", page_icon="📦", layout="wide")

COMPANY_LOGO_PATH = "company_logo.png" 

st.markdown("""
<style>
    .stApp { background-color: #ffffff; }
    [data-testid="stExpander"] { background-color: #ffffff !important; border: 1px solid #e2e8f0; border-radius: 6px; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.04); margin-bottom: 10px; }
    [data-testid="stExpander"] summary p { font-weight: 600 !important; color: #1e293b !important; font-size: 1.05rem !important; }
    [data-testid="stExpander"] p, [data-testid="stExpander"] h3, [data-testid="stExpander"] h4, [data-testid="stExpander"] h5 { color: #1e293b !important; }
</style>
""", unsafe_allow_html=True)

for folder in ["uploaded_docs", "logos", "signatures", "watermarks", "templates"]:
    if not os.path.exists(folder): os.makedirs(folder)

# ==========================================
# 2. CONSTANTS
# ==========================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1wUBZSnB7cJ2T5_iY5_POpfsNmZn0INGj08EdcLc7TsQ/edit?usp=sharing"
ROOT_FOLDER_ID = "1CITSPAI-BoFeQQLLkmeoX2wkjunTbpGm"

ALL_COUNTRIES = [
    "", "USA", "China", "UK", "Canada", "Brazil", "Mexico", "Panama", "Japan", "Germany", 
    "India", "France", "Italy", "South Korea", "Spain", "Australia", "Taiwan", 
    "Netherlands", "Vietnam", "Malaysia", "Singapore", "South Africa", "UAE", 
    "Saudi Arabia", "Switzerland", "Sweden", "Poland", "Belgium", "Thailand", 
    "Indonesia", "Turkey", "Philippines", "Ireland", "Other"
]

ALL_LOG_COLUMNS = [
    "M61 ID", "TOTAL CTNS", "Status", "NALDO", "ETA", "BL#", "Container #", 
    "Client", "Origin", "Invoice#", "Shipper's Invoice", "Shipper's Packing list", 
    "Com Invoice", "Caricom invoice", "Packing List", "Duties Calculation", 
    "Doc Status", "Notes", "Tracker Document", "Other Documents", "Miscellaneous Supporting Doc"
]

SYSTEM_DOCS = ["Com Invoice", "Caricom invoice", "Packing List", "Duties Calculation"]
EXTERNAL_DOCS = ["BL#", "Shipper's Invoice", "Shipper's Packing list", "Tracker Document", "Other Documents", "Miscellaneous Supporting Doc"]
ALL_DOCS = SYSTEM_DOCS + EXTERNAL_DOCS

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
        all_records = ws.get_all_records()
        return pd.DataFrame(all_records) if all_records else pd.DataFrame(columns=ALL_LOG_COLUMNS)
    except Exception as e: 
        st.error(f"Failed to load: {e}")
        return pd.DataFrame(columns=ALL_LOG_COLUMNS)

def save_log_data(df):
    try:
        ws = get_gspread_client().open_by_url(SHEET_URL).sheet1
        ws.clear()
        df_reordered = df.reindex(columns=ALL_LOG_COLUMNS).fillna("")
        ws.update([df_reordered.columns.values.tolist()] + df_reordered.values.tolist())
        return True
    except Exception as e:
        st.error(f"Failed to sync: {e}")
        return False

def upload_system_pdf_to_drive(html_content, file_name, client_name, reference_id):
    if not html_content: return "Pending Upload"
    try:
        drive = get_drive_service()
        safe_client = str(client_name if client_name else "Unassigned").replace("'", "\\'")
        safe_ref = str(reference_id).replace("'", "\\'")
        
        folders = drive.files().list(q=f"name='{safe_client}' and '{ROOT_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false", fields="files(id, name)").execute().get('files', [])
        client_folder_id = folders[0]['id'] if folders else drive.files().create(body={"name": safe_client, "parents": [ROOT_FOLDER_ID], "mimeType": "application/vnd.google-apps.folder"}).execute()['id']
        
        inv_folders = drive.files().list(q=f"name='{safe_ref}' and '{client_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false", fields="files(id, name)").execute().get('files', [])
        inv_folder_id = inv_folders[0]['id'] if inv_folders else drive.files().create(body={"name": safe_ref, "parents": [client_folder_id], "mimeType": "application/vnd.google-apps.folder"}).execute()['id']
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            temp_pdf_path = temp_pdf.name
            
        HTML(string=html_content).write_pdf(temp_pdf_path)
        
        pdf_metadata = {'name': file_name, 'parents': [inv_folder_id]}
        pdf_media = MediaFileUpload(temp_pdf_path, mimetype='application/pdf', resumable=True)
        final_pdf = drive.files().create(body=pdf_metadata, media_body=pdf_media, fields='id, webViewLink').execute()
        
        os.remove(temp_pdf_path)
        return final_pdf.get('webViewLink', 'Upload Failed')
    except Exception as e:
        st.error(f"PDF Error: {e}")
        return "Upload Failed"

def get_entity_profile(file_name, entity_name):
    profile = {"Name": entity_name, "Address": "Main Office Hub", "Template": "classic.html"}
    if os.path.exists(file_name) and os.path.getsize(file_name) > 0:
        df = pd.read_csv(file_name)
        match = df[df["Name"] == entity_name]
        if not match.empty:
            for col in df.columns: profile[col] = match.iloc[0][col]
    return profile

def get_supplier_mapping(supplier):
    if os.path.exists("supplier_mappings.csv"):
        df = pd.read_csv("supplier_mappings.csv")
        match = df[df["Supplier"] == supplier]
        if not match.empty: return match.iloc[0]["DescCol"], match.iloc[0]["QtyCol"], match.iloc[0]["PriceCol"]
    return "-- Select --", "-- Select --", "-- Select --"

def save_supplier_mapping(supplier, desc, qty, price):
    df = pd.read_csv("supplier_mappings.csv") if os.path.exists("supplier_mappings.csv") else pd.DataFrame(columns=["Supplier", "DescCol", "QtyCol", "PriceCol"])
    df = df[df["Supplier"] != supplier]
    df = pd.concat([df, pd.DataFrame([{"Supplier": supplier, "DescCol": desc, "QtyCol": qty, "PriceCol": price}])], ignore_index=True)
    df.to_csv("supplier_mappings.csv", index=False)

def generate_html_document(title, inv_no, date, client, c_addr, supplier, s_profile, bl, total_ctns, df, total_val, freight=None, additional_notes="", payment_terms="", signatory_position="", is_packing=False, is_caricom=False, is_duties=False, duty_data=None):
    logo_path = get_img_b64(f"logos/{s_profile.get('Name', '')}_logo.png")
    
    if is_packing:
        table_rows = "".join([f'<tr><td style="padding:10px; border:1px solid #ccc;">{row.get("SPECIFICATION OF COMMODITIES","N/A")}</td><td style="padding:10px; border:1px solid #ccc; text-align:center;">{row.get("CTNS NOS","N/A")}</td><td style="padding:10px; border:1px solid #ccc; text-align:center;">{row.get("TOTAL CTNS",0)}</td><td style="padding:10px; border:1px solid #ccc; text-align:right;">{int(row.get("QUANTITY",0)):,}</td></tr>' for _, row in df.iterrows()])
        rendered_html = f'<html><body><table width="100%"><tr><td><img src="{logo_path}" height="50"></td><td align="right"><h2>{title}</h2></td></tr></table><p><b>Exporter:</b> {supplier}<br><b>Consignee:</b> {client}</p><table border="1" width="100%" cellspacing="0" cellpadding="5"><thead><tr bgcolor="#f7f7f7"><th>Description</th><th>Carton Nos</th><th>Total Ctns</th><th>Qty</th></tr></thead><tbody>{table_rows}</tbody></table></body></html>'
    elif is_caricom:
        desc_text = f"{additional_notes} as per invoice # {inv_no}, dated: {date}"
        rendered_html = f'<html><body><h2>{title}</h2><p><b>Exporter:</b> {supplier}<br><b>Consignee:</b> {client}</p><p>Description: {desc_text}</p></body></html>'
    else:
        template_env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath="./templates"))
        template = template_env.get_template(s_profile.get("Template", "classic.html")) if os.path.exists(f"./templates/{s_profile.get('Template', 'classic.html')}") else template_env.from_string("<h1>{{title}}</h1>")
        items = [{"Description": str(row["Description"])[:250], "Qty": f"{row.get('Qty', ''):,}", "UnitPrice": f"{row.get('UnitPrice', ''):.2f}", "Total": f"{row.get('Total Foreign (USD)', ''):.2f}"} for _, row in df.iterrows()]
        rendered_html = template.render({"title": title, "inv_no": inv_no, "date": date, "client_name": client, "supplier_name": supplier, "items": items, "subtotal": f"{total_val:,.2f}", "grand_total": f"{(total_val + (freight or 0)):,.2f}"})
    
    return rendered_html

def create_print_button(html_content, label):
    components.html(f"""<button onclick="var w=window.open(); w.document.write('{html_content.replace("'", "\\'")}'); w.print(); w.close();" style="width:100%; padding:10px; background:#2b2b2b; color:white; border:none; border-radius:4px;">🖨️ {label}</button>""", height=50)

def display_html_preview(raw_html):
    components.html(f'<div style="background:white; padding:20px; max-width:900px; margin:auto;">{raw_html}</div>', height=600, scrolling=True)

# ==========================================
# 4. VIEWS
# ==========================================

def render_master_log():
    st.subheader("🗄️ System Workspace Overview")
    df = load_log_data()
    for idx, row in df.iterrows():
        header_text = f"📦 CTNS: {row.get('TOTAL CTNS', '0')} | {row.get('Status', 'Active')} | Client: {row.get('Client', 'Unassigned')} | Inv: {row.get('Invoice#', 'Pending')} | Cont: {row.get('Container #', 'Pending')} | {row.get('M61 ID', 'N/A')}"
        with st.expander(header_text):
            st.write("Edit details and upload docs here...")

def render_admin_tracker():
    st.subheader("⚙️ Active File Processor Matrix")
    client_name = st.selectbox("Client", ["Select..."] + sorted(pd.read_csv("clients.csv")["Name"].tolist()))
    supplier_name = st.selectbox("Supplier", ["Select..."] + sorted(pd.read_csv("suppliers.csv")["Name"].tolist()))
    
    # Auto-load mapping
    map_desc, map_qty, map_price = get_supplier_mapping(supplier_name)
    
    uploaded_file = st.file_uploader("Upload Vendor Data")
    if uploaded_file:
        df_raw = pd.read_csv(uploaded_file)
        # Processor logic ... (Simplified for brevity)
        
        # Scenario A: Specific "Invoices Only" Trigger
        if st.button("⚡ Generate Commercial & CARICOM Invoices Only"):
            # CARICOM logic with auto-concatenated description
            inv_html = generate_html_document("Commercial Invoice", "INV123", "07-06-2026", client_name, "Addr", supplier_name, {}, "BL123", 10, pd.DataFrame(), 100)
            caricom_html = generate_html_document("CARICOM Invoice", "INV123", "07-06-2026", client_name, "Addr", supplier_name, {}, "BL123", 10, pd.DataFrame(), 100, is_caricom=True, additional_notes="Bulk Load")
            
            # Save to Drive logic ...
            st.success("Invoices Generated!")

# ==========================================
# 5. MAIN
# ==========================================
st.title("🚢 Meridian Command Console")
col_trigger, col_selector = st.columns([1, 1.5])

with col_trigger:
    if st.button("➕ Create Empty Shipment Shell"):
        df = load_log_data()
        next_num = max([int(re.findall(r'\d+', x)[0]) for x in df["M61 ID"].astype(str) if re.findall(r'\d+', x)] + [1000]) + 1
        new_id = f"M61-{next_num}"
        df = pd.concat([df, pd.DataFrame([{"M61 ID": new_id, "Status": "Active"}])], ignore_index=True)
        save_log_data(df)
        st.session_state["target_m61_id"] = new_id
        st.rerun()

with col_selector:
    df = load_log_data()
    options = ["-- Choose Active Shell --"] + [f"📦 CTNS: {r.get('TOTAL CTNS', '0')} | Client: {r.get('Client', 'Unassigned')} | {r.get('M61 ID', '')}" for _, r in df.iterrows()]
    selected = st.selectbox("Workspace", options, label_visibility="collapsed")
    if selected != "-- Choose Active Shell --":
        st.session_state["target_m61_id"] = selected.split(" | ")[-1]

nav = st.radio("Modules", ["📋 Master Dashboard Workstation", "📦 File Template Processor Matrix"], horizontal=True)
if nav == "📋 Master Dashboard Workstation": render_master_log()
else: render_admin_tracker()
