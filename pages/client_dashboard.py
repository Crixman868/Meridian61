import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import base64
import uuid
from datetime import datetime
import gspread

st.set_page_config(page_title="Client Dashboard", page_icon="🏢", layout="wide")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1ipB1DaIdX_BS_0iSWRHMwHcP-wEpfu2pZzFT3nJtlho/edit?gid=0#gid=0"
DOC_DIR = "uploaded_docs"

# --- THE ULTIMATE UNBREAKABLE PDF RENDERER (PDF.JS CANVAS BYPASS WITH ZOOM) ---
def display_pdf(file_path):
    # 1. System Generated HTML fallback (For fast loading if available)
    html_path = file_path.replace(".pdf", ".html")
    if os.path.exists(html_path):
        try:
            with open(html_path, "r", encoding="utf-8") as f: raw_html = f.read()
            preview_html = f"""<div style="background-color: white; padding: 40px; margin: 10px auto; border-radius: 5px; box-shadow: 0px 4px 10px rgba(0,0,0,0.1); max-width: 900px; color: #333333;">{raw_html}</div>"""
            components.html(preview_html, height=750, scrolling=True)
            return
        except: pass
            
    if not os.path.exists(file_path):
        st.error("Document asset context missing from system registry.")
        return
        
    try:
        # 2. PDF.JS Canvas Engine: Bypasses Chrome Sandbox restrictions completely by drawing the PDF natively.
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
                // Auto-fit to width on initial load
                currentPdf.getPage(1).then(function(page) {{
                    var containerWidth = document.getElementById('pdf-container').clientWidth - 60; // account for padding/scrollbars
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

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.error("🚨 Access Denied. Please log in through the Secure Gatekeeper.")
    st.stop()

if "client_row_idx" not in st.session_state:
    st.session_state["client_row_idx"] = None

@st.cache_data(ttl=2)
def load_data():
    try:
        gc = gspread.service_account(filename="credentials.json")
        sh = gc.open_by_url(SHEET_URL)
        worksheet = sh.sheet1
        data = worksheet.get_all_records()
        if data:
            df = pd.DataFrame(data)
            for col in ["Container #", "ETA", "Actual Release Date", "Lodged Status", "Job State", "Shipment Type"]:
                if col not in df.columns: df[col] = ""
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"☁️ Cloud Connection Error: {e}")
        return pd.DataFrame()

df_master = load_data()

if df_master.empty:
    st.info("🏢 Logistics registry initialization pending.")
    st.stop()

current_role = st.session_state.get("role", "client")
current_user = st.session_state.get("username", "Client Alpha")

if current_role == "client":
    df_client = df_master[df_master["Client Name"].str.lower() == current_user.lower()].copy()
    st.title(f"🏢 Executive Dashboard: {current_user.upper()} (☁️ CLOUD)")
else:
    st.title("🏢 Client Dashboard (Staff Preview Mode) (☁️ CLOUD)")
    client_list = df_master["Client Name"].dropna().unique().tolist()
    selected_client = st.selectbox("👁️ Select Client Account to Preview:", client_list)
    df_client = df_master[df_master["Client Name"] == selected_client].copy()
    current_user = selected_client

st.write("---")

if df_client.empty:
    st.info(f"Welcome {current_user}! You have no active entries currently processing in the global network.")
    st.stop()

active_count = len(df_client[df_client["Job State"] != "Closed"])
closed_count = len(df_client[df_client["Job State"] == "Closed"])

m1, m2 = st.columns(2)
m1.metric("🟢 Active Freight Lines", active_count)
m2.metric("📦 Cleared Consignments", closed_count)

st.write("---")
st.markdown("### 🚢 Live Tracking Board")

hc1, hc2, hc3, hc4 = st.columns([1.5, 3, 2, 1.5])
hc1.markdown("**⏱️ ETA Status**")
hc2.markdown("**📦 Shipment & Routing**")
hc3.markdown("**🏛️ Customs Status**")
hc4.markdown("**🗄️ Documents**")
st.markdown("---")

for idx, row in df_client.iterrows():
    c1, c2, c3, c4 = st.columns([1.5, 3, 2, 1.5])
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
    c2.markdown(f"**Inv:** {row['Invoice No']} | **BL:** {row['BL#']}{badge_str}<br/>*Cont:* {row.get('Container #', 'TBA')} | *Vol:* {row['Total CTNS']} CTNS", unsafe_allow_html=True)
    
    c3.markdown(f"{'✅ Lodged' if str(row.get('Lodged Status')) == 'Yes' else '❌ Pending'} <br/> {'🗄️ Closed' if str(row.get('Job State')) == 'Closed' else '📂 Active'}", unsafe_allow_html=True)
    
    if c4.button("📂 View Vault", key=f"client_btn_{idx}"):
        st.session_state["client_row_idx"] = idx
        st.rerun()

st.markdown("---")

if st.session_state["client_row_idx"] is not None:
    target_idx = st.session_state["client_row_idx"]
    if target_idx in df_client.index:
        target_row = df_client.loc[target_idx]
        inv_target = str(target_row['Invoice No'])
        
        st.markdown(f"### 🗄️ Secure Document Vault (Inv: {inv_target})")
        doc_map = {
            "Original Invoice (Uploaded)": f"{DOC_DIR}/{inv_target}_rattans.pdf",
            "Original Packing List (Uploaded)": f"{DOC_DIR}/{inv_target}_original_packing.pdf",
            "Custom Tracker Document (Uploaded)": f"{DOC_DIR}/{inv_target}_tracker_doc.pdf",
            "Bill of Lading (Uploaded)": f"{DOC_DIR}/{inv_target}_bill_of_lading.pdf",
            "Commercial Invoice Set": f"{DOC_DIR}/Commercial_Invoice_{inv_target}.pdf",
            "CARICOM Common Market Document": f"{DOC_DIR}/CARICOM_Invoice_{inv_target}.pdf",
            "Official Duties & Tax Assessment": f"{DOC_DIR}/Duties_Assessment_{inv_target}.pdf",
            "Sequential Packing Manifest": f"{DOC_DIR}/Packing_List_{inv_target}.pdf"
        }
        available_docs = {name: path for name, path in doc_map.items() if os.path.exists(path)}
        
        if not available_docs:
            st.warning("Documents matching this layout criteria are currently processing mapping indexing.")
        else:
            v_col1, v_col2 = st.columns([1, 2.5])
            with v_col1:
                selected_doc_name = st.radio("Available Files Asset Index:", list(available_docs.keys()))
                target_path = available_docs[selected_doc_name]
                with open(target_path, "rb") as f:
                    # THE FIX: Byte-safe formatting to prevent client-side download button crashes
                    raw_dl_data = f.read()
                    safe_dl_data = bytes(raw_dl_data) if isinstance(raw_dl_data, bytearray) else raw_dl_data
                    st.download_button("⬇️ Download PDF", safe_dl_data, file_name=os.path.basename(target_path), mime="application/pdf", type="primary")
            with v_col2:
                display_pdf(target_path)
