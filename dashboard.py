import streamlit as st
import pandas as pd
from app import load_log_data, get_eta_status, ALL_DOCS
from datetime import datetime

st.set_page_config(page_title="Staff Dashboard", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .stApp { background-color: #ffffff; }
    /* Mobile-responsive font scaling */
    .stDataFrame { font-size: 0.8rem !important; }
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

    df["Shipment Status"] = df.apply(get_status_label, axis=1)

    # All Original Columns preserved
    doc_cols = [col for col in ALL_DOCS if col in df.columns]
    
    # Doc Status Calculation (Ready vs Pending)
    def get_doc_status(row):
        for col in doc_cols:
            if not str(row[col]).startswith("http"):
                return "⏳ PENDING"
        return "✅ READY"

    df["Doc Status"] = df.apply(get_doc_status, axis=1)
    
    # Visual Binary Transformation for all docs
    for col in doc_cols:
        df[col] = df[col].apply(lambda x: "✅" if str(x).startswith("http") else "⬜")

    df["NALDO"] = df["NALDO"].apply(lambda x: "✅" if str(x).strip().upper() == "YES" else "⬜")
    
    # KEEP ALL COLUMNS
    display_cols = ["Invoice No", "Shipment Status", "NALDO"] + doc_cols + ["Doc Status"]
    df_display = df[display_cols]

    # Styling
    def style_dashboard(row):
        styles = [''] * len(row)
        if 'NALDO' in row.index and row['NALDO'] == '✅':
            styles[row.index.get_loc('NALDO')] = 'background-color: #9b59b6; color: white; font-weight: bold;'
        if 'Shipment Status' in row.index:
            s = str(row['Shipment Status'])
            if 'OVERDUE' in s: styles[row.index.get_loc('Shipment Status')] = 'background-color: #ffb3b3; color: black;'
            if 'URGENT' in s: styles[row.index.get_loc('Shipment Status')] = 'background-color: #ffe6a8; color: black;'
        return styles

    # Mobile-optimized grid: use_container_width + scrolling handles the columns
    st.dataframe(
        df_display.style.apply(style_dashboard, axis=1), 
        use_container_width=True, 
        hide_index=True
    )

render_staff_dashboard()
