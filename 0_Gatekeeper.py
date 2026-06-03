import streamlit as st

st.set_page_config(page_title="Meridian 61 - Login", page_icon="🧭", layout="centered")

st.title("🧭 Meridian 61 Logistics")
st.subheader("Secure Gateway")
st.write("---") 

# 1. Turn on the computer's memory for both login status AND their specific role
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["role"] = None  # NEW: Blank nametag to start

# 2. Login Logic
if st.session_state["logged_in"] == False:
    username = st.text_input("Authorized Username")
    password = st.text_input("Secure Password", type="password")

    if st.button("Secure Launch"):
        # YOUR ACCOUNT (Master Control)
        if username == "admin" and password == "meridian":
            st.session_state["logged_in"] = True
            st.session_state["role"] = "admin"
            st.rerun()
            
        # STAFF ACCOUNT (Customs Submissions)
        elif username == "staff" and password == "customs":
            st.session_state["logged_in"] = True
            st.session_state["role"] = "staff"
            st.rerun()
            
        # CLIENT ACCOUNT (Read-Only)
        elif username == "client" and password == "viewonly":
            st.session_state["logged_in"] = True
            st.session_state["role"] = "client"
            st.rerun()
            
        else:
            st.error("Access Denied. Incorrect credentials.")

# 3. Welcome Screen
if st.session_state["logged_in"] == True:
    # Notice how this now greets you by your specific role!
    st.success(f"Access Granted! You are securely connected as: {st.session_state['role'].upper()}")
    st.info("👈 Please select a workspace from the sidebar to begin.")
    
    if st.button("Secure Log Out"):
        st.session_state["logged_in"] = False
        st.session_state["role"] = None
        st.rerun()