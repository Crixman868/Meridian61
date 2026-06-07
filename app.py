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
    /* White background with subtle geometric shading for the main app */
    .stApp {
        background-color: #ffffff;
        background-image: 
            linear-gradient(45deg, #f8f9fa 25%, transparent 25%, transparent 75%, #f8f9fa 75%, #f8f9fa), 
            linear-gradient(45deg, #f8f9fa 25%, transparent 25%, transparent 75%, #f8f9fa 75%, #f8f9fa);
        background-size: 20px 20px;
        background-position: 0 0, 10px 10px;
    }
    
    /* Clean, crisp expander modules */
    [data-testid="stExpander"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.04);
        margin-bottom: 10px;
    }
    
    /* Emphasizing the Header Text for the Shopfloor */
    [data-testid="stExpander"] summary p {
        font-weight: 600 !important;
        color: #1e293b !important;
        font-size: 1.05rem !important;
    }

    /* --- THE INVISIBLE TEXT FIX FOR MOBILE --- */
    [data-testid="stExpander"] p, 
    [data-testid="stExpander"] h3, 
    [data-testid="stExpander"] h4, 
    [data-testid="stExpander"] h5 {
        color: #1e293b !important;
    }
</style>
""", unsafe_allow_html=True)

# Create required local directories if they don't exist
for folder in ["uploaded_docs", "logos", "signatures", "watermarks", "templates"]:
    if not os.path.exists(folder): os.makedirs(folder)

# ==========================================
# 2. CONSTANTS (DEVELOPMENT SANDBOX WORKSPACE)
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

# Exact layout sequence matching the staff muscle memory + full document 10-slot matrix
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
# 3. HELPER FUNCTIONS (API & DATA)
# ==========================================
def get_gspread_client():
    creds_dict = json.loads(st.secrets["google_api"]["credentials"])
    creds = BotCredentials.from_service_account_info(
        creds_dict, 
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.readonly"]
    )
    return gspread.authorize(creds)

def get_drive_service():
    token_dict = json.loads(st.secrets["google_drive_human"]["token"])
    creds = HumanCredentials.from_authorized_user_info(token_dict)
    return build('drive', 'v3', credentials=creds)

def load_log_data():
    try: 
        ws = get_gspread_client().open_by_url(SHEET_URL).sheet1
        all_records = ws.get_all_records()
        if not all_records:
            return pd.DataFrame(columns=ALL_LOG_COLUMNS)
        return pd.DataFrame(all_records)
    except Exception as e: 
        st.error(f"Failed to load data from Sandbox: {e}")
        return pd.DataFrame(columns=ALL_LOG_COLUMNS)

def save_log_data(df):
    try:
        ws = get_gspread_client().open_by_url(SHEET_URL).sheet1
        ws.clear()
        
        # Ensure correct formatting structure matching explicit sequential schema headers
        df_reordered = df.reindex(columns=ALL_LOG_COLUMNS).fillna("")
        ws.update([df_reordered.columns.values.tolist()] + df_reordered.values.tolist())
        return True
    except Exception as e:
        st.error(f"Failed to sync with Google Sheets: {e}")
        return False

def upload_system_pdf_to_drive(html_content, file_name, client_name, reference_id):
    if not html_content: return "Pending Upload"
    try:
        drive = get_drive_service()
        
        # --- THE APOSTROPHE FIX ---
        safe_client = str(client_name if client_name else "Unassigned_Client").replace("'", "\\'")
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
        st.error(f"PDF Engine Error for {file_name}: {e}")
        return "Upload Failed"

def upload_physical_file_to_drive(uploaded_file, file_name, client_name, reference_id):
    if not uploaded_file: return None
    try:
        drive = get_drive_service()
        
        # --- THE APOSTROPHE FIX ---
        safe_client = str(client_name if client_name else "Unassigned_Client").replace("'", "\\'")
        safe_ref = str(reference_id).replace("'", "\\'")
        
        folders = drive.files().list(q=f"name='{safe_client}' and '{ROOT_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false", fields="files(id, name)").execute().get('files', [])
        client_folder_id = folders[0]['id'] if folders else drive.files().create(body={"name": safe_client, "parents": [ROOT_FOLDER_ID], "mimeType": "application/vnd.google-apps.folder"}).execute()['id']
        
        inv_folders = drive.files().list(q=f"name='{safe_ref}' and '{client_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false", fields="files(id, name)").execute().get('files', [])
        inv_folder_id = inv_folders[0]['id'] if inv_folders else drive.files().create(body={"name": safe_ref, "parents": [client_folder_id], "mimeType": "application/vnd.google-apps.folder"}).execute()['id']
        
        file_ext = os.path.splitext(uploaded_file.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_file.write(uploaded_file.getvalue())
            temp_path = temp_file.name

        file_metadata = {'name': file_name, 'parents': [inv_folder_id]}
        media = MediaFileUpload(temp_path, resumable=True)
        file = drive.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        
        os.remove(temp_path)
        return file.get('webViewLink')
    except Exception as e:
        st.error(f"Drive Upload Error: {e}")
        return None

def get_eta_status(eta_date, shipment_status):
    if shipment_status == "Delivered":
        return "✅ DELIVERED", "#00b050"
    try:
        days_diff = (eta_date - datetime.now().date()).days
        if days_diff < 0: return "⚠️ Overdue", "#FF4500"
        if 0 <= days_diff <= 5: return "🔴 Urgent", "#FF0000"
        if 6 <= days_diff <= 14: return "🟡 Upcoming", "#FFD700"
        return "🟢 On Track", "#008000"
    except: return "TBD", "#808080"

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
            for col in df.columns: profile[col] = match.iloc[0][col]
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

def generate_html_document(title, inv_no, date, client, c_addr, supplier, s_profile, bl, total_ctns, df, total_val, freight=None, additional_notes="", payment_terms="", signatory_position="", is_packing=False, is_caricom=False, is_duties=False, duty_data=None):
    logo_path = get_img_b64(f"logos/{s_profile.get('Name', '')}_logo.png")
    
    if is_packing:
        table_rows = ""
        for idx, row in df.iterrows():
            table_rows += f'<tr><td style="padding:10px; border:1px solid #ccc;">{row.get("SPECIFICATION OF COMMODITIES","N/A")}</td><td style="padding:10px; border:1px solid #ccc; text-align:center;">{row.get("CTNS NOS","N/A")}</td><td style="padding:10px; border:1px solid #ccc; text-align:center;">{row.get("TOTAL CTNS",0)}</td><td style="padding:10px; border:1px solid #ccc; text-align:right;">{int(row.get("QUANTITY",0)):,}</td></tr>'
        img_tag = f'<img src="{logo_path}" height="50">' if logo_path else ''
        rendered_html = f'<html><body><table width="100%"><tr><td>{img_tag}</td><td align="right"><h2>{title}</h2></td></tr></table><p><b>Exporter:</b> {supplier}<br><b>Consignee:</b> {client}<br>{c_addr}</p><table border="1" width="100%" cellspacing="0" cellpadding="5"><thead><tr bgcolor="#f7f7f7"><th>Description</th><th>Carton Nos</th><th>Total Ctns</th><th>Qty</th></tr></thead><tbody>{table_rows}</tbody></table><br><br></body></html>'
    
    elif is_duties:
        duty_data = duty_data or {}
        img_tag = f'<img src="{logo_path}" height="50">' if logo_path else ''
        rendered_html = f'<html><body><table width="100%"><tr><td>{img_tag}</td><td align="right"><h2>{title}</h2></td></tr></table><p><b>Invoice:</b> {inv_no}</p><p>Converted Base Value: ${duty_data.get("convert_to_ttd",0):,.2f} TTD</p><p>Customs Duty: ${duty_data.get("duty_owed",0):,.2f} TTD</p><p>VAT Owed: ${duty_data.get("vat_owed",0):,.2f} TTD</p><br><table border="1" width="100%" cellspacing="0" cellpadding="10"><tr><td bgcolor="#f9f9f9"><h3>Total Customs Bill Due: ${duty_data.get("grand_total_ttd",0):,.2f} TTD</h3></td></tr></table></body></html>'
    
    else:
        template_env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath="./templates"))
        chosen_template = s_profile.get("Template", "classic.html")
        if not os.path.exists(f"./templates/{chosen_template}"): chosen_template = "classic.html"
        try: template = template_env.get_template(chosen_template)
        except: template = template_env.from_string("<h1>{{title}}</h1><p><b>Exporter:</b> {{supplier_name}}<br><b>Consignee:</b> {{client_name}}</p><table border='1' width='100%' cellspacing='0' cellpadding='5'><thead><tr bgcolor='#f2f2f2'><th>Description</th><th>Qty</th><th>Total</th></tr></thead><tbody>{% for item in items %}<tr><td>{{item.Description}}</td><td>{{item.Qty}}</td><td>{{item.Total}}</td></tr>{% endfor %}</tbody></table>")

        items = []
        for idx, row in df.iterrows():
            desc = str(row["Description"])[:250]
            qty = f"{row.get('Qty', ''):,}" if pd.notna(row.get('Qty')) and row.get('Qty') != "" else ""
            price = f"{row.get('UnitPrice', ''):.2f}" if pd.notna(row.get('UnitPrice')) and row.get('UnitPrice') != "" else ""
            total = f"{row.get('Total Foreign (USD)', ''):.2f}" if pd.notna(row.get('Total Foreign (USD)')) and row.get('Total Foreign (USD)') != "" else ""
            items.append({"Description": desc, "Qty": qty, "UnitPrice": price, "Total": total})
            
        rendered_html = template.render({"title": title, "inv_no": inv_no, "date": date, "client_name": client, "client_address": c_addr, "supplier_name": supplier, "supplier_address": s_profile.get("Address", "Main Office Hub"), "bl": bl, "total_ctns": total_ctns, "payment_terms": payment_terms, "additional_notes": additional_notes, "is_caricom": is_caricom, "primary_hex": s_profile.get("PrimaryHex", "#0A2240"), "logo_path": logo_path, "subtotal": f"{total_val:,.2f}", "freight": (f"{freight:,.2f}" if freight else None), "grand_total": f"{(total_val + (freight or 0)):,.2f}", "items": items})
        rendered_html = re.sub(r'>\$\s*<', '><', rendered_html)

    return rendered_html

def create_print_button(html_content, button_label):
    escaped_html = html_content.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "")
    components_code = f"""
    <div style="display: flex; justify-content: center; margin-bottom: 8px;">
        <button onclick="triggerSystemPrint()" style="width: 100%; background-color: #2b2b2b; color: white; border: 1px solid #4a4a4a; padding: 10px 16px; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 14px;">🖨️ {button_label}</button>
    </div>
    <script>
        function triggerSystemPrint() {{ var printWindow = window.open('', '_blank', 'height=700,width=900'); printWindow.document.write('{escaped_html}'); printWindow.document.close(); printWindow.focus(); setTimeout(function() {{ printWindow.print(); printWindow.close(); }}, 400); }}
    </script>
    """
    components.html(components_code, height=55)

def display_html_preview(raw_html):
    preview_html = f'<div style="background-color: white; padding: 40px; margin: 10px auto; border-radius: 5px; box-shadow: 0px 4px 10px rgba(0,0,0,0.1); max-width: 900px; color: #333333;">{raw_html}</div>'
    components.html(preview_html, height=750, scrolling=True)


# ==========================================
# 4. APP VIEWS & CONSOLE LAYOUT
# ==========================================

def render_master_log():
    st.subheader("🗄️ System Workspace Overview")
    df = load_log_data()

    if df.empty:
        st.info("No active logs recorded in this workspace yet.")
    else:
        for idx, row in df.iterrows():
            m61_id = str(row.get('M61 ID', 'N/A'))
            client_name = str(row.get('Client', ''))
            ship_status = str(row.get("Status", "Active"))
            total_cartons = str(row.get("TOTAL CTNS", ""))
            inv_no = str(row.get("Invoice#", ""))
            container_no = str(row.get("Container #", ""))
            
            raw_eta = row.get("ETA")
            timestamp = pd.to_datetime(raw_eta, errors='coerce')
            current_date = timestamp.date() if not pd.isna(timestamp) else datetime.now().date()
            status_label, _ = get_eta_status(current_date, ship_status)
            
            naldo_val = str(row.get("NALDO", "No")).strip().upper()
            naldo_display = f"🔴 NALDO: YES" if naldo_val == "YES" else f"⚪ NALDO: NO"
            
            header_text = f"⚙️ {m61_id} | CTNS: {total_cartons if total_cartons else '0'} | {status_label} | Client: {client_name if client_name else 'Unassigned'} | Inv: {inv_no if inv_no else 'Pending'} | Cont: {container_no if container_no else 'Pending'} | {naldo_display}"

            with st.expander(header_text):
                col1, col2, col3, col4, col5, col6 = st.columns(6)
                with col1: new_cont = st.text_input("Container #", value=container_no, key=f"cont_{idx}")
                with col2: new_orig = st.selectbox("Country of Origin", ALL_COUNTRIES, index=ALL_COUNTRIES.index(row.get("Origin", "")) if row.get("Origin", "") in ALL_COUNTRIES else 0, key=f"orig_{idx}")
                with col3: new_eta = st.date_input("ETA", value=current_date, key=f"eta_{idx}")
                with col4: new_lodg = st.radio("Doc Status", ["Yes", "No"], index=0 if row.get("Doc Status") == "Yes" else 1, horizontal=True, key=f"lodged_{idx}")
                with col5: new_stat = st.selectbox("Status", ["Active", "Delivered"], index=0 if ship_status != "Delivered" else 1, key=f"stat_{idx}")
                with col6: new_naldo = st.radio("NALDO Override", ["Yes", "No"], index=0 if naldo_val == "YES" else 1, horizontal=True, key=f"naldo_{idx}")
                
                st.write("---")
                st.markdown("#### Document Control Matrix")
                
                # Dynamic grid layout for the 10 document slots (5 columns x 2 rows)
                grid = st.columns(5)
                upload_cache = {}
                
                for i, slot in enumerate(ALL_DOCS):
                    with grid[i % 5]:
                        st.markdown(f"**{slot}**")
                        file_link = str(row.get(slot, "")).strip()
                        
                        if file_link.startswith("http"):
                            clean_link = file_link
                            match = re.search(r'/d/([a-zA-Z0-9_-]+)', file_link)
                            if match:
                                file_id = match.group(1)
                                clean_link = f"https://drive.google.com/uc?export=download&id={file_id}"
                            st.link_button("📄 View Document", url=clean_link, key=f"view_{idx}_{i}", use_container_width=True)
                        else:
                            st.button("Pending Upload", disabled=True, key=f"pend_{idx}_{i}", use_container_width=True)
                        
                        if slot in EXTERNAL_DOCS:
                            uploaded_file = st.file_uploader(f"Replace {slot}", key=f"up_{idx}_{i}", label_visibility="collapsed")
                            if uploaded_file:
                                upload_cache[slot] = uploaded_file
                
                if st.button("💾 Save Shipment Updates", key=f"save_{idx}", type="primary"):
                    with st.spinner("Processing structural workspace records..."):
                        df_update = load_log_data()
                        row_index = df_update.index[df_update['M61 ID'].astype(str) == m61_id].tolist()[0]
                        df_update.at[row_index, "Container #"] = new_cont
                        df_update.at[row_index, "Origin"] = new_orig
                        df_update.at[row_index, "ETA"] = str(new_eta)
                        df_update.at[row_index, "Doc Status"] = new_lodg
                        df_update.at[row_index, "Status"] = new_stat
                        df_update.at[row_index, "NALDO"] = new_naldo
                        
                        for slot_name, up_file in upload_cache.items():
                            doc_filename = f"{m61_id}_{slot_name.replace(' ', '_')}.pdf"
                            new_link = upload_physical_file_to_drive(up_file, doc_filename, client_name, m61_id)
                            if new_link: df_update.at[row_index, slot_name] = new_link
                            
                        if save_log_data(df_update):
                            st.success("✅ Log tracking entries synchronized!")
                            st.rerun()

def render_admin_tracker():
    st.subheader("⚙️ Active File Processor Matrix")
    
    client_file = "clients.csv"
    supplier_file = "suppliers.csv"
    client_options = ["Select a Client..."] + sorted(pd.read_csv(client_file)["Name"].dropna().tolist()) if os.path.exists(client_file) and os.path.getsize(client_file) > 0 else ["Select a Client..."]
    supplier_options = ["Select a Supplier..."] + sorted(pd.read_csv(supplier_file)["Name"].dropna().tolist()) if os.path.exists(supplier_file) and os.path.getsize(supplier_file) > 0 else ["Select a Supplier..."]

    st.write("---")
    col1, col2 = st.columns([1, 1.3])

    with col1:
        st.subheader("Data Intake Configuration")
        client_name = st.selectbox("Client Workspace", client_options)
        supplier_name = st.selectbox("Supplier Profile", supplier_options)
        
        supplier_profile = get_entity_profile("suppliers.csv", supplier_name)
        client_profile = get_entity_profile("clients.csv", client_name)
        
        uploaded_file = st.file_uploader("Drop Raw Vendor Spreadsheet (CSV or Excel)", type=["csv", "xlsx"])
        saved_desc, saved_qty, saved_price = get_supplier_mapping(supplier_name)
        map_description, map_qty, map_price = "-- Select --", "-- Select --", "-- Select --"
        
        if uploaded_file is not None:
            df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            all_columns = list(df_raw.dropna(how='all').columns)
            cm1, cm2, cm3 = st.columns(3)
            with cm1: map_description = st.selectbox("Description Column", ["-- Select --"] + all_columns, index=all_columns.index(saved_desc)+1 if saved_desc in all_columns else 0)
            with cm2: map_qty = st.selectbox("Quantity Column", ["-- Select --"] + all_columns, index=all_columns.index(saved_qty)+1 if saved_qty in all_columns else 0)
            with cm3: map_price = st.selectbox("Unit Price Column", ["-- Select --"] + all_columns, index=all_columns.index(saved_price)+1 if saved_price in all_columns else 0)
            if map_description != "-- Select --" and (map_description != saved_desc or map_qty != saved_qty or map_price != saved_price):
                if st.button("Save Column Translation Matrix"):
                    save_supplier_mapping(supplier_name, map_description, map_qty, map_price)
                    st.success("Matrix Mapped!")

        st.write("---")
        st.markdown("#### Dynamic Logistics Allocation Fields")
        cx1, cx2 = st.columns(2)
        with cx1:
            invoice_num = st.text_input("Invoice Number", value="")
            invoice_date = st.text_input("Invoice Date", value=datetime.now().strftime("%d-%m-%Y"))
            bl_number = st.text_input("Bill of Lading (BL#)")
            payment_terms = st.selectbox("Terms", ["NET 90 Days", "NET 45 Days", "NET 30 Days"])
            special_indicator = st.selectbox("Shipment Type", ["Standard", "Express", "Maritime Direct"])
        with cx2:
            freight_cost = st.number_input("Ocean Freight (USD)", value=0.00)
            container_total_ctns = st.number_input("Total Cartons", value=0)
            exchange_rate = st.number_input("Exchange Rate", value=6.77967, format="%.5f")
            signatory_position = st.text_input("Signatory Position", value="Authorized Director")
            
        additional_notes = st.text_area("Cargo Notes", "Assorted cargo bulk manifest")

        st.markdown("#### Tariff Parameters")
        tx1, tx2 = st.columns(2)
        with tx1: duty_percentage = st.number_input("Duty Rate (%)", value=20.0)
        with tx1: vat_percentage = st.number_input("VAT Rate (%)", value=12.5)
        with tx2: ces_fee = st.number_input("CES Fee (TTD)", value=1050.00)
        with tx2: uf_fee = st.number_input("UF Fee (TTD)", value=80.00)

    with col2:
        st.subheader("Document Sync Operations")
        if uploaded_file and map_description != "-- Select --" and map_qty != "-- Select --" and map_price != "-- Select --":
            df_clean = df_raw[[map_description, map_qty, map_price]].dropna().copy()
            df_clean.columns = ["Description", "Qty", "UnitPrice"]
            df_clean["Qty"] = pd.to_numeric(df_clean["Qty"], errors='coerce').fillna(0).astype(int)
            df_clean["UnitPrice"] = pd.to_numeric(df_clean["UnitPrice"], errors='coerce').fillna(0.0)
            subtotal_foreign = (df_clean["Qty"] * df_clean["UnitPrice"]).sum()
            df_clean["Total Foreign (USD)"] = df_clean["Qty"] * df_clean["UnitPrice"]
            
            convert_to_ttd = (subtotal_foreign + freight_cost) * exchange_rate
            duty_owed = convert_to_ttd * (duty_percentage / 100.0)
            vat_owed = (convert_to_ttd + duty_owed) * (vat_percentage / 100.0)
            grand_total_ttd = duty_owed + vat_owed + ces_fee + uf_fee
            duty_dict = {'exchange_rate': exchange_rate, 'convert_to_ttd': convert_to_ttd, 'duty_owed': duty_owed, 'vat_owed': vat_owed, 'fixed_fees': ces_fee + uf_fee, 'grand_total_ttd': grand_total_ttd}
            
            file_state_hash = f"{uploaded_file.name}_{supplier_name}_{client_name}"
            if "active_file_hash" not in st.session_state or st.session_state["active_file_hash"] != file_state_hash:
                st.session_state["active_file_hash"] = file_state_hash
                base_pck_df = df_raw[[map_description, map_qty]].dropna().copy()
                base_pck_df.columns = ["SPECIFICATION OF COMMODITIES", "QUANTITY"]
                base_pck_df["TOTAL CTNS"] = 0
                st.session_state["pck_working_df"] = base_pck_df

            t_inv, t_car, t_pck, t_dut = st.tabs(["📄 Invoice", "🌐 CARICOM", "📋 Packing Manifest", "🇹🇹 Customs Audit"])
            
            with t_inv:
                if st.button("⚙️ Preview Invoice"): 
                    st.session_state["h_inv"] = generate_html_document("COMMERCIAL INVOICE", invoice_num, invoice_date, client_name, client_profile.get("Address",""), supplier_name, supplier_profile, bl_number, container_total_ctns, df_clean, subtotal_foreign, freight_cost, additional_notes, payment_terms, signatory_position)
                if "h_inv" in st.session_state: 
                    create_print_button(st.session_state["h_inv"], "Export / Open System Print Wizard")
                    display_html_preview(st.session_state["h_inv"])
                    
            with t_car:
                if st.button("⚙️ Preview CARICOM"): 
                    df_caricom = pd.DataFrame([{"Description": f"{additional_notes} as per invoice # {invoice_num}, dated: {invoice_date}", "Qty": "", "UnitPrice": "", "Total Foreign (USD)": ""}])
                    st.session_state["h_car"] = generate_html_document("CARICOM INVOICE", invoice_num, invoice_date, client_name, client_profile.get("Address",""), supplier_name, supplier_profile, bl_number, container_total_ctns, df_caricom, subtotal_foreign, freight_cost, additional_notes, payment_terms, signatory_position, is_caricom=True)
                if "h_car" in st.session_state: 
                    create_print_button(st.session_state["h_car"], "Export / Open System Print Wizard")
                    display_html_preview(st.session_state["h_car"])
                    
            with t_pck:
                st.markdown("##### Interactive Packing Line Sheet")
                with st.form("packing_matrix_form"):
                    edited_pck_df = st.data_editor(st.session_state["pck_working_df"], disabled=["SPECIFICATION OF COMMODITIES", "QUANTITY"], key="pck_table_editor", width="stretch")
                    submit_packing = st.form_submit_button("⚙️ Generate & Preview Packing List", type="primary")

                if submit_packing:
                    st.session_state["pck_working_df"] = edited_pck_df
                    calculated_rows = []
                    box_cursor = 1
                    for idx, row in edited_pck_df.iterrows():
                        assigned_ctns = int(row.get("TOTAL CTNS", 0))
                        if assigned_ctns > 0:
                            end_box = box_cursor + assigned_ctns - 1
                            range_str = f"{box_cursor}-{end_box}" if box_cursor != end_box else f"{box_cursor}"
                            box_cursor = end_box + 1
                        else: range_str = "0"
                        calculated_rows.append({"SPECIFICATION OF COMMODITIES": row["SPECIFICATION OF COMMODITIES"], "QUANTITY": row["QUANTITY"], "TOTAL CTNS": assigned_ctns, "CTNS NOS": range_str})
                    
                    df_p_compiled = pd.DataFrame(calculated_rows)
                    st.session_state["df_p_compiled"] = df_p_compiled
                    st.session_state["h_pck"] = generate_html_document("PACKING LIST MANIFEST", invoice_num, invoice_date, client_name, client_profile.get("Address",""), supplier_name, supplier_profile, bl_number, container_total_ctns, df_p_compiled, subtotal_foreign, freight_cost, additional_notes, payment_terms, signatory_position, is_packing=True)
                
                if "h_pck" in st.session_state: 
                    create_print_button(st.session_state["h_pck"], "Export / Open System Print Wizard")
                    display_html_preview(st.session_state["h_pck"])
                    
            with t_dut:
                if st.button("⚙️ Preview Customs Summary"): 
                    st.session_state["h_dut"] = generate_html_document("OFFICIAL DUTIES ASSESSMENT", invoice_num, invoice_date, client_name, client_profile.get("Address",""), supplier_name, supplier_profile, bl_number, container_total_ctns, st.session_state.get("df_p_compiled", df_clean), subtotal_foreign, freight_cost, additional_notes, payment_terms, signatory_position, is_duties=True, duty_data=duty_dict)
                if "h_dut" in st.session_state: 
                    create_print_button(st.session_state["h_dut"], "Export / Open System Print Wizard")
                    display_html_preview(st.session_state["h_dut"])

        st.write("---")
        if st.button("💾 Compile & Overwrite Selected Workspace Docs", type="primary", width="stretch"):
            if "target_m61_id" in st.session_state and st.session_state["target_m61_id"] != "-- Choose Active Shell --":
                target_id = st.session_state["target_m61_id"]
                with st.spinner("Compiling structural system documents to Drive Vault..."):
                    try:
                        auto_inv_html = generate_html_document("COMMERCIAL INVOICE", invoice_num, invoice_date, client_name, client_profile.get("Address",""), supplier_name, supplier_profile, bl_number, container_total_ctns, df_clean, subtotal_foreign, freight_cost, additional_notes, payment_terms, signatory_position)
                        df_caricom_auto = pd.DataFrame([{"Description": f"{additional_notes} as per invoice # {invoice_num}, dated: {invoice_date}", "Qty": "", "UnitPrice": "", "Total Foreign (USD)": ""}])
                        auto_car_html = generate_html_document("CARICOM INVOICE", invoice_num, invoice_date, client_name, client_profile.get("Address",""), supplier_name, supplier_profile, bl_number, container_total_ctns, df_caricom_auto, subtotal_foreign, freight_cost, additional_notes, payment_terms, signatory_position, is_caricom=True)
                        auto_pck_html = generate_html_document("PACKING LIST MANIFEST", invoice_num, invoice_date, client_name, client_profile.get("Address",""), supplier_name, supplier_profile, bl_number, container_total_ctns, st.session_state.get("df_p_compiled", df_clean), subtotal_foreign, freight_cost, additional_notes, payment_terms, signatory_position, is_packing=True)
                        auto_dut_html = generate_html_document("OFFICIAL DUTIES ASSESSMENT", invoice_num, invoice_date, client_name, client_profile.get("Address",""), supplier_name, supplier_profile, bl_number, container_total_ctns, st.session_state.get("df_p_compiled", df_clean), subtotal_foreign, freight_cost, additional_notes, payment_terms, signatory_position, is_duties=True, duty_data=duty_dict)

                        inv_link = upload_system_pdf_to_drive(auto_inv_html, f"{target_id}_Commercial_Invoice.pdf", client_name, target_id)
                        car_link = upload_system_pdf_to_drive(auto_car_html, f"{target_id}_CARICOM_Invoice.pdf", client_name, target_id)
                        pck_link = upload_system_pdf_to_drive(auto_pck_html, f"{target_id}_Sequential_Packing_List.pdf", client_name, target_id)
                        dut_link = upload_system_pdf_to_drive(auto_dut_html, f"{target_id}_Official_Duties.pdf", client_name, target_id)

                        df_all = load_log_data()
                        row_index = df_all.index[df_all['M61 ID'].astype(str) == target_id].tolist()[0]
                        
                        df_all.at[row_index, "TOTAL CTNS"] = str(container_total_ctns)
                        df_all.at[row_index, "Invoice#"] = str(invoice_num)
                        df_all.at[row_index, "BL#"] = str(bl_number)
                        df_all.at[row_index, "Client"] = str(client_name)
                        df_all.at[row_index, "Com Invoice"] = inv_link
                        df_all.at[row_index, "Caricom invoice"] = car_link
                        df_all.at[row_index, "Packing List"] = pck_link
                        df_all.at[row_index, "Duties Calculation"] = dut_link
                        df_all.at[row_index, "Notes"] = str(additional_notes)
                        
                        save_log_data(df_all)
                        st.success(f"🎉 System Documents mapped and compiled onto Workspace Shell {target_id}!")
                        st.balloons()
                    except Exception as sheet_err:
                        st.error(f"Integration Error: {sheet_err}")
            else:
                st.warning("⚠️ Workspace Target Validation Error: Please select an active shell mapping workspace dropdown anchor first.")


# ==========================================
# 5. COMMAND PIPELINE INTERFACE
# ==========================================

st.title("🚢 Meridian Command Console (Unified Control Center)")

# --- INTEGRATED ASYNCHRONOUS "SEED" SYSTEM TRIGGER CONTROLLER ---
st.markdown("### ⚡ Quick Intake Pipeline")
col_trigger, col_selector = st.columns([1, 1.5])

with col_trigger:
    if st.button("➕ Create Empty Shipment Shell", type="primary", use_container_width=True):
        with st.spinner("Initializing serial master workspace shell..."):
            df_current = load_log_data()
            
            # Smart serial index look-up logic
            next_num = 1001
            if not df_current.empty and "M61 ID" in df_current.columns:
                valid_ids = df_current["M61 ID"].astype(str).tolist()
                nums = [int(re.findall(r'\d+', x)[0]) for x in valid_ids if re.findall(r'\d+', x)]
                if nums:
                    next_num = max(nums) + 1
            
            new_id_code = f"M61-{next_num}"
            
            # Append complete baseline 21-column series array row dictionary definition
            blank_row = {col: "" for col in ALL_LOG_COLUMNS}
            blank_row["M61 ID"] = new_id_code
            blank_row["Status"] = "Active"
            blank_row["NALDO"] = "No"
            blank_row["Doc Status"] = "No"
            
            for doc_slot in ALL_DOCS:
                blank_row[doc_slot] = "Pending Upload"
                
            df_new = pd.concat([df_current, pd.DataFrame([blank_row])], ignore_index=True)
            if save_log_data(df_new):
                st.session_state["target_m61_id"] = new_id_code
                st.toast(f"Shell {new_id_code} successfully generated!", icon="✅")

with col_selector:
    df_dropdown_feed = load_log_data()
    dropdown_options = ["-- Choose Active Shell --"]
    
    if not df_dropdown_feed.empty:
        for _, r in df_dropdown_feed.iterrows():
            s_id = str(r.get("M61 ID", ""))
            s_ctns = str(r.get("TOTAL CTNS", "")).strip()
            s_inv = str(r.get("Invoice#", "")).strip()
            s_cont = str(r.get("Container #", "")).strip()
            s_client = str(r.get("Client", "")).strip()
            
            # Formatting the Smart CTNS Front-Loaded Label string
            label = f"{s_id}"
            if s_ctns: label += f" | CTNS: {s_ctns}"
            if s_client: label += f" | Client: {s_client}"
            if s_inv: label += f" | Inv: {s_inv}"
            if s_cont: label += f" | Cont: {s_cont}"
            
            if not s_ctns and not s_inv and not s_cont: 
                label += " (New Empty Shell)"
            
            dropdown_options.append(label)

    # Determine dynamic state index tracking focus selector anchor point
    current_target = st.session_state.get("target_m61_id", "-- Choose Active Shell --")
    matching_indices = [i for i, opt in enumerate(dropdown_options) if opt.startswith(str(current_target))]
    default_sel_idx = matching_indices[0] if matching_indices else 0

    selected_option = st.selectbox(
        "Select Active Shipment Workspace Anchor", 
        dropdown_options, 
        index=default_sel_idx, 
        label_visibility="collapsed"
    )
    
    if selected_option != "-- Choose Active Shell --":
        st.session_state["target_m61_id"] = selected_option.split(" ")[0]
    else:
        st.session_state["target_m61_id"] = "-- Choose Active Shell --"

st.write("---")

# --- NAVIGATION TABS FLOW ---
nav_selection = st.radio("Workspace Directory Modules", ["📋 Master Dashboard Workstation", "📦 File Template Processor Matrix"], horizontal=True, label_visibility="collapsed")

if nav_selection == "📋 Master Dashboard Workstation":
    render_master_log()
elif nav_selection == "📦 File Template Processor Matrix":
    if st.session_state.get("target_m61_id", "-- Choose Active Shell --") == "-- Choose Active Shell --":
        st.warning("⚠️ Access Restriction: Please choose an active tracking workspace shell anchor dropdown selection at the top header area to utilize file processor engines.")
    else:
        render_admin_tracker()
