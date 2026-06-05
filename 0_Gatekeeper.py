import streamlit as st
import extra_streamlit_components as stx
import time

st.set_page_config(page_title="Meridian Gatekeeper", page_icon="🔐")

# --- THE COOKIE ENGINE ---
# Initialized directly to comply with Streamlit's updated widget rules
cookie_manager = stx.CookieManager()

# Give the browser a split-second to send the cookies to the server
time.sleep(0.1)

# Check for existing 30-day session cookies
cached_auth = cookie_manager.get(cookie="meridian_auth")
cached_role = cookie_manager.get(cookie="meridian_role")

if cached_auth == "approved":
    st.session_state["logged_in"] = True
    st.session_state["is_admin"] = (cached_role == "admin")
    st.success("Secure Session Restored! Redirecting...")
    time.sleep(0.5)
    st.switch_page("pages/1_Master_Tracker.py")
    st.stop()

# --- LOGIN UI ---
st.title("🔐 Meridian Logistics Gatekeeper")
st.markdown("Please authenticate to enter the Command Console.")

with st.form("login_form"):
    username = st.text_input("Username").strip().lower()
    password = st.text_input("Password", type="password")
    submit = st.form_submit_button("Access System")

if submit:
    valid_login = False
    is_admin = False
    
    # --- PASSWORD VERIFICATION ---
    # This assumes your Streamlit Secrets has a [passwords] section
    try:
        secrets = st.secrets["passwords"]
        if username in secrets and secrets[username] == password:
            valid_login = True
            
            # Identify if the user is an Admin (like 'allrounder' or 'admin')
            if username in ["admin", "allrounder", "crixman"]: 
                is_admin = True
    except KeyError:
        st.error("System Error: [passwords] block missing from Streamlit Secrets.")
        st.stop()
        
    if valid_login:
        st.success("Authentication accepted. Baking 30-Day security cookies...")
        
        # SET COOKIES (2,592,000 seconds = 30 Days)
        cookie_manager.set("meridian_auth", "approved", max_age=2592000)
        cookie_manager.set("meridian_role", "admin" if is_admin else "staff", max_age=2592000)
        
        # Set short-term memory as a backup
        st.session_state["logged_in"] = True
        st.session_state["is_admin"] = is_admin
        
        time.sleep(1)
        st.rerun()
    else:
        st.error("🚨 Invalid username or password.")