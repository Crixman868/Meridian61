import streamlit as st
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="Meridian 61 Access", page_icon="🌐")

# --- BRANDING & STYLING ---
st.markdown("""
    <style>
    /* The Subtle Geometric Background */
    .stApp {
        background-color: #FAFAFA;
        background-image: url("data:image/svg+xml,%3Csvg width='100%25' height='100%25' xmlns='http://www.w3.org/2000/svg'%3E%3Cpattern id='grid' width='60' height='60' patternUnits='userSpaceOnUse'%3E%3Cpath d='M 60 0 L 0 0 0 60' fill='none' stroke='%230A2240' stroke-width='1' stroke-opacity='0.03'/%3E%3C/pattern%3E%3Crect width='100%25' height='100%25' fill='url(%23grid)' /%3E%3Cline x1='61%25' y1='0' x2='61%25' y2='100%25' stroke='%230A2240' stroke-width='2' stroke-opacity='0.08' /%3E%3Ccircle cx='61%25' cy='35%25' r='500' fill='none' stroke='%23FF6700' stroke-width='1.5' stroke-opacity='0.08' /%3E%3Ccircle cx='61%25' cy='35%25' r='300' fill='none' stroke='%230A2240' stroke-width='1' stroke-opacity='0.04' /%3E%3C/svg%3E");
        background-attachment: fixed;
        background-position: center;
        background-repeat: no-repeat;
        background-size: cover;
    }
    
    /* Clean, Floating White Card Styling */
    .login-card {
        background-color: #FFFFFF;
        padding: 40px;
        border-radius: 16px;
        box-shadow: 0px 15px 40px rgba(10, 34, 64, 0.08);
        border: 1px solid rgba(10, 34, 64, 0.05);
        max-width: 400px;
        margin: 40px auto;
        position: relative;
        z-index: 10;
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
    }
    div.stButton > button:hover {
        background-color: #E65C00 !important;
        box-shadow: 0px 6px 15px rgba(255, 103, 0, 0.3);
    }
    
    /* Centering the logo container */
    .logo-container {
        display: flex;
        justify-content: center;
        margin-bottom: 25px;
    }
    
    /* Subtitle Styling */
    .auth-title {
        color: #0A2240;
        text-align: center;
        font-family: 'Inter', sans-serif;
        margin-bottom: 5px;
    }
    .auth-subtitle {
        color: #666666;
        text-align: center;
        font-size: 14px;
        margin-bottom: 30px;
    }
    </style>
    """, unsafe_allow_html=True)


# --- LOGIN FORM CONTAINER ---
st.markdown("<div class='login-card'>", unsafe_allow_html=True)

# --- LOGO SECTION (BULLETPROOFED) ---
st.markdown("<div class='logo-container'>", unsafe_allow_html=True)
if os.path.exists("assets/logo.png"):
    st.image("assets/logo.png", width=260)
elif os.path.exists("logo.png"):
    st.image("logo.png", width=260)
else:
    st.warning("⚠️ Logo file missing. System running in text-only mode.")
st.markdown("</div>", unsafe_allow_html=True)

# --- AUTHENTICATION FIELDS ---
st.markdown("<h3 class='auth-title'>Portal Access</h3>", unsafe_allow_html=True)
st.markdown("<p class='auth-subtitle'>Secure Gatekeeper</p>", unsafe_allow_html=True)

user = st.text_input("Username")
password = st.text_input("Password", type="password")

st.write("") # Quick spacer

if st.button("Enter Portal"):
    # Replace with your actual secure authentication logic
    if user == "Admin" and password == "Majestic2026": 
        st.session_state["logged_in"] = True
        st.session_state["is_admin"] = True
        st.success("Authentication successful. Initializing Master Log...")
        st.switch_page("pages/3_Master_Log.py")
    else:
        st.error("Access Denied. Invalid credentials.")
        
st.markdown("</div>", unsafe_allow_html=True)