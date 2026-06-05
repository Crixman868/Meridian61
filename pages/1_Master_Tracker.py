import streamlit as st

# --- STRICT ADMIN SECURITY BLOCK ---
if not st.session_state.get("logged_in", False):
    st.switch_page("0_Gatekeeper.py")

if not st.session_state.get("is_admin", False):
    st.error("🚨 RESTRICTED AREA: Administrator clearance required.")
    st.stop() 

import streamlit.components.v1 as components
import pandas as pd
import os
import base64
import gspread
import json
import jinja2
import re
import tempfile
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials as HumanCredentials
from google.oauth2.service_account import Credentials as BotCredentials
from googleapiclient.http import MediaFileUpload
from weasyprint import HTML

# ==========================================
# ☁️ CONFIGURATION & SECURITY
# ==========================================
st.set_page_config(page_title="Master Tracker", page_icon="📦", layout="wide")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1ipB1DaIdX_BS_0iSWRHMwHcP-wEpfu2pZzFT3nJtlho/edit?gid=0#gid=0"
ROOT_FOLDER_ID = "19pHVBp63Y2j8y5BKPujV78rbwBVeYuBk"

# --- THE HYBRID AUTHENTICATION SYSTEM ---
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

def upload_system_pdf_to_drive(html_content, file_name, client_name, invoice_no):
    if not html_content: return "Pending Upload"
    try:
        drive = get_drive_service()
        
        folders = drive.files().list(q=f"name='{client_name}' and '{ROOT_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false", fields="files(id, name)").execute().get('files', [])
        client_folder_id = folders[0]['id'] if folders else drive.files().create(body={"name": client_name, "parents": [ROOT_FOLDER_ID], "mimeType": "application/vnd.google-apps.folder"}).execute()['id']
        
        inv_folders = drive.files().list(q=f"name='{invoice_no}' and '{client_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false", fields="files(id, name)").execute().get('files', [])
        inv_folder_id = inv_folders[0]['id'] if inv_folders else drive.files().create(body={"name": invoice_no, "parents": [client_folder_id], "mimeType": "application/vnd.google-apps.folder"}).execute()['id']
        
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

def load_log_data():
    try: return pd.DataFrame(get_gspread_client().open_by_url(SHEET_URL).sheet1.get_all_records())
    except: return pd.DataFrame()

def save_log_data(df):
    ws = get_gspread_client().open_by_url(SHEET_URL).sheet1
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
            
        rendered_html = template.render({"title": title, "inv_no": inv_no, "date": date, "client_name": client, "client_address": c_addr, "supplier_name": supplier, "supplier_address": s_profile.get("Address", "Main Office Hub"), "bl": bl, "total_ctns": total_ctns, "payment_terms": payment_terms, "additional_notes": additional_notes, "is_caricom": is_caricom, "primary_hex": s_profile.get("PrimaryHex", "#0A2240"), "logo_path": logo_path, "sig_path": sig_path, "signatory_position": signatory_position, "subtotal": f"{total_val:,.2f}", "freight": (f"{freight:,.2f}" if freight else None), "grand_total": f"{(total_val + (freight or 0)):,.2f}", "items": items})
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

# --- MAIN UI ---
st.title("📦 Command Console: Master Tracker")
DOC_DIR = "uploaded_docs"
for folder in [DOC_DIR, "logos", "signatures", "watermarks", "templates"]:
    if not os.path.exists(folder): os.makedirs(folder)

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
    with tx1: duty_percentage = st.number_input("Duty Rate (%)", value=20.0)
    with tx1: vat_percentage = st.number_input("VAT Rate (%)", value=12.5)
    with tx2: ces_fee = st.number_input("CES Fee (TTD)", value=1050.00)
    with tx2: uf_fee = st.number_input("UF Fee (TTD)", value=80.00)

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
            
            # --- THE FORM BUFFER FIX ---
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

        # --- AUTO-COMPILE & SYNC ENGINE ---
        st.write("---")
        if st.button("💾 Commit Data & Send to Master Log", type="primary", width="stretch"):
            if client_name != "Select a Client..." and supplier_name != "Select a Supplier...":
                with st.spinner("Locking PDFs and Syncing to Master Log..."):
                    try:
                        auto_inv_html = generate_html_document("COMMERCIAL INVOICE", invoice_num, invoice_date, client_name, client_profile.get("Address",""), supplier_name, supplier_profile, bl_number, container_total_ctns, df_clean, subtotal_foreign, freight_cost, additional_notes, payment_terms, signatory_position)
                        df_caricom_auto = pd.DataFrame([{"Description": f"{additional_notes} as per invoice # {invoice_num}, dated: {invoice_date}", "Qty": "", "UnitPrice": "", "Total Foreign (USD)": ""}])
                        auto_car_html = generate_html_document("CARICOM INVOICE", invoice_num, invoice_date, client_name, client_profile.get("Address",""), supplier_name, supplier_profile, bl_number, container_total_ctns, df_caricom_auto, subtotal_foreign, freight_cost, additional_notes, payment_terms, signatory_position, is_caricom=True)
                        auto_pck_html = generate_html_document("PACKING LIST MANIFEST", invoice_num, invoice_date, client_name, client_profile.get("Address",""), supplier_name, supplier_profile, bl_number, container_total_ctns, st.session_state.get("df_p_compiled", df_clean), subtotal_foreign, freight_cost, additional_notes, payment_terms, signatory_position, is_packing=True)
                        auto_dut_html = generate_html_document("OFFICIAL DUTIES ASSESSMENT", invoice_num, invoice_date, client_name, client_profile.get("Address",""), supplier_name, supplier_profile, bl_number, container_total_ctns, st.session_state.get("df_p_compiled", df_clean), subtotal_foreign, freight_cost, additional_notes, payment_terms, signatory_position, is_duties=True, duty_data=duty_dict)

                        inv_link = upload_system_pdf_to_drive(auto_inv_html, f"{invoice_num}_Commercial_Invoice.pdf", client_name, invoice_num)
                        car_link = upload_system_pdf_to_drive(auto_car_html, f"{invoice_num}_CARICOM_Invoice.pdf", client_name, invoice_num)
                        pck_link = upload_system_pdf_to_drive(auto_pck_html, f"{invoice_num}_Sequential_Packing_List.pdf", client_name, invoice_num)
                        dut_link = upload_system_pdf_to_drive(auto_dut_html, f"{invoice_num}_Official_Duties.pdf", client_name, invoice_num)

                        df_all = load_log_data()
                        
                        new_row = {
                            "Invoice No": str(invoice_num), 
                            "Client Name": str(client_name),
                            "Container #": "", 
                            "Country of Origin": "", 
                            "ETA": str(invoice_date), 
                            "Lodged Status": "No",
                            "Shipment Status": "Active",
                            "NALDO": "No",
                            "Total Cartons": int(container_total_ctns), 
                            "Commercial Invoice": inv_link,
                            "CARICOM Invoice": car_link, 
                            "Sequential Packing List": pck_link, 
                            "Official Duties Assessment": dut_link,
                            "Bill of Lading Scan": "Pending Upload",
                            "Original Invoice": "Pending Upload",
                            "Original Packing List": "Pending Upload",
                            "Tracker Document": "Pending Upload",
                            "Other Documents": "Pending Upload",
                            "Miscellaneous Supporting Doc": "Pending Upload"
                        }
                        
                        if not df_all.empty and "Invoice No" in df_all.columns:
                            df_all = pd.concat([df_all[df_all["Invoice No"].astype(str) != str(invoice_num)], pd.DataFrame([new_row])], ignore_index=True)
                        else:
                            df_all = pd.DataFrame([new_row])
                            
                        save_log_data(df_all)
                        st.success("🎉 Shipment data locked and synced! Exact Replica PDFs are now available in the Vault.")
                        st.balloons()
                    except Exception as sheet_err:
                        st.error(f"Integration Error: {sheet_err}")
            else:
                st.warning("⚠️ Workspace Validation Error: Ensure client and supplier selections are active.")