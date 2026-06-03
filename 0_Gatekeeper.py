import streamlit as st
import json
from google.oauth2 import service_account

# 1. SETUP THE FRONT DOOR
st.set_page_config(page_title="Meridian 61", page_icon="🔐")

# 2. CONNECT THE GOOGLE ROBOT TO THE VAULT
def get_google_creds():
    creds_dict = json.loads(st.secrets["google_api"]["credentials"])
    return service_account.Credentials.from_service_account_info(creds_dict)

# 3. LOGIN LOGIC (Your Front Door)
def check_password():
    """Returns True if the user has the correct password."""
    def password_entered():
        # Changed variable to 'logged_in' for consistency across pages
        if st.session_state["password"] == "Cocosteaw868": 
            st.session_state["logged_in"] = True
            del st.session_state["password"]
        else:
            st.session_state["logged_in"] = False

    if "logged_in" not in st.session_state:
        # Show login screen
        st.title("Meridian 61 Logistics")
        st.subheader("Secure Gateway")
        st.text_input("Secure Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["logged_in"]:
        # Show error if wrong
        st.error("😕 Password incorrect")
        st.text_input("Secure Password", type="password", on_change=password_entered, key="password")
        return False
    else:
        # Password is correct!
        return True

# 4. LET THEM IN
if check_password():
    # If login works, the robot gets the keys from the vault
    creds = get_google_creds()
    
    st.success("Welcome, Authorized User!")
    st.write("You are now in the system. Use the sidebar to track shipments.")