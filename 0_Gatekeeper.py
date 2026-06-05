import streamlit as st

# --- CONFIG ---
st.set_page_config(page_title="Meridian 61 Access", page_icon="🌐")

# --- BRANDING & STYLING ---
st.markdown("""
    <style>
    /* Dark Navy Background for the Page */
    .stApp {
        background-color: #0A2240;
    }
    /* Floating White Card for the Login Form */
    .login-card {
        background-color: white;
        padding: 40px;
        border-radius: 20px;
        box-shadow: 0px 10px 30px rgba(0,0,0,0.3);
    }
    /* Custom Orange Button */
    div.stButton > button {
        background-color: #FF6700 !important;
        color: white !important;
        border: none !important;
        font-weight: bold !important;
        width: 100% !important;
        border-radius: 10px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- LOGO & LOGIN INTERFACE ---
# Ensure you have your logo file in a 'logos' folder or current directory
st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
st.image("Meridian 61 Logistics Ltd..png", width=300)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='login-card'>", unsafe_allow_html=True)
st.subheader("Login to Meridian 61")
st.write("Enter your credentials to access the Master Log.")

user = st.text_input("Username")
password = st.text_input("Password", type="password")

if st.button("Enter Portal"):
    if user == "Admin" and password == "Majestic2026": # Replace with your secure logic
        st.session_state["logged_in"] = True
        st.session_state["is_admin"] = True
        st.success("Welcome, AllRounder. Redirecting...")
        st.switch_page("pages/3_Master_Log.py")
    else:
        st.error("Invalid credentials.")
        
st.markdown("</div>", unsafe_allow_html=True)