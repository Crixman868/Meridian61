import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import base64
import gspread
import json
import io
import jinja2
import re
from fpdf import FPDF
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ==========================================
# ☁️ CONFIGURATION & SECURITY
# ==========================================
st.set_page_config(page_title="Master Tracker", page_icon="📦", layout="wide")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1ipB1DaIdX_BS_0iSWRHMwHcP-wEpfu2pZzFT3nJtlho/edit?gid=0#gid=0"
DRIVE_FOLDER_ID = "19pHVBp63Y2j8y5BKPujV78rbwBVeYuBk"
SCOPES = ['https://www.googleapis.com/auth/drive']

# --- GOOGLE AUTHENTICATION HELPERS ---
def get_gspread_client():
    # Uses the Robot Key for spreadsheets (no storage limit)
    creds_dict = json.loads(st.secrets["google_api"]["credentials"])
    return gspread.service_account_from_dict(creds_dict)

def get_drive_service():
    # FORCES the use of your Human Key (token.json) for 15GB of free storage
    try:
        token_dict = json.loads(st.secrets["google_drive"]["token"])
        creds = Credentials.from_authorized_user_info(token_dict, SCOPES)
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"🚨 Could not find the human 'token' in Streamlit Secrets. Error: {e}")
        st.stop()

# --- SECURITY GATEKEEPER VALIDATION ---
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
        try:
            drive_service.files().delete(fileId=f.get('id')).execute()
        except:
            pass 
    media = MediaIoBaseUpload(io.BytesIO(bytes(file_bytes)), mimetype='application/pdf', resumable=True)
    return drive_service.files().create(body={'name': filename, 'parents': [folder_id]}, media_body=media, fields='webViewLink').execute().get('webViewLink', '')

def load_log_data():
    try:
        gc = get_gspread_client()
        df = pd.DataFrame(gc.open_by_url(SHEET_URL).sheet1.get_all_records())
        return df if not df.empty else pd.DataFrame()
    except: return pd.DataFrame()

def save_log_data(df):
    gc = get_gspread_client()
    ws = gc.open_by_url(SHEET_URL).sheet1
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

# --- DOCUMENT FACTORY ENGINE (Powered by fpdf2) ---
def generate_html_pdf(title, inv_no, date, client, c_addr, supplier, s_profile, bl, total_ctns, df, total_val, freight=None, additional_notes="", payment_terms="", signatory_position="", is_packing=False, is_caricom=False, is_duties=False, duty_data=None):
    logo_path = get_img_b64(f"logos/{s_profile.get('Name', '')}_logo.png")
    sig_path = get_img_b64(f"signatures/{s_profile.get('Name', '')}_sig.png")

    if is_packing:
        table_rows = ""
        for idx, row in df.iterrows():
            table_rows += f'<tr><td style="padding:10px; border:1px solid #ccc;">{row.get("SPECIFICATION OF COMMODITIES","N/A")}</td><td style="padding:10px; border:1px solid #ccc; text-align:center;">{row.get("CTNS NOS","N/A")}</td><td style="padding:10px; border:1px solid #ccc; text-align:center;">{row.get("TOTAL CTNS",0)}</td><td style="padding:10px; border:1px solid #ccc; text-align:right;">{int(row.get("QUANTITY",0)):,}</td></tr>'
        
        img_tag = f'<img src="{logo_path}" height="50">' if logo_path else ''
        sig_tag = f'<img src="{sig_path}" height="80">' if sig_path else ''
        
        rendered_html = f'<html><body><table width="100%"><tr><td>{img_tag}</td><td align="right"><h2>{title}</h2></td></tr></table><p><b>Exporter:</b> {supplier}<br><b>Consignee:</b> {client}<br>{c_addr}</p><table border="1" width="100%" cellspacing="0" cellpadding="5"><thead><tr bgcolor="#f7f7f7"><th>Description</th><th>Carton Nos</th><th>Total Ctns</th><th>Qty</th></tr></thead><tbody>{table_rows}</tbody></table><br><br><div align="right">{sig_tag}<br><b>{signatory_position}</b></div></body></html>'

    elif is_duties:
        duty_data = duty_data or {}
        img_tag = f'<img src="{logo_path}" height="50">' if logo_path else ''
        
        rendered_html = f'<html><body><table width="100%"><tr><td>{img_tag}</td><td align="right"><h2>{title}</h2></td></tr></table><p><b>Invoice:</b> {inv_no}</p><p>Converted Base Value: ${duty_data.get("convert_to_ttd",0):,.2f} TTD</p><p>Customs Duty: ${duty_data.get("duty_owed",0):,.2f} TTD</p><p>VAT Owed: ${duty_data.get("vat_owed",0):,.2f} TTD</p><br><table border="1" width="100%" cellspacing="0" cellpadding="10"><tr><td bgcolor="#f9f9f9"><h3>Total Customs Bill Due: ${duty_data.get("grand_total_ttd",0):,.2f} TTD</h3></td></tr></table></body></html>'
        
    else:
        template_env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath="./templates"))
        chosen_template = s_profile.get("Template", "classic.html")
        if not os.path.exists(f"./templates/{chosen_template}"):
            chosen_template = "classic.html"
        
        try:
            template = template_env.get_template(chosen_template)
        except:
            template = template_env.from_string("<h1>{{title}}</h1><p><b>Exporter:</b> {{supplier_name}}<br><b>Consignee:</b> {{client_name}}</p><table border='1' width='100%' cellspacing='0' cellpadding='5'><thead><tr bgcolor='#f2f2f2'><th>Description</th><th>Qty</th><th>Total</th></tr></thead><tbody>{% for item in items %}<tr><td>{{item.Description}}</td><td>{{item.Qty}}</td><td>{{item.Total}}</td></tr>{% endfor %}</tbody></table>")

        items = []
        for idx, row in df.iterrows():
            desc = str(row["Description"])[:250]
            qty_val = row.get("Qty", "")
            price_val = row.get("UnitPrice", "")
            total_val_row = row.get("Total Foreign (USD)", "")
            
            qty = f"{qty_val:,}" if pd.notna(qty_val) and qty_val != "" else ""
            price = f"{price_val:.2f}" if pd.notna(price_val) and price_val != "" else ""
            total = f"{total_val_row:.2f}" if pd.notna(total_val_row) and total_val_row != "" else ""
            items.append({"Description": desc, "Qty": qty, "UnitPrice": price, "Total": total})
            
        rendered_html = template.render({"title": title, "inv_no": inv_no, "date": date, "client_name": client, "client_address": c_addr, "supplier_name": supplier, "supplier_address": s_profile.get("Address", "Main Office Hub"), "bl": bl, "total_ctns": total_ctns, "payment_terms": payment_terms, "additional_notes": additional_notes, "is_caricom": is_caricom, "primary_hex": s_profile.get("PrimaryHex", "#0A2240"), "logo_path": logo_path, "sig_path": sig_path, "signatory_position": signatory_position, "subtotal": f"{total_val:,.2f}", "freight": (f"{freight:,.2f}" if freight else None), "grand_total": f"{(total_val + (freight or 0)):,.2f}", "items": items})
        rendered_html = re.sub(r'>\$\s*<', '><', rendered_html)

    try:
        pdf = FPDF()
        pdf.add_page()
        cleaned_html = re.sub(r'<style\b[^>]*>[\s\S]*?</style>', '', rendered_html, flags=re.IGNORECASE)
        cleaned_html = cleaned_html.replace('src=""', '')
        pdf.write_html(cleaned_html)
        pdf_bytes = bytes(pdf.output())
    except Exception as e:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", size=12)
        pdf.multi_cell(0, 10, f"DOCUMENT: {title}\nINVOICE: {inv_no}\n\nNotice: Detailed HTML rendering failed. Please use the 'Export / Print Wizard' button in the app for the fully formatted document.\n\nSystem Error: {e}")
        pdf_bytes = bytes(pdf.output())

    return pdf_bytes, rendered_html


# --- MAIN UI ---
client_file = "clients.csv"
supplier_file = "suppliers.csv"

client_options = ["Select a Client..."] + sorted(pd.read_csv(client_file)["Name"].dropna().tolist()) if os.path.exists(client_file) and os.path.getsize(client_file) > 0 else ["Select a Client..."]
supplier_options = ["Select a Supplier..."] + sorted(pd.read_csv(supplier_file)["Name"].dropna().tolist()) if os.path.exists(supplier_file) and os.path.getsize(supplier_file) > 0 else ["Select a Supplier..."]

st.write("---")
col1, col2 = st.columns([1, 1.3])

with col1:
    st.subheader("Data Intake & Matrix Mapping")
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
    st.markdown("#### Logistics Manifest Fields")
    cx1, cx2 = st.columns(2)
    with cx1:
        invoice_num = st.text_input("Invoice Number", value="269698487")
        invoice_date = st.text_input("Invoice Date", value="05-05-2026")
        bl_number = st.text_input("Bill of Lading (BL#)")
        payment_terms = st.selectbox("Terms", ["NET 90 Days", "NET 45 Days", "NET 30 Days"])
        special_indicator = st.selectbox("Shipment Type", ["Standard", "Express", "Maritime Direct"])
    with cx2:
        freight_cost = st.number_input("Ocean Freight (USD)", value=2500.00)
        container_total_ctns = st.number_input("Total Cartons", value=980)
        exchange_rate = st.number_input("Exchange Rate", value=6.77967, format="%.5f")
        signatory_position = st.text_input("Signatory Position", value="Authorized Director")
        
    additional_notes = st.text_area("Cargo Notes", "Assorted cargo bulk manifest")

    st.markdown("#### Tariff Tax Parameters")
    tx1, tx2 = st.columns(2)
    with tx1: 
        duty_percentage = st.number_input("Duty Rate (%)", value=20.0)
        vat_percentage = st.number_input("VAT Rate (%)", value=12.5)
    with tx2: 
        ces_fee = st.number_input("CES Fee (TTD)", value=1050.00)
        uf_fee = st.number_input("UF Fee (TTD)", value=80.00)

with col2:
    st.subheader("Automated Document Delivery Streams")
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

        if "pck_working_df" in st.session_state and "TOTAL CTNS" not in st.session_state["pck_working_df"].columns:
            st.session_state["pck_working_df"]["TOTAL CTNS"] = 0

        t_inv, t_car, t_pck, t_dut = st.tabs(["📄 Invoice", "🌐 CARICOM", "📋 Packing Manifest", "🇹🇹 Customs Audit"])
        
        with t_inv:
            if st.button("⚙️ Compile Invoice"): 
                st.session_state["p_inv"], st.session_state["h_inv"] = generate_html_pdf("COMMERCIAL INVOICE", invoice_num, invoice_date, client_name, client_profile.get("Address",""), supplier_name, supplier_profile, bl_number, container_total_ctns, df_clean, subtotal_foreign, freight_cost, additional_notes, payment_terms, signatory_position)
            if "p_inv" in st.session_state and "h_inv" in st.session_state: 
                create_print_button(st.session_state["h_inv"], "Export / Open System Print Wizard")
                display_pdf(st.session_state["p_inv"], st.session_state["h_inv"])
                
        with t_car:
            if st.button("⚙️ Compile CARICOM"): 
                df_caricom = pd.DataFrame([{
                    "Description": f"{additional_notes} as per invoice # {invoice_num}, dated: {invoice_date}",
                    "Qty": "", "UnitPrice": "", "Total Foreign (USD)": ""
                }])
                
                st.session_state["p_car"], st.session_state["h_car"] = generate_html_pdf("CARICOM INVOICE", invoice_num, invoice_date, client_name, client_profile.get("Address",""), supplier_name, supplier_profile, bl_number, container_total_ctns, df_caricom, subtotal_foreign, freight_cost, additional_notes, payment_terms, signatory_position, is_caricom=True)
            if "p_car" in st.session_state and "h_car" in st.session_state: 
                create_print_button(st.session_state["h_car"], "Export / Open System Print Wizard")
                display_pdf(st.session_state["p_car"], st.session_state["h_car"])
                
        with t_pck:
            st.markdown("##### Interactive Packing Line Sheet")
            edited_pck_df = st.data_editor(
                st.session_state["pck_working_df"],
                disabled=["SPECIFICATION OF COMMODITIES", "QUANTITY"],
                key="pck_table_editor",
                use_container_width=True
            )
            st.session_state["pck_working_df"] = edited_pck_df

            calculated_rows = []
            box_cursor = 1
            for idx, row in edited_pck_df.iterrows():
                assigned_ctns = int(row.get("TOTAL CTNS", 0))
                if assigned_ctns > 0:
                    end_box = box_cursor + assigned_ctns - 1
                    range_str = f"{box_cursor}-{end_box}" if box_cursor != end_box else f"{box_cursor}"
                    box_cursor = end_box + 1
                else:
                    range_str = "0"
                
                calculated_rows.append({
                    "SPECIFICATION OF COMMODITIES": row["SPECIFICATION OF COMMODITIES"],
                    "QUANTITY": row["QUANTITY"],
                    "TOTAL CTNS": assigned_ctns,
                    "CTNS NOS": range_str
                })
            df_p_compiled = pd.DataFrame(calculated_rows)
            st.session_state["df_p_compiled"] = df_p_compiled

            if st.button("⚙️ Compile Packing List"): 
                st.session_state["p_pck"], st.session_state["h_pck"] = generate_html_pdf("PACKING LIST MANIFEST", invoice_num, invoice_date, client_name, client_profile.get("Address",""), supplier_name, supplier_profile, bl_number, container_total_ctns, df_p_compiled, subtotal_foreign, freight_cost, additional_notes, payment_terms, signatory_position, is_packing=True)
            if "p_pck" in st.session_state and "h_pck" in st.session_state: 
                create_print_button(st.session_state["h_pck"], "Export / Open System Print Wizard")
                display_pdf(st.session_state["p_pck"], st.session_state["h_pck"])
                
        with t_dut:
            if st.button("⚙️ Compile Customs Summary"): 
                st.session_state["p_dut"], st.session_state["h_dut"] = generate_html_pdf("OFFICIAL DUTIES ASSESSMENT", invoice_num, invoice_date, client_name, client_profile.get("Address",""), supplier_name, supplier_profile, bl_number, container_total_ctns, st.session_state.get("df_p_compiled", df_clean), subtotal_foreign, freight_cost, additional_notes, payment_terms, signatory_position, is_duties=True, duty_data=duty_dict)
            if "p_dut" in st.session_state and "h_dut" in st.session_state: 
                create_print_button(st.session_state["h_dut"], "Export / Open System Print Wizard")
                display_pdf(st.session_state["p_dut"], st.session_state["h_dut"])

        # --- MASTER CLOUD & LOCAL SYNCHRONIZATION SWITCH ---
        st.write("---")
        if st.button("💾 Commit Ingestion & Sync Cloud Vault Bundle", type="primary", use_container_width=True):
            if client_name != "Select a Client..." and supplier_name != "Select a Supplier...":
                with st.spinner("Executing synchronization across cloud vaults and local log files..."):
                    
                    df_caricom = pd.DataFrame([{
                        "Description": f"{additional_notes} as per invoice # {invoice_num}, dated: {invoice_date}",
                        "Qty": "", "UnitPrice": "", "Total Foreign (USD)": ""
                    }])
                    
                    p_i, _ = generate_html_pdf("COMMERCIAL INVOICE", invoice_num, invoice_date, client_name, client_profile.get("Address",""), supplier_name, supplier_profile, bl_number, container_total_ctns, df_clean, subtotal_foreign, freight_cost, additional_notes, payment_terms, signatory_position)
                    p_c, _ = generate_html_pdf("CARICOM INVOICE", invoice_num, invoice_date, client_name, client_profile.get("Address",""), supplier_name, supplier_profile, bl_number, container_total_ctns, df_caricom, subtotal_foreign, freight_cost, additional_notes, payment_terms, signatory_position, is_caricom=True)
                    p_p, _ = generate_html_pdf("PACKING LIST MANIFEST", invoice_num, invoice_date, client_name, client_profile.get("Address",""), supplier_name, supplier_profile, bl_number, container_total_ctns, st.session_state.get("df_p_compiled", df_clean), subtotal_foreign, freight_cost, additional_notes, payment_terms, signatory_position, is_packing=True)
                    p_d, _ = generate_html_pdf("OFFICIAL DUTIES ASSESSMENT", invoice_num, invoice_date, client_name, client_profile.get("Address",""), supplier_name, supplier_profile, bl_number, container_total_ctns, st.session_state.get("df_p_compiled", df_clean), subtotal_foreign, freight_cost, additional_notes, payment_terms, signatory_position, is_duties=True, duty_data=duty_dict)
                    
                    with open(f"uploaded_docs/[{invoice_num}] - Commercial_Invoice.pdf", "wb") as f: f.write(p_i)
                    with open(f"uploaded_docs/[{invoice_num}] - CARICOM_Invoice.pdf", "wb") as f: f.write(p_c)
                    with open(f"uploaded_docs/[{invoice_num}] - Packing_List.pdf", "wb") as f: f.write(p_p)
                    with open(f"uploaded_docs/[{invoice_num}] - Duties_Assessment.pdf", "wb") as f: f.write(p_d)
                    
                    # PROPER DRIVE UPLOAD (NO BYPASS)
                    try:
                        drive_service = get_drive_service()
                        f_id = get_or_create_client_folder(drive_service, client_name, DRIVE_FOLDER_ID)
                        u_i = upload_file_to_drive(drive_service, p_i, f"[{invoice_num}] - Commercial_Invoice.pdf", f_id)
                        u_c = upload_file_to_drive(drive_service, p_c, f"[{invoice_num}] - CARICOM_Invoice.pdf", f_id)
                        u_p = upload_file_to_drive(drive_service, p_p, f"[{invoice_num}] - Packing_List.pdf", f_id)
                        u_d = upload_file_to_drive(drive_service, p_d, f"[{invoice_num}] - Duties_Assessment.pdf", f_id)
                    except Exception as drive_err:
                        st.error(f"🚨 Google Drive Upload Failed: {drive_err}")
                        st.stop()

                    try:
                        df_all = load_log_data()
                        new_row = {
                            "Invoice No": str(invoice_num), "Invoice Date": str(invoice_date), "BL#": str(bl_number), 
                            "Client Name": str(client_name), "Supplier": str(supplier_name), "Total C&F (USD)": float(subtotal_foreign+freight_cost), 
                            "Total CTNS": int(container_total_ctns), "Exchange Rate": float(exchange_rate), "Duty TTD": float(duty_dict['duty_owed']), 
                            "VAT TTD": float(duty_dict['vat_owed']), "Total Customs Bill TTD": float(grand_total_ttd), "Job State": "Open", 
                            "Shipment Type": str(special_indicator), "Commercial Invoice": str(u_i), "CARICOM Invoice": str(u_c), 
                            "Sequential Packing List": str(u_p), "Duties Assessment": str(u_d)
                        }
                        
                        df_all = pd.concat([df_all[df_all["Invoice No"].astype(str) != str(invoice_num)] if not df_all.empty else df_all, pd.DataFrame([new_row])], ignore_index=True)
                        save_log_data(df_all)
                        st.success("🎉 Enterprise Cloud Sync & Local Storage Verification Complete!")
                        st.balloons()
                    except Exception as sheet_err:
                        st.error(f"Database Integration Error: {sheet_err}")
            else:
                st.warning("⚠️ Workspace Validation Error: Ensure client and supplier selections are active before locking data arrays.")