import streamlit as st
import requests
from utils import API_BASE, fetch_me, inject_custom_css

st.set_page_config(page_title="Login - RBAC Dashboard", page_icon="🔐")
inject_custom_css()

def login_page():
    st.title("🔐 Login")
    st.markdown("Enter your credentials to access the RBAC Dashboard.")

    # Using a container for a centered look
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", placeholder="e.g., admin")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("Please provide both username and password.")
            else:
                try:
                    # FastAPI OAuth2PasswordRequestForm expects data as form-urlencoded
                    payload = {"username": username, "password": password}
                    response = requests.post(f"{API_BASE}/auth/login", data=payload, timeout=20)
                    
                    if response.status_code == 200:
                        token_data = response.json()
                        st.session_state["token"] = token_data.get("access_token")
                        
                        if fetch_me():
                            st.success(f"Successfully logged in as {st.session_state['username']}!")
                            st.balloons()
                            # Short delay before switching
                            st.rerun()
                        else:
                            st.error("Authentication succeeded, but failed to fetch user profile.")
                    else:
                        st.error(f"Login failed: {response.json().get('detail', 'Unknown error')}")
                except Exception as e:
                    st.error(f"An error occurred during login: {str(e)}")

    # Display some demo accounts if useful for the user
    with st.expander("Demo Accounts (Click to view)"):
        st.code("""
admin / adminpassword
manager_sales / managerpassword
viewer_sales / viewerpassword
manager_it / managerpassword
        """)

if __name__ == "__main__":
    login_page()
