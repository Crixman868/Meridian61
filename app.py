import streamlit as st

st.set_page_config(page_title="Meridian Logistics", page_icon="🔐")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# 1. LOGIN LOGIC
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
    # 2. REDIRECT SCREEN
    st.success("Authentication successful!")
    st.write("Please use the sidebar on the left to navigate to your workspace.")
    
    # Simple Logout
    if st.sidebar.button("Logout"):
        st.session_state["logged_in"] = False
        st.rerun()