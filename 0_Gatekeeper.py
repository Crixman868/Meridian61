import streamlit as st
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="Meridian 61 Access", page_icon="🌐", layout="wide", initial_sidebar_state="collapsed")

# --- BRANDING & STYLING ---
st.markdown("""
    <style>
    /* 1. Hide the Sidebar on the Login Page to prevent bypassing */
    [data-testid="stSidebar"] {
        display: none !important;
    }
    
    /* 2. The Custom Orange Orbital Background */
    .stApp {
        background-color: #FAFAFA;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1440 900' preserveAspectRatio='xMidYMid slice'%3E%3Cpath d='M-200,1000 C400,600 1000,200 1600,-200' fill='none' stroke='%23FF6700' stroke-width='120' stroke-opacity='0.12' /%3E%3Cpath d='M-200,1000 C400,600 1000,200 1600,-200' fill='none' stroke='%23FF6700' stroke-width='8' stroke-opacity='0.45' transform='translate(0, -60)' /%3E%3C/svg%3E");
        background-attachment: fixed;
        background-position: center;
        background-repeat: no-repeat;
        background-size: cover;
    }
    
    /* 3. Force Vibrant Orange Primary Button */
    div[data-testid="stButton"] > button {
        background-color: #FF6700 !important;
        color: white !important;
        border: none !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        height: 50px !important;
        transition: all 0.3s ease;
        box-shadow: 0px 4px 10px rgba(255, 103, 0, 0.2);
        margin-top: 15px;
    }
    div[data-testid="stButton"] > button:hover {
        background-color: #E65C00 !important;
        box-shadow: 0px 6px 15px rgba(255, 103, 0, 0.3);
    }
    
    /* 4. Remove the default top padding to pull everything up cleanly */
    .block-container {
        padding-top: 3rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- NATIVE STREAMLIT CENTERING ---
spacer_left, main_col, spacer_right = st.columns([1, 1.2, 1])

with main_col:
    # --- LOGO SECTION ---
    st.markdown("<div style='display: flex; justify-content: center; margin-bottom: 10px;'>", unsafe_allow_html=True)
    if os.path.exists("assets/logo.png"):
        st.image("assets/logo.png", width=280)
    elif os.path.exists("logo.png"):
        st.image("logo.png", width=280)
    else:
        st.warning("⚠️ Logo file missing. System running in text-only mode.")
    st.markdown("</div>", unsafe_allow_html=True)

    # --- TITLES ---
    st.markdown("<h2 style='text-align: center; color: #0A2240; margin-bottom: 0px; padding-bottom: 0px;'>Portal Access</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666666; margin-bottom: 30px; font-size: 16px;'>Secure Gatekeeper</p>", unsafe_allow_html=True)

    # --- LOGIN FORM ---
    user = st.text_input("Username")
    password = st.text_input("Password", type="password")

    # --- ROUTING & ACCESS CONTROL LOGIC ---
    if st.button("Enter Portal", use_container_width=True):
        
        # 1. Administrator Level (Full Access)
        if user == "allrounder" and password == "Cocosteaw123!": 
            st.session_state["logged_in"] = True
            st.session_state["is_admin"] = True
            st.success("Admin Authentication successful. Initializing Master Log...")
            st.switch_page("pages/3_Master_Log.py")
            
        # 2. Staff Level - Elton (Read-Only)
        elif user == "elton" and password == "8681":
            st.session_state["logged_in"] = True
            st.session_state["is_admin"] = False
            st.success("Staff Authentication successful. Loading View-Only Log...")
            st.switch_page("pages/3_Master_Log.py")
            
        # 3. Staff Level - Smallman (Read-Only)
        elif user == "smallman" and password == "8682":
            st.session_state["logged_in"] = True
            st.session_state["is_admin"] = False
            st.success("Staff Authentication successful. Loading View-Only Log...")
            st.switch_page("pages/3_Master_Log.py")
            
        # 4. Failed Authentication
        else:
            st.error("Access Denied. Invalid credentials.")