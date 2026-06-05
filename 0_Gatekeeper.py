import streamlit as st
import time
import hashlib

st.set_page_config(page_title="Meridian Gatekeeper", page_icon="🔐")

# --- THE NATIVE QUERY PARAM ENGINE ---
# Instead of cookies, we check the URL for a persistent 'auth_token'
params = st.query_params
auth_token = params.get("auth_token")

# Verify token against a secret hash to prevent people from faking the URL
SECRET_SALT = "meridian_secure_2026"

def generate_token(username, role):
    raw = f"{username}:{role}:{SECRET_SALT}"
    return hashlib.sha256(raw.encode()).hexdigest()

# Validate existing token if present
if auth_token:
    users_secrets = st.secrets.get("users", {})
    for user, data in users_secrets.items():
        if generate_token(user, data["role"]) == auth_token:
            st.session_state["logged_in"] = True
            st.session_state["is_admin"] = (data["role"] == "admin")
            st.success("Session Restored!")
            st.switch_page("pages/1_Master_Tracker.py")
            st.stop()

# --- LOGIN UI ---
st.title("🔐 Meridian Logistics Gatekeeper")
with st.form("login_form"):
    username = st.text_input("Username").strip().lower()
    password = st.text_input("Password", type="password")
    submit = st.form_submit_button("Access System")

if submit:
    users_secrets = st.secrets.get("users", {})
    if username in users_secrets and users_secrets[username].get("password") == password:
        role = users_secrets[username]["role"]
        token = generate_token(username, role)
        
        # Save session and redirect to URL with the secret token attached
        st.session_state["logged_in"] = True
        st.session_state["is_admin"] = (role == "admin")
        
        # This forces the browser to remember the user via the URL
        st.query_params["auth_token"] = token
        st.rerun()
    else:
        st.error("🚨 Invalid username or password.")