import streamlit as st

st.set_page_config(page_title="Meridian61 Portal", page_icon="🔐", layout="centered")

# --- 1. THE BOUNCER (Authentication Logic) ---
def login():
    st.title("🔐 Meridian61 Secure Portal")
    st.markdown("Enter your credentials to access the logistics network.")

    with st.form("login_form"):
        # Automatically converts usernames to lowercase to prevent case-sensitive typos
        username = st.text_input("Username").strip().lower()
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Authenticate")

        if submitted:
            # Check if the user exists in our Secrets Vault
            if "users" in st.secrets and username in st.secrets["users"]:
                stored_password = st.secrets["users"][username]["password"]
                role = st.secrets["users"][username]["role"]

                if password == stored_password:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = username
                    # Silently tag the user's permission level based on the TOML file
                    st.session_state["is_admin"] = (role == "admin") 
                    st.rerun()
                else:
                    st.error("Invalid password.")
            else:
                st.error("User not found.")

# --- 2. THE INVISIBLE DOOR (Dynamic Routing) ---
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    login()
else:
    # Map the physical files to the router
    # Note: Ensure these paths exactly match the filenames in your 'pages' folder
    master_log = st.Page("pages/2_Master_Log.py", title="Master Log", icon="🗄️")
    master_tracker = st.Page("pages/1_Master_Tracker.py", title="Master Tracker", icon="📦")

    # If Admin (AllRounder): Show both pages. If Staff (Elton/Smallman): Show ONLY the Master Log.
    if st.session_state.get("is_admin", False):
        pg = st.navigation([master_log, master_tracker])
    else:
        pg = st.navigation([master_log])

    # Sidebar profile and logout
    with st.sidebar:
        # Capitalizes the username for a clean display (e.g., "Allrounder", "Elton")
        st.markdown(f"👤 **User:** {st.session_state['username'].title()}")
        st.markdown(f"🛡️ **Role:** {'Administrator' if st.session_state['is_admin'] else 'Staff Operations'}")
        st.write("---")
        if st.button("Log Out", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # Execute the allowed navigation
    pg.run()