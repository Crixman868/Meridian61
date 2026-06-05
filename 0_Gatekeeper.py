import streamlit as st
import extra_streamlit_components as stx
import time
import json

st.set_page_config(page_title="Meridian Gatekeeper", page_icon="🔐")

# --- THE COOKIE ENGINE ---
cookie_manager = stx.CookieManager()

# Give the browser a split-second to send the cookies to the server
time.sleep(0.2)

# Check for our unified 30-day session cookie
cached_session = cookie_manager.get(cookie="meridian_session")

if cached_session:
    try:
        # Parse our combined cookie data safely
        session_data = json.loads(cached_session) if isinstance(cached_session, str) else cached_session
        if session_data.get("auth") == "approved":
            st.session_state["logged_in"] = True
            st.session_state["is_admin"] = (session_data.get("role") == "admin")
            st.success("Secure Session Restored! Redirecting...")
            time.sleep(0.5)
            st.switch_page("pages/1_Master_Tracker.py")
            st.stop()
    except Exception:
        pass # If cookie data is corrupted, just let them log in normally

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
        st.success("Authentication accepted. Baking 30-Day security session vault...")
        
        # FIX: Combine all info into a single package so we only execute .set() exactly once!
        session_payload = {
            "auth": "approved",
            "role": "admin" if is_admin else "staff"
        }
        
        # Serialize payload to string format for cookie storage
        cookie_manager.set(
            cookie="meridian_session", 
            val=json.dumps(session_payload), 
            max_age=2592000
        )
        
        # Set short-term memory session state as a backup layer
        st.session_state["logged_in"] = True
        st.session_state["is_admin"] = is_admin
        
        time.sleep(1)
        st.rerun()
    else:
        st.error("🚨 Invalid username or password.")