import streamlit as st
import extra_streamlit_components as stx
import time

st.set_page_config(page_title="Meridian Gatekeeper", page_icon="🔐")

# --- THE COOKIE ENGINE ---
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
    
    # --- DYNAMIC PASSWORDS MATCH ENGINE ---
    try:
        users_secrets = st.secrets["users"]
        
        if username in users_secrets:
            user_data = users_secrets[username]
            
            if user_data.get("password") == password:
                valid_login = True
                if user_data.get("role") == "admin":
                    is_admin = True
    except Exception as err:
        st.error("System Error: Your [users] secrets block format is missing or misconfigured.")
        st.stop()
        
    if valid_login:
        st.success("Authentication accepted. Baking 30-Day security cookies...")
        
        # FIX: Added unique custom element keys manually to prevent inner component naming collisions
        cookie_manager.set("meridian_auth", "approved", max_age=2592000, key="set_cookie_auth")
        cookie_manager.set("meridian_role", "admin" if is_admin else "staff", max_age=2592000, key="set_cookie_role")
        
        # Set short-term memory session state as a backup layer
        st.session_state["logged_in"] = True
        st.session_state["is_admin"] = is_admin
        
        time.sleep(1)
        st.rerun()
    else:
        st.error("🚨 Invalid username or password.")