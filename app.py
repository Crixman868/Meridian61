import streamlit as st
import pages.tracker_app as tracker_app
import pages.master_log as master_log

# Initialize State
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# 3. Gatekeeper Logic
if not st.session_state["logged_in"]:
    st.title("🔐 Meridian Logistics Gatekeeper")
    with st.form("login_form"):
        username = st.text_input("Username").strip().lower()
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Access System")
    
    if submit:
        users = st.secrets.get("users", {})
        if username in users and users[username].get("password") == password:
            st.session_state["logged_in"] = True
            st.session_state["role"] = users[username].get("role")
            st.rerun()
        else:
            st.error("Invalid credentials.")
else:
    # Traffic Cop: Send Admin to Tracker, Shopfloor to Log
    if st.session_state.get("role") == "admin":
        tracker_app.main()
    else:
        master_log.main()