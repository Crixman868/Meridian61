import streamlit as st

st.set_page_config(page_title="Meridian Logistics", page_icon="🔐")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    st.title("🔐 Meridian Logistics Gatekeeper")
    with st.form("login"):
        username = st.text_input("Username").strip().lower()
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Access System"):
            users = st.secrets.get("users", {})
            if username in users and users[username].get("password") == password:
                st.session_state["logged_in"] = True
                st.session_state["role"] = users[username].get("role")
                st.rerun()
            else:
                st.error("Invalid credentials.")
else:
    # Router: Use st.switch_page for the pages folder
    if st.session_state.get("role") == "admin":
        st.switch_page("pages/tracker_app.py")
    else:
        st.switch_page("pages/master_log.py")