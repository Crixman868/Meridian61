import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import base64
import uuid
import json
from datetime import datetime
import gspread
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

st.set_page_config(page_title="Master Log Control Tower", page_icon="🗃️", layout="wide")

if "selected_row_idx" not in st.session_state:
    st.session_state["selected_row_idx"] = None

if "logged_in" not in st.session_state or st.session_state["logged_in"] == False:
    st.error("🚨 Access Denied. Please log in through the Secure Gatekeeper.")
    st.stop()

st.title("🗃️ Control Tower: Master Customs Log (☁️ CLOUD)")
st.write("---")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1ipB1DaIdX_BS_0iSWRHMwHcP-wEpfu2pZzFT3nJtlho/edit?gid=0#gid=0"
DRIVE_FOLDER_ID = "19pHVBp63Y2j8y5BKPujV78rbwBVeYuBk"
SCOPES = ['https://www.googleapis.com/auth/drive']
DOC_DIR = "uploaded_docs"

# --- GOOGLE AUTHENTICATION HELPERS (Uses st.secrets) ---
def get_gspread_client():
    creds_dict = json.loads(st.secrets["google_api"]["credentials"])
    return gspread.service_account_from_dict(creds_dict)

def get_drive_service():
    creds_dict = json.loads(st.secrets["google_api"]["credentials"])
    creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

# --- THE ULTIMATE UNBREAKABLE PDF RENDERER (NOW WITH ZOOM CONTROLS) ---
def display_pdf(file_path):
    html_path = file_path.replace(".pdf", ".html")
    if os.path.exists(html_path):
        try:
            with open(html_path, "r", encoding="utf-8") as f: raw_html = f.read()
            preview_html = f"""<div style="background-color: white; padding: 40px; margin: 10px auto; border-radius: 5px; box-shadow: 0px 4px 10px rgba(0,0,0,0.1); max-width: 900px; color: #333333;">{raw_html}</div>"""
            components.html(preview_html, height=750, scrolling=True)
            return
        except: pass
            
    if not os.path.exists(file_path):
        st.error("System storage index reference not found.")
        return
        
    try:
        with open(file_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        
        pdf_js_viewer = f"""
        <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.min.js"></script>
        
        <div style="background-color: #2b2b2b; padding: 10px; text-align: center; border-radius: 5px 5px 0 0; border: 1px solid #ccc; border-bottom: none;">
            <button onclick="zoomOut()" style="margin: 0 5px; padding: 6px 15px; cursor: pointer; border-radius: 4px; border: none; background: #f0f2f6; font-weight: bold; color: #31333F;">➖ Zoom Out</button>
            <button onclick="resetZoom()" style="margin: 0 5px; padding: 6px 15px; cursor: pointer; border-radius: 4px; border: none; background: #f0f2f6; font-weight: bold; color: #31333F;">Fit Width</button>
            <button onclick="zoomIn()" style="margin: 0 5px; padding: 6px 15px; cursor: pointer; border-radius: 4px; border: none; background: #f0f2f6; font-weight: bold; color: #31333F;">➕ Zoom In</button>
        </div>
        <div id="pdf-container" style="background-color: #525659; overflow-y: auto; overflow-x: auto; height: 700px; padding: 20px; border-radius: 0 0 5px 5px; border: 1px solid #ccc;">
        </div>
        
        <script>
            var pdfjsLib = window['pdfjs-dist/build/pdf'];
            pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.worker.min.js';
            
            var pdfData = atob('{base64_pdf}');
            var uint8Array = new Uint8Array(pdfData.length);
            for (var i = 0; i < pdfData.length; i++) {{
                uint8Array[i] = pdfData.charCodeAt(i);
            }}
            
            var currentPdf = null;
            var currentScale = 1.0;
            
            function renderPage(page) {{
                var viewport = page.getViewport({{scale: currentScale}});
                var canvas = document.createElement('canvas');
                canvas.style.display = "block";
                canvas.style.margin = "0 auto 20px auto";
                canvas.style.boxShadow = "0px 4px 10px rgba(0,0,0,0.3)";
                canvas.height = viewport.height;
                canvas.width = viewport.width;
                
                var pageDiv = document.createElement('div');
                pageDiv.id = 'page-' + page.pageNumber;
                pageDiv.appendChild(canvas);
                document.getElementById('pdf-container').appendChild(pageDiv);
                
                var context = canvas.getContext('2d');
                page.render({{canvasContext: context, viewport: viewport}});
            }}

            function renderAllPages() {{
                document.getElementById('pdf-container').innerHTML = ''; // Clear container
                for (let pageNum = 1; pageNum <= currentPdf.numPages; pageNum++) {{
                    currentPdf.getPage(pageNum).then(renderPage);
                }}
            }}

            var loadingTask = pdfjsLib.getDocument({{data: uint8Array}});
            loadingTask.promise.then(function(pdf) {{
                currentPdf = pdf;
                currentPdf.getPage(1).then(function(page) {{
                    var containerWidth = document.getElementById('pdf-container').clientWidth - 60;
                    var unscaledViewport = page.getViewport({{scale: 1.0}});
                    currentScale = containerWidth / unscaledViewport.width;
                    renderAllPages();
                }});
            }});
            
            window.zoomIn = function() {{
                currentScale += 0.25;
                renderAllPages();
            }};
            
            window.zoomOut = function() {{
                if (currentScale > 0.5) {{
                    currentScale -= 0.25;
                    renderAllPages();
                }}
            }};
            
            window.resetZoom = function() {{
                currentPdf.getPage(1).then(function(page) {{
                    var containerWidth = document.getElementById('pdf-container').clientWidth - 60;
                    var unscaledViewport = page.getViewport({{scale: 1.0}});
                    currentScale = containerWidth / unscaledViewport.width;
                    renderAllPages();
                }});
            }};
        </script>
        """
        components.html(pdf_js_viewer, height=760, scrolling=False)
    except Exception as e:
        st.error(f"Render Error: {e}")

def get_or_create_client_folder(drive_service, client_name, parent_id):
    safe_name = client_name.replace("'", "\\'")
    query = f"name='{safe_name}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
    response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    folders = response.get('files', [])
    if not folders:
        folder_metadata = {'name': client_name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_id]}
        folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
        return folder.get('id')
    return folders[0].get('id')

def upload_file_to_drive(drive_service, file_bytes, filename, folder_id):
    safe_filename = filename.replace("'", "\\'")
    query = f"name='{safe_filename}' and '{folder_id}' in parents and trashed=false"
    response = drive_service.files().list(q=query, spaces='drive', fields='files(id)').execute()
    existing_files = response.get('files', [])
    for f in existing_files:
        try: drive_service.files().delete(fileId=f.get('id')).execute()
        except: pass
    file_metadata = {'name': filename, 'parents': [folder_id]}
    
    if isinstance(file_bytes, io.BytesIO):
        safe_data = file_bytes.getvalue()
    elif isinstance(file_bytes, (bytearray, bytes)):
        safe_data = bytes(file_bytes)
    else:
        safe_data = file_bytes
        
    media = MediaIoBaseUpload(io.BytesIO(safe_data), mimetype='application/pdf', resumable=True)
    drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

def load_log_data():
    try:
        gc = get_gspread_client()
        sh = gc.open_by_url(SHEET_URL)
        worksheet = sh.sheet1
        data = worksheet.get_all_records()
        if data:
            df = pd.DataFrame(data)
            for col in ["Country of Origin", "Container #", "ETA", "Actual Release Date", 
                        "Lodged Status", "Lodged Date", "Assigned Entry #", "Job State", "Shipment Type"]:
                if col not in df.columns: df[col] = ""
                else: df[col] = df[col].astype("object")
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"☁️ Cloud Connection Error: {e}")
        return pd.DataFrame()

def save_log_data(df):
    try:
        gc = get_gspread_client()
        sh = gc.open_by_url(SHEET_URL)
        worksheet = sh.sheet1
        worksheet.clear()
        df_clean = df.fillna("")
        worksheet.update([df_clean.columns.values.tolist()] + df_clean.values.tolist())
    except Exception as e:
        st.error(f"☁️ Cloud Save Error: {e}")

df_master = load_log_data()

if df_master.empty:
    st.info("📦 Cloud Registry Empty. Ingest structural records from Master Tracker node.")
    st.stop()

f_col1, f_col2 = st.columns(2)
with f_col1: filter_state = st.selectbox("Show Pipelines by Job State", ["Open (Active)", "Closed (Archived)", "All Shipments"])
with f_col2: search_bl = st.text_input("Filter by Bill of Lading (BL#) or Invoice Reference")

df_visible = df_master.copy()
if filter_state == "Open (Active)": df_visible = df_visible[df_visible["Job State"] != "Closed"]
elif filter_state == "Closed (Archived)": df_visible = df_visible[df_visible["Job State"] == "Closed"]

if search_bl:
    mask = df_visible["BL#"].astype(str).str.contains(search_bl, case=False, na=False) | df_visible["Invoice No"].astype(str).str.contains(search_bl, case=False, na=False)
    df_visible = df_visible[mask]

st.write("---")
st.markdown("### 📊 Global Pipeline Snapshot Board")

hc1, hc2, hc3, hc4, hc5 = st.columns([1.5, 2.5, 2, 2, 1.5])
hc1.markdown("**⏱️ ETA Status**")
hc2.markdown("**📦 Shipment ID & Routing**")
hc3.markdown("**🏛️ Customs State**")
hc4.markdown("**📎 Vault Cache**")
hc5.markdown("**⚙️ Action**")
st.markdown("---")

for idx, row in df_visible.iterrows():
    c1, c2, c3, c4, c5 = st.columns([1.5, 2.5, 2, 2, 1.5])
    eta_badge = "⚪ Pending Schedule"
    if str(row.get("Actual Release Date")) not in ["", "nan", "None"]:
        eta_badge = "⚪ **CLEARED (Released)**"
    elif str(row.get("ETA")) not in ["", "nan", "None"]:
        try:
            eta_date = datetime.strptime(str(row["ETA"]), "%Y-%m-%d").date()
            days_left = (eta_date - datetime.today().date()).days
            if days_left <= 5: eta_badge = f"🔴 **CRITICAL** ({days_left}d)"
            elif 6 <= days_left <= 14: eta_badge = f"🟡 **WARNING** ({days_left}d)"
            else: eta_badge = f"🟢 **SCHEDULED** ({days_left}d)"
        except: pass
    c1.markdown(eta_badge)
    
    p_type = row.get("Shipment Type", "🟢 Standard Cargo")
    badge_str = f" | `{p_type}`" if p_type and p_type != "🟢 Standard Cargo" else ""
    c2.markdown(f"**Inv:** {row.get('Invoice No', '')} | **BL:** {row.get('BL#', '')}{badge_str}<br/>*Cont:* {row.get('Container #', 'TBA')} | *Vol:* {row.get('Total CTNS', '')} CTNS", unsafe_allow_html=True)
    c3.markdown(f"{'✅ Lodged' if str(row.get('Lodged Status')) == 'Yes' else '❌ Pending'} <br/> {'🗄️ Closed' if str(row.get('Job State')) == 'Closed' else '📂 Active'}", unsafe_allow_html=True)
    
    inv_str = str(row.get('Invoice No', ''))
    
    expected_paths = [
        f"[{inv_str}] - Original_Invoice.pdf",
        f"[{inv_str}] - Original_Packing_List.pdf",
        f"[{inv_str}] - Custom_Tracker.pdf",
        f"[{inv_str}] - Bill_of_Lading.pdf",
        f"[{inv_str}] - Commercial_Invoice.pdf",
        f"[{inv_str}] - CARICOM_Invoice.pdf",
        f"[{inv_str}] - Packing_List.pdf",
        f"[{inv_str}] - Duties_Assessment.pdf"
    ]
    av_f = sum(1 for p in expected_paths if os.path.exists(f"{DOC_DIR}/{p}"))
    c4.caption(f"Files: {av_f}/8 Vaulted")
    
    if c5.button("📂 Manage Records", key=f"btn_{idx}"):
        st.session_state["selected_row_idx"] = idx
        st.rerun()

st.markdown("---")

if st.session_state["selected_row_idx"] is not None:
    target_idx = st.session_state["selected_row_idx"]
    if target_idx in df_master.index:
        target_row = df_master.loc[target_idx]
        inv_target = str(target_row.get('Invoice No', ''))
        c_name = str(target_row.get("Client Name", ""))
        
        st.markdown(f"### 🛠️ Shipment Control Console (Inv: {inv_target})")
        
        ed_col1, ed_col2, ed_col3 = st.columns(3)
        with ed_col1:
            st.markdown("**🚛 Freight Parameters**")
            c_origin = st.text_input("Country of Origin", value=str(target_row.get("Country of Origin", "")))
            c_number = st.text_input("Container #", value=str(target_row.get("Container #", "")))
            cur_eta = str(target_row.get("ETA", ""))
            try: def_eta = datetime.strptime(cur_eta, "%Y-%m-%d").date() if (cur_eta and cur_eta != "nan" and cur_eta != "") else datetime.today().date()
            except: def_eta = datetime.today().date()
            eta_val = st.date_input("ETA Date Specification", value=def_eta)
        with ed_col2:
            st.markdown("**🏛️ Customs Lodgement**")
            l_status = st.selectbox("Customs Lodged Status", ["No", "Yes"], index=1 if str(target_row.get("Lodged Status")) == "Yes" else 0)
            cur_l_date = str(target_row.get("Lodged Date", ""))
            try: def_l_date = datetime.strptime(cur_l_date, "%Y-%m-%d").date() if (cur_l_date and cur_l_date != "nan" and cur_l_date != "") else datetime.today().date()
            except: def_l_date = datetime.today().date()
            l_date_val = st.date_input("Lodged Date", value=def_l_date) if l_status == "Yes" else ""
            l_entry_val = st.text_input("Assigned Customs Entry #", value=str(target_row.get("Assigned Entry #", ""))) if l_status == "Yes" else ""
            
            p_type_val = str(target_row.get("Shipment Type", "🟢 Standard Cargo"))
            s_type_opts = ["🟢 Standard Cargo", "🔥 PRIORITY SPECIAL", "⚡ EXPRESS LINE", "⚠️ CUSTOMS HOLD REGIME"]
            if p_type_val not in s_type_opts: s_type_opts.append(p_type_val)
            new_s_type = st.selectbox("Shipment Priority Flag", s_type_opts, index=s_type_opts.index(p_type_val))
            
            j_state = st.selectbox("Pipeline Active Job State", ["Open", "Closed"], index=1 if str(target_row.get("Job State")) == "Closed" else 0)
        with ed_col3:
            st.markdown("**📦 Port Releases**")
            cur_rel_date = str(target_row.get("Actual Release Date", ""))
            try: def_rel_date = datetime.strptime(cur_rel_date, "%Y-%m-%d").date() if (cur_rel_date and cur_rel_date != "nan" and cur_rel_date != "") else None
            except: def_rel_date = None
            apply_rel = st.checkbox("Mark as Port Released", value=(def_rel_date is not None))
            rel_date_val = st.date_input("Actual Release Date", value=def_rel_date if def_rel_date else datetime.today().date()) if apply_rel else ""

        st.write("---")
        st.markdown("**🗄️ Upload / Overwrite Source Documents**")
        up1, up2, up3, up4 = st.columns(4)
        with up1: f_rat = st.file_uploader("Upload Original Invoice", type=["pdf"], key="f_rat")
        with up2: f_opk = st.file_uploader("Upload Orig. Packing List", type=["pdf"], key="f_opk")
        with up3: f_trk = st.file_uploader("Upload Tracker Document", type=["pdf"], key="f_trk")
        with up4: f_bl = st.file_uploader("Upload Bill of Lading", type=["pdf"], key="f_bl")

        if st.button("💾 Commit Tracking Matrix & Save to Cloud", type="primary", use_container_width=True):
            with st.spinner("Synchronizing Vaults & Ledger..."):
                df_master.at[target_idx, "Country of Origin"] = c_origin
                df_master.at[target_idx, "Container #"] = c_number
                df_master.at[target_idx, "ETA"] = str(eta_val)
                df_master.at[target_idx, "Actual Release Date"] = str(rel_date_val) if apply_rel else ""
                df_master.at[target_idx, "Job State"] = j_state
                df_master.at[target_idx, "Lodged Status"] = l_status
                df_master.at[target_idx, "Lodged Date"] = str(l_date_val) if l_status == "Yes" else ""
                df_master.at[target_idx, "Assigned Entry #"] = l_entry_val if l_status == "Yes" else ""
                df_master.at[target_idx, "Shipment Type"] = new_s_type
                
                if f_rat:
                    with open(f"{DOC_DIR}/[{inv_target}] - Original_Invoice.pdf", "wb") as f: f.write(f_rat.getbuffer())
                if f_opk:
                    with open(f"{DOC_DIR}/[{inv_target}] - Original_Packing_List.pdf", "wb") as f: f.write(f_opk.getbuffer())
                if f_trk:
                    with open(f"{DOC_DIR}/[{inv_target}] - Custom_Tracker.pdf", "wb") as f: f.write(f_trk.getbuffer())
                if f_bl:
                    with open(f"{DOC_DIR}/[{inv_target}] - Bill_of_Lading.pdf", "wb") as f: f.write(f_bl.getbuffer())

                if f_rat or f_opk or f_trk or f_bl:
                    try:
                        drive_service = get_drive_service()
                        client_folder_id = get_or_create_client_folder(drive_service, c_name, DRIVE_FOLDER_ID)
                        if f_rat: upload_file_to_drive(drive_service, f_rat.getvalue(), f"[{inv_target}] - {c_name} - Original_Invoice.pdf", client_folder_id)
                        if f_opk: upload_file_to_drive(drive_service, f_opk.getvalue(), f"[{inv_target}] - {c_name} - Original_Packing_List.pdf", client_folder_id)
                        if f_trk: upload_file_to_drive(drive_service, f_trk.getvalue(), f"[{inv_target}] - {c_name} - Custom_Tracker.pdf", client_folder_id)
                        if f_bl:  upload_file_to_drive(drive_service, f_bl.getvalue(), f"[{inv_target}] - {c_name} - Bill of Lading.pdf", client_folder_id)
                    except Exception as e:
                        st.warning(f"Cloud Drive upload bypass active: {e}")

                save_log_data(df_master)
                st.success("🎉 Matrix changes updated into live cloud ledger records successfully!")
                st.rerun()

        st.write("---")
        st.markdown("### 🗄️ Interactive Security Document Vault")
        
        doc_map = {
            "Original Invoice (Uploaded)": f"{DOC_DIR}/[{inv_target}] - Original_Invoice.pdf",
            "Original Packing List (Uploaded)": f"{DOC_DIR}/[{inv_target}] - Original_Packing_List.pdf",
            "Custom Tracker Document (Uploaded)": f"{DOC_DIR}/[{inv_target}] - Custom_Tracker.pdf",
            "Bill of Lading (Uploaded)": f"{DOC_DIR}/[{inv_target}] - Bill_of_Lading.pdf",
            "Commercial Invoice (System Generated)": f"{DOC_DIR}/[{inv_target}] - Commercial_Invoice.pdf",
            "CARICOM Invoice (System Generated)": f"{DOC_DIR}/[{inv_target}] - CARICOM_Invoice.pdf",
            "Duties Assessment (System Generated)": f"{DOC_DIR}/[{inv_target}] - Duties_Assessment.pdf",
            "Sequential Packing List (System Generated)": f"{DOC_DIR}/[{inv_target}] - Packing_List.pdf"
        }
        
        available_docs = {name: path for name, path in doc_map.items() if os.path.exists(path)}
        if not available_docs:
            st.info("ℹ️ No system documents found for this tracking node code context.")
        else:
            v_col1, v_col2 = st.columns([1, 2])
            with v_col1:
                selected_doc_name = st.radio("Available Container Files Asset Index:", list(available_docs.keys()))
                target_path = available_docs[selected_doc_name]
                
                with open(target_path, "rb") as f:
                    raw_dl_data = f.read()
                    safe_dl_data = bytes(raw_dl_data) if isinstance(raw_dl_data, bytearray) else raw_dl_data
                    st.download_button("⬇️ Download File", safe_dl_data, file_name=os.path.basename(target_path), mime="application/pdf", type="primary")
            with v_col2:
                display_pdf(target_path)