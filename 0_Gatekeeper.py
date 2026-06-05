import streamlit as st
import time
import json

st.set_page_config(page_title="Meridian Gatekeeper", page_icon="🔐")

# Initialize session states as fallback layers
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False

# --- NATIVE JAVASCRIPT COOKIE MANAGEMENT ---
# Using st.iframe to fulfill the latest framework requirements
cookie_js = """
<script>
    function getCookie(name) {
        let match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
        if (match) return match[2];
        return null;
    }
    
    // Periodically post cookie data back to Streamlit app backend
    setInterval(function() {
        const sessionCookie = getCookie('meridian_session');
        if (sessionCookie) {
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: decodeURIComponent(sessionCookie)
            }, '*');
        }
    }, 300);
</script>
"""
# Encapsulated in iframe as required by the latest update
cookie_receiver = st.iframe(srcdoc=cookie_js, height=0, width=0)

# Process incoming session data from browser cookie payload if found
if cookie_receiver:
    try:
        session_data = json.loads(cookie_receiver)
        if session_data.get("auth") == "approved":
            st.session_state["logged_in"] = True
            st.session_state["is_admin"] = (session_data.get("role") == "admin")
            st.success("Secure Session Restored! Redirecting...")
            time.sleep(0.5)
            st.switch_page("pages/1_Master_Tracker.py")
            st.stop()
    except Exception:
        pass

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
    except Exception:
        st.error("System Error: Your [users] secrets block is misconfigured.")
        st.stop()
        
    if valid_login:
        st.success("Authentication accepted. Securely baking 30-day session...")
        
        session_payload = {"auth": "approved", "role": "admin" if is_admin else "staff"}
        cookie_string = json.dumps(session_payload)
        
        # JS to write cookie in browser memory explicitly
        js_writer = f"""
        <script>
            document.cookie = "meridian_session=" + encodeURIComponent('{cookie_string}') + "; max-age=2592000; path=/; SameSite=Strict";
        </script>
        """
        st.iframe(srcdoc=js_writer, height=0, width=0)
        
        st.session_state["logged_in"] = True
        st.session_state["is_admin"] = is_admin
        
        time.sleep(1)
        st.rerun()
    else:
        st.error("🚨 Invalid username or password.")