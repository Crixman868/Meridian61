import streamlit as st

st.set_page_config(page_title="Meridian Logistics", page_icon="🔐")

# --- LOGIN LOGIC ---
st.title("🔐 Meridian Logistics Gatekeeper")
with st.form("login_form"):
    username = st.text_input("Username").strip().lower()
    password = st.text_input("Password", type="password")
    submit = st.form_submit_button("Access System")

if submit:
    users = st.secrets.get("users", {})
    if username in users and users[username].get("password") == password:
        # Save login status and role in URL parameters
        st.query_params["logged_in"] = "true"
        st.query_params["role"] = users[username].get("role")
        
        # Route based on role
        if users[username].get("role") == "admin":
            st.switch_page("pages/tracker_app.py")
        else:
            st.switch_page("pages/master_log.py")
    else:
        st.error("Invalid credentials.")