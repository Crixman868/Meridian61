import streamlit as st
import pandas as pd
from app import load_log_data, get_eta_status, ALL_DOCS
from datetime import datetime

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Staff Dashboard", layout="wide")

# 2. STYLING (Including purple override for the table)
st.markdown("""
<style>
    .stApp { background-color: #ffffff; }
    /* Ensure text remains legible */
    .stDataFrame { color: #000000 !important; }
</style>
""", unsafe_allow_html=True)

# 3. DASHBOARD RENDERING LOGIC
def render_staff_dashboard():
    st.title("📊 Operational Floor Dashboard")
    
    df_raw = load_log_data()
    if df_raw.empty:
        st.info("No active shipments to display.")
        return
        
    df = df_raw.copy()

    # Timeline Status Logic
    def get_status_label(row):
        ship_status = str(row.get("Shipment Status", ""))
        raw_eta = row.get("ETA")
        timestamp = pd.to_datetime(raw_eta, errors='coerce')
        current_date = timestamp.date() if not pd.isna(timestamp) else datetime.now().date()
        label, _ = get_eta_status(current_date, ship_status)
        return label

    df["Shipment Status"] = df.apply(get_status_label, axis=1)

    # Visual Transformation (Links to Checked Boxes)
    doc_cols = [col for col in ALL_DOCS if col in df.columns]
    
    def get_doc_status(row):
        for col in doc_cols:
            if not str(row[col]).startswith("http"):
                return "⏳ PENDING"
        return "✅ READY"

    df["Doc Status"] = df.apply(get_doc_status, axis=1)
    
    for col in doc_cols:
        df[col] = df[col].apply(lambda x: "✅" if str(x).startswith("http") else "⬜")

    # NALDO Formatting
    df["NALDO"] = df["NALDO"].apply(lambda x: "✅" if str(x).strip().upper() == "YES" else "⬜")
    
    # Display Grid
    display_cols = ["Invoice No", "Client Name", "ETA", "Shipment Status", "NALDO"] + doc_cols + ["Doc Status"]
    df_display = df[display_cols]

    # Conditional Styling
    def style_dashboard(row):
        styles = [''] * len(row)
        # NALDO Purple Override
        if 'NALDO' in row.index and row['NALDO'] == '✅':
            styles[row.index.get_loc('NALDO')] = 'background-color: #9b59b6; color: white; font-weight: bold;'
        
        # Timeline Overdue/Urgent Highlighting
        if 'Shipment Status' in row.index:
            s = str(row['Shipment Status'])
            if 'OVERDUE' in s: styles[row.index.get_loc('Shipment Status')] = 'background-color: #ffb3b3;'
            if 'URGENT' in s: styles[row.index.get_loc('Shipment Status')] = 'background-color: #ffe6a8;'
        
        return styles

    # Render Data Grid
    st.dataframe(df_display.style.apply(style_dashboard, axis=1), use_container_width=True, hide_index=True)

# 4. EXECUTION
render_staff_dashboard()
