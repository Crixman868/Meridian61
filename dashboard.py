import streamlit as st
import pandas as pd
from app import load_log_data, get_eta_status, ALL_DOCS
from datetime import datetime

# 1. PAGE CONFIGURATION
st.set_page_config(
    page_title="Staff Dashboard", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# 2. CSS FOR MOBILE, ALIGNMENT, AND SPACING
st.markdown("""
<style>
    /* Remove white gap above title */
    .block-container { padding-top: 1rem; }
    
    /* Smaller title */
    h1 { font-size: 1.5rem !important; margin-bottom: 0.5rem !important; }
    
    /* Center/Middle align headers and cells */
    div[data-testid="stDataFrame"] th {
        text-align: center !important;
        vertical-align: middle !important;
        white-space: normal !important;
    }
    div[data-testid="stDataFrame"] td {
        text-align: center !important;
        vertical-align: middle !important;
    }
</style>
""", unsafe_allow_html=True)

def render_staff_dashboard():
    st.title("📊 Operational Floor Dashboard")
    
    df_raw = load_log_data()
    if df_raw.empty:
        st.info("No active shipments to display.")
        return
        
    df = df_raw.copy()

    # Timeline Logic
    def get_status_label(row):
        ship_status = str(row.get("Shipment Status", ""))
        raw_eta = row.get("ETA")
        timestamp = pd.to_datetime(raw_eta, errors='coerce')
        current_date = timestamp.date() if not pd.isna(timestamp) else datetime.now().date()
        label, _ = get_eta_status(current_date, ship_status)
        return label

    df["Status"] = df.apply(get_status_label, axis=1)

    # Visual Transformation (Doc Links to ✅/⬜)
    doc_cols = [col for col in ALL_DOCS if col in df.columns]
    
    def get_doc_status(row):
        for col in doc_cols:
            if not str(row[col]).startswith("http"):
                return "⏳ PENDING"
        return "✅ READY"

    df["Doc Status"] = df.apply(get_doc_status, axis=1)
    
    for col in doc_cols:
        df[col] = df[col].apply(lambda x: "✅" if str(x).startswith("http") else "⬜")

    df["NALDO"] = df["NALDO"].apply(lambda x: "✅" if str(x).strip().upper() == "YES" else "⬜")
    
    # EXACT HEADER ORDER
    display_cols = ["Total Cartons", "Status", "NALDO", "ETA", "Container #", "Client Name", "Country of Origin", "Invoice No"] + doc_cols + ["Doc Status"]
    df_display = df[display_cols]
    df_display.columns = ["TOTAL CTNS", "Status", "NALDO", "ETA", "Container #", "Client", "Origin", "Invoice#"] + doc_cols + ["Doc Status"]

    # Conditional Styling
    def style_dashboard(row):
        styles = [''] * len(row)
        # NALDO Purple Override
        if 'NALDO' in row.index and row['NALDO'] == '✅':
            styles[row.index.get_loc('NALDO')] = 'background-color: #9b59b6; color: white; font-weight: bold;'
        
        # Timeline Overdue/Urgent Highlighting
        if 'Status' in row.index:
            s = str(row['Status'])
            if 'OVERDUE' in s: styles[row.index.get_loc('Status')] = 'background-color: #ffb3b3; color: black;'
            if 'URGENT' in s: styles[row.index.get_loc('Status')] = 'background-color: #ffe6a8; color: black;'
        return styles

    # Column Configuration (Locked/Pinned "TOTAL CTNS" column)
    column_config = {
        "TOTAL CTNS": st.column_config.Column("TOTAL CTNS", pinned=True),
    }

    # Render Data Grid with Column Locking and Locked Headers (height=600 locks headers)
    st.dataframe(
        df_display.style.apply(style_dashboard, axis=1), 
        use_container_width=True, 
        hide_index=True,
        column_config=column_config,
        height=600 
    )

# Execution
render_staff_dashboard()
