import streamlit as st
import os
import base64

# --- 1. PAGE CONFIG (Must be the very first Streamlit command) ---
st.set_page_config(page_title="Master Log", page_icon="📋", layout="wide")

# --- 2. STRICT SECURITY LOCK ---
# Kick out anyone who bypassed the login page entirely
if not st.session_state.get("logged_in", False):
    st.switch_page("0_Gatekeeper.py")

# Identify the user's role
is_admin = st.session_state.get("is_admin", False)

# --- 3. BASE64 WATERMARK ENCODER ---
# Safely converts your logo into a background text string
@st.cache_data
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

# Try 'assets/logo.png', fallback to 'logo.png'
logo_base64 = get_base64_image("assets/logo.png")
if not logo_base64:
    logo_base64 = get_base64_image("logo.png")

# --- 4. BRANDING & DASHBOARD STYLING ---
# Dynamically hide the sidebar if the user is a Staff member
sidebar_css = ""
if not is_admin:
    sidebar_css = """
    [data-testid="stSidebar"] {
        display: none !important;
    }
    """

st.markdown(f"""
    <style>
    /* Security: Apply Sidebar Restrictions */
    {sidebar_css}

    /* LAYER 1 & 2: The Pure White Canvas & The Orange Orbital Swirl */
    .stApp {{
        background-color: #FFFFFF;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1440 900' preserveAspectRatio='xMidYMid slice'%3E%3Cellipse cx='720' cy='450' rx='900' ry='300' transform='rotate(-20 720 450)' fill='none' stroke='%23FF6700' stroke-width='80' stroke-opacity='0.06' /%3E%3Cellipse cx='720' cy='450' rx='900' ry='300' transform='rotate(-20 720 450)' fill='none' stroke='%23FF6700' stroke-width='4' stroke-opacity='0.35' /%3E%3C/svg%3E");
        background-attachment: fixed;
        background-position: center;
        background-repeat: no-repeat;
        background-size: cover;
    }}
    
    /* LAYER 2.5: The 10% Logo Watermark */
    .watermark-container {{
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 500px;
        height: 500px;
        background-image: url("data:image/png;base64,{logo_base64}");
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center;
        opacity: 0.10;
        z-index: 0;
        pointer-events: none; /* Prevents the watermark from blocking mouse clicks */
    }}

    /* LAYER 3: The Floating Dashboard Container */
    .block-container {{
        background-color: #FFFFFF;
        padding: 40px !important;
        border-radius: 16px;
        box-shadow: 0px 15px 40px rgba(10, 34, 64, 0.08);
        border: 1px solid rgba(10, 34, 64, 0.05);
        margin-top: 40px;
        margin-bottom: 40px;
        z-index: 10;
        position: relative;
        max-width: 90% !important; /* Leaves room on the edges to see the orbit */
    }}
    </style>
    
    <div class="watermark-container"></div>
    """, unsafe_allow_html=True)


# --- 5. THE DASHBOARD CONTENT ---

# Page Header
st.markdown("<h1 style='color: #0A2240; margin-bottom: 0px;'>📋 Master Log</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #666666;'>Meridian 61 Logistics Tracking Array</p>", unsafe_allow_html=True)
st.divider()

# Security & Access Display
if is_admin:
    st.success("🟢 **Admin Connected:** Full Read/Write Access Enabled.")
    
    # What the Admin sees
    st.subheader("Admin Controls")
    st.file_uploader("Upload New Packing List or Commercial Invoice")
    
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Enter New Container Reference")
    with col2:
        st.write("") # Spacer to align the button
        st.write("")
        st.button("Save New Record", type="primary", use_container_width=True)

else:
    st.info("🔵 **Staff Connected:** Read-Only Mode Enforced.")
    
    # What the Staff sees
    st.subheader("Recent Logistics Data")
    st.write("*(Data grids and tracking tables will load here securely)*")
    st.button("Refresh Tracking Data")