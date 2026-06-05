import streamlit as st

st.set_page_config(page_title="Meridian Logistics", page_icon="🔐")

# 1. Check if already logged in via URL
if st.query_params.get("auth") == "yes":
    st.session_state["logged_in"] = True
    st.session_state["role"] = st.query_params.get("role")

# 2. Login Form
if not st.session_state.get("logged_in", False):
    st.title("🔐 Meridian Logistics Gatekeeper")
    with st.form("login"):
        username = st.text_input("Username").strip().lower()
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Access"):
            users = st.secrets.get("users", {})
            if username in users and users[username].get("password") == password:
                # Set session and URL parameters to "stick" the login
                role = users[username].get("role")
                st.query_params["auth"] = "yes"
                st.query_params["role"] = role
                st.session_state["logged_in"] = True
                st.session_state["role"] = role
                st.rerun()
            else:
                st.error("Invalid credentials.")
else:
    # 3. Navigation (Do NOT use switch_page, use page_link)
    st.success("Authenticated.")
    if st.session_state.get("role") == "admin":
        st.page_link("pages/tracker_app.py", label="📦 Go to Master Tracker")
    else:
        st.page_link("pages/master_log.py", label="📋 Go to Master Log")