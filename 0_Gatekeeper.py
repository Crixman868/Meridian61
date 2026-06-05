import streamlit as st

# --- PAGE CONFIG ---
st.set_page_config(page_title="Meridian 61 Access", page_icon="🌐")

# --- BRANDING & STYLING ---
st.markdown("""
    <style>
    /* Deep Navy Page Background */
    .stApp {
        background-color: #0A2240;
    }
    
    /* White Card Styling */
    .login-card {
        background-color: white;
        padding: 40px;
        border-radius: 20px;
        box-shadow: 0px 10px 30px rgba(0,0,0,0.3);
        max-width: 400px;
        margin: 0 auto;
    }
    
    /* Vibrant Orange Button */
    div.stButton > button {
        background-color: #FF6700 !important;
        color: white !important;
        border: none !important;
        font-weight: bold !important;
        width: 100% !important;
        border-radius: 10px !important;
        height: 50px !important;
    }
    
    /* Centering the logo container */
    .logo-container {
        display: flex;
        justify-content: center;
        margin-bottom: 30px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- LOGO SECTION ---
st.markdown("<div class='logo-container'>", unsafe_allow_html=True)
# App will now look in your 'assets' folder for the logo
st.image("assets/logo.png", width=300)
st.markdown("</div>", unsafe_allow_html=True)

# --- LOGIN FORM ---
st.markdown("<div class='login-card'>", unsafe_allow_html=True)
st.subheader("Login to Meridian 61")
st.write("Enter your credentials to access the Master Log.")

user = st.text_input("Username")
password = st.text_input("Password", type="password")

if st.button("Enter Portal"):
    # Replace with your actual secure authentication logic
    if user == "Admin" and password == "Majestic2026": 
        st.session_state["logged_in"] = True
        st.session_state["is_admin"] = True
        st.success("Welcome, AllRounder. Redirecting...")
        st.switch_page("pages/3_Master_Log.py")
    else:
        st.error("Invalid credentials.")
        
st.markdown("</div>", unsafe_allow_html=True)