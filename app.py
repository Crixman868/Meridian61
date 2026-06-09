import streamlit as st
import pandas as pd
import os
import gspread
import json
from datetime import datetime
from weasyprint import HTML
import tempfile
import base64

# ... [Keep your existing imports and Helper Functions (get_gspread_client, load_log_data, save_log_data, upload_system_pdf_to_drive)] ...

def generate_caricom_printout(inv_num, date, client, supplier, compliance_data, df_items):
    # This is your static, landscape-style document generator (mimicking Packing List)
    decl = "CARICOM COMMON MARKET DECLARATION: The undermentioned exporter hereby declares that the cargo specified in this commercial invoice manifest has been produced completely within the parameters of the common market rules of origin. All values and freight indices specified herein match active terminal data profiles perfectly."
    
    html = f"""
    <html><body style="font-family: Arial, sans-serif; font-size: 11px;">
    <h2 style="text-align: center;">CARICOM INVOICE</h2>
    <table width="100%" border="1" cellpadding="5" cellspacing="0">
        <tr><td><b>Invoice No:</b> {inv_num}</td><td><b>Date:</b> {date}</td></tr>
        <tr><td><b>Exporter:</b> {supplier}</td><td><b>Buyer/Consignee:</b> {client}</td></tr>
    </table>
    <br>
    <table width="100%" border="1" cellpadding="5" cellspacing="0">
        <tr><th>Order No</th><th>Origin</th><th>Loading Port</th><th>Discharge Port</th><th>Final Dest</th><th>Transport</th></tr>
        <tr>
            <td>{compliance_data.get('cust_order_no', '')}</td>
            <td>{compliance_data.get('country_origin', '')}</td>
            <td>{compliance_data.get('port_loading', '')}</td>
            <td>{compliance_data.get('port_discharge', '')}</td>
            <td>{compliance_data.get('final_dest', '')}</td>
            <td>{compliance_data.get('mode_transport', '')}</td>
        </tr>
    </table>
    <br>
    <table width="100%" border="1" cellpadding="5" cellspacing="0">
        <tr><th>Description</th><th>Quantity</th></tr>
        {"".join([f"<tr><td>{row.get('Description','')}</td><td>{row.get('Qty','')}</td></tr>" for _, row in df_items.iterrows()])}
    </table>
    <br>
    <p style="border: 1px solid #000; padding: 10px; font-size: 10px;">{decl}</p>
    </body></html>
    """
    return html

def render_admin_tracker():
    st.title("📦 Command Console: Master Tracker")
    active_shell_uid = st.session_state.get("active_shell_uid", "")
    
    # ... [Keep your existing Data Intake & Matrix Mapping code] ...

    with st.expander("📝 Customs Compliance Details (CARICOM)", expanded=True):
        col1, col2 = st.columns(2)
        cust_order_no = col1.text_input("Customer's Order No.")
        country_origin = col2.text_input("Country of Origin", "USA")
        port_loading = col1.text_input("Port of Loading")
        port_discharge = col2.text_input("Port of Discharge")
        final_dest = col1.text_input("Final Destination", "Trinidad & Tobago")
        mode_transport = col2.selectbox("Mode", ["SHIP", "AIR", "COURIER", "OTHER"])

    # Collect inputs locally for this execution
    comp_data = {
        "cust_order_no": cust_order_no, "country_origin": country_origin,
        "port_loading": port_loading, "port_discharge": port_discharge,
        "final_dest": final_dest, "mode_transport": mode_transport
    }

    if st.button("💾 Save CARICOM Invoice Only", type="primary"):
        with st.spinner("Locking CARICOM Invoice..."):
            # Ensure we have clean data
            html = generate_caricom_printout(invoice_num, invoice_date, client_name, supplier_name, comp_data, df_clean)
            link = upload_system_pdf_to_drive(html, f"{invoice_num}_CARICOM.pdf", client_name, invoice_num)
            
            df_update = load_log_data()
            df_update = sync_base_metadata_to_log(df_update, invoice_num, client_name, container_total_ctns, invoice_date)
            idx = df_update.index[df_update['Row_UID'].astype(str).str.strip() == active_shell_uid.strip()].tolist()[0]
            df_update.at[idx, "CARICOM Invoice"] = link
            save_log_data(df_update)
            st.success("✅ CARICOM Locked!")

# ... [Keep the rest of your existing code and execution blocks] ...
