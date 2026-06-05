import streamlit as st
import os

# --- PAGE CONFIG ---
# Using "wide" layout so we can use columns to perfectly center the form
st.set_page_config(page_title="Meridian 61 Access", page_icon="🌐", layout="wide")

# --- BRANDING & STYLING ---
st.markdown("""
    <style>
    /* The Custom Orange Orbital Background */
    /* Features a dynamic double-swoosh mimicking the logo's globe orbit */
    .stApp {
        background-color: #FAFAFA;
        background-image: url("data:image/svg+xml,%3Csvg width='100%25' height='100%25' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M -10vw 110vh C 30vw 80vh, 60vw 30vh, 110vw -10vh' fill='none' stroke='%23FF6700' stroke-width='40' stroke-opacity='0.10' /%3E%3Cpath d='M -10vw 110vh C 35vw 85vh, 65vw 35vh, 110vw 0vh' fill='none' stroke='%23FF6700' stroke-width='4' stroke-opacity='0.30' /%3E%3Cpath d='M 10vw 120vh C 45vw 90vh, 75vw 40vh, 120vw 10vh' fill='none' stroke='%230A2240' stroke-width='2' stroke-opacity='0.04' /%3E%3C/svg%3E");
        background-attachment: fixed;
        background-position: center;
        background-repeat: no-repeat;
        background-size: cover;
    }
    
    /* Vibrant Orange Button */
    div.stButton > button {
        background-color: #FF6700 !important;
        color: white !important;
        border: none !important;
        font-weight: bold !important;
        width: 100% !important;
        border-radius: 8px !important;
        height: 50px !important;
        transition: all 0.3s ease;
        box-shadow: 0px 4px 10px rgba(255, 103, 0, 0.2);
        margin-top: 15px;
    }
    div.stButton > button:hover {
        background-color: #E65C00 !important;
        box-shadow: 0px 6px 15px rgba(255, 103, 0, 0.3);
    }
    
    /* Remove the default top padding to pull everything up cleanly */
    .block-container {
        padding-top: 2rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- NATIVE STREAMLIT CENTERING ---
# We use empty columns on the left and right to squeeze the form into the middle
spacer_left, main_col, spacer_right = st.columns([1, 1.2, 1])

with main_col:
    # --- LOGO SECTION ---
    st.markdown("<div style='display: flex; justify-content: center; margin-bottom: 20px; margin-top: 40px;'>", unsafe_allow_html=True)
    if os.path.exists("assets/logo.png"):
        st.image("assets/logo.png", width=280)
    elif os.path.exists("logo.png"):
        st.image("logo.png", width=280)
    else:
        st.warning("⚠️ Logo file missing. System running in text-only mode.")
    st.markdown("</div>", unsafe_allow_html=True)

    # --- TITLES ---
    st.markdown("<h2 style='text-align: center; color: #0A2240; margin-bottom: 0px;'>Portal Access</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666666; margin-bottom: 30px; font-size: 16px;'>Secure Gatekeeper</p>", unsafe_allow_html=True)

    # --- LOGIN FORM ---
    # These inputs now sit natively on the page, no HTML boxes to glitch out
    user = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Enter Portal"):
        # Replace with your actual secure authentication logic
        if user == "Admin" and password == "Majestic2026": 
            st.session_state["logged_in"] = True
            st.session_state["is_admin"] = True
            st.success("Authentication successful. Initializing Master Log...")
            st.switch_page("pages/3_Master_Log.py")
        else:
            st.error("Access Denied. Invalid credentials.")