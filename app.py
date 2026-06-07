import streamlit as st
import pandas as pd
import os

# [Include your existing imports and helper functions...]

# ==========================================
# 4. VIEW FUNCTIONS (WITH ERROR TRAPS)
# ==========================================

def render_master_log():
    st.subheader("🗄️ System Workspace Overview")
    try:
        df = load_log_data()
        # [Existing render logic...]
    except Exception as e:
        st.error(f"Error in Master Log: {e}")

def render_admin_tracker():
    st.subheader("⚙️ Active File Processor Matrix")
    
    # SAFE FILE LOADING
    client_file = "clients.csv"
    supplier_file = "suppliers.csv"
    
    if not os.path.exists(client_file):
        st.error(f"CRITICAL: {client_file} is missing from your GitHub repository.")
        return
    if not os.path.exists(supplier_file):
        st.error(f"CRITICAL: {supplier_file} is missing from your GitHub repository.")
        return

    try:
        client_options = ["Select a Client..."] + sorted(pd.read_csv(client_file)["Name"].dropna().tolist())
        supplier_options = ["Select a Supplier..."] + sorted(pd.read_csv(supplier_file)["Name"].dropna().tolist())
        
        # [The rest of your existing logic...]
        
    except Exception as e:
        st.error(f"Error in Processor Matrix: {e}")

# ==========================================
# 5. MAIN (DEBUGGED)
# ==========================================
st.title("🚢 Meridian Command Console")

# Ensure target ID is initialized
if "target_m61_id" not in st.session_state:
    st.session_state["target_m61_id"] = "-- Choose Active Shell --"

# Navigation
nav = st.radio("Modules", ["📋 Master Dashboard Workstation", "📦 File Template Processor Matrix"], horizontal=True)

if nav == "📋 Master Dashboard Workstation":
    render_master_log()
else:
    render_admin_tracker()
