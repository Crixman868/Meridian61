import streamlit as st

st.set_page_config(page_title="Meridian Gatekeeper", page_icon="🔐")

# 1. Initialize State
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# 2. Logout Logic (Optional - add a logout button in your other pages)
if st.sidebar.button("Logout"):
    st.session_state["logged_in"] = False
    st.rerun()

# 3. If NOT logged in, show Gatekeeper
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
            st.session_state["is_admin"] = (users[username].get("role") == "admin")
            st.rerun()
        else:
            st.error("Invalid credentials.")
    st.stop() # Prevents anything below from loading

# 4. If we reach here, they are logged in. 
# Instead of switching pages, we just run the app content.
# This forces the app to stay in one memory block.
import pages.1_Master_Tracker as app 
app.main()