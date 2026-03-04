import streamlit as st
import pandas as pd
from utils import APIClient, check_auth, inject_custom_css

st.set_page_config(page_title="Admin - RBAC", page_icon="🛡️", layout="wide")
inject_custom_css()

def admin_page():
    if not check_auth():
        st.stop()

    me = st.session_state["me"]
    if me.get("role") != "admin":
        st.error("🚫 Access Denied: Administrator privileges required.")
        st.stop()

    st.title("🛡️ Administrator Dashboard")

    tab1, tab2 = st.tabs(["👥 User Management", "🧾 Audit Logs"])

    with tab1:
        st.subheader("Current Registered Users")
        users_resp = APIClient.get("/admin/users")
        if users_resp and users_resp.status_code == 200:
            users_list = users_resp.json()
            if users_list:
                df_users = pd.DataFrame(users_list)
                # Select only relevant columns for display
                cols_to_show = ["id", "username", "role", "department", "is_active", "created_at"]
                st.dataframe(df_users[cols_to_show], use_container_width=True, hide_index=True)
                
                st.divider()
                
                st.subheader("Edit User Permissions")
                with st.form("edit_user_form"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        target_id = st.number_input("User ID", min_value=1, step=1)
                    with col2:
                        new_role = st.selectbox("Assign New Role", ["admin", "manager", "viewer"])
                    with col3:
                        new_dept = st.selectbox("Assign Department", ["(None)", "Sales", "IT"])
                    
                    submitted = st.form_submit_button("Update User Profile", use_container_width=True)

                if submitted:
                    payload = {
                        "role": new_role,
                        "department": None if new_dept == "(None)" else new_dept
                    }
                    update_resp = APIClient.patch(f"/admin/users/{target_id}", json=payload)
                    if update_resp and update_resp.status_code == 200:
                        st.success(f"User #{target_id} updated successfully!")
                        st.rerun()
                    else:
                        st.error(f"Failed to update user: {update_resp.text}")
            else:
                st.info("No users found.")
        else:
            st.error("Could not fetch user list.")

    with tab2:
        st.subheader("System Audit Logs")
        logs_resp = APIClient.get("/admin/audit-logs")
        if logs_resp and logs_resp.status_code == 200:
            logs = logs_resp.json()
            if logs:
                df_logs = pd.DataFrame(logs)
                # Format timestamp
                df_logs['timestamp'] = pd.to_datetime(df_logs['timestamp'])
                df_logs = df_logs.sort_values(by="timestamp", ascending=False)
                
                # Search feature
                search_query = st.text_input("Search Logs (Action, User ID, etc.)", placeholder="e.g., LOGIN")
                if search_query:
                    # Filter across all string columns
                    mask = df_logs.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)
                    df_logs = df_logs[mask]

                st.dataframe(df_logs, use_container_width=True, hide_index=True)
                
                csv = df_logs.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Export Logs to CSV",
                    data=csv,
                    file_name='audit_logs.csv',
                    mime='text/csv',
                )
            else:
                st.info("No audit logs recorded yet.")
        else:
            st.error("Audit log retrieval failed.")

if __name__ == "__main__":
    admin_page()
