import streamlit as st
import requests
import pandas as pd

API_BASE = "http://127.0.0.1:8000"  # your FastAPI backend

st.set_page_config(page_title="RBAC Dashboard", layout="wide")

# -----------------------------
# Helpers
# -----------------------------
def api_headers():
    token = st.session_state.get("token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}

def api_get(path, params=None):
    url = f"{API_BASE}{path}"
    r = requests.get(url, headers=api_headers(), params=params, timeout=20)
    return r

def api_post(path, data=None, json=None):
    url = f"{API_BASE}{path}"
    r = requests.post(url, headers=api_headers(), data=data, json=json, timeout=20)
    return r

def logout():
    st.session_state.pop("token", None)
    st.session_state.pop("me", None)
    st.session_state.pop("role", None)
    st.session_state.pop("username", None)
    st.success("Logged out.")
    st.rerun()

def fetch_me():
    r = api_get("/me")
    if r.status_code == 200:
        me = r.json()
        st.session_state["me"] = me
        st.session_state["role"] = me.get("role")
        st.session_state["username"] = me.get("username")
        return True
    return False

# -----------------------------
# Auth UI
# -----------------------------
def login_ui():
    st.title("🔐 RBAC Dashboard Login")

    with st.form("login_form"):
        username = st.text_input("Username", placeholder="admin / manager_sales / viewer_sales")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        if not username or not password:
            st.error("Please enter username and password.")
            return

        # OAuth2PasswordRequestForm expects form-urlencoded:
        payload = {"username": username, "password": password}

        r = requests.post(
            f"{API_BASE}/auth/login",
            data=payload,
            timeout=20,
        )

        if r.status_code != 200:
            st.error(f"Login failed: {r.text}")
            return

        token = r.json().get("access_token")
        st.session_state["token"] = token

        if fetch_me():
            st.success(f"Welcome, {st.session_state['username']} ({st.session_state['role']})")
            st.rerun()
        else:
            st.error("Login succeeded but /me failed. Check backend.")
            st.session_state.pop("token", None)

# -----------------------------
# Dashboard UI
# -----------------------------
def dashboard_ui():
    st.subheader("📊 Dashboard")

    me = st.session_state.get("me", {})
    role = st.session_state.get("role")
    dept = me.get("department")

    # Admin can choose department filter; others locked to their department by backend
    dept_filter = None
    if role == "admin":
        dept_filter = st.selectbox("Filter department (admin only)", ["(all)", "Sales", "IT"])
        if dept_filter == "(all)":
            dept_filter = None

    col1, col2 = st.columns([1, 1])

    # ---- KPIs ----
    with col1:
        st.markdown("### KPIs")
        params = {}
        if dept_filter:
            params["department"] = dept_filter

        r = api_get("/dashboard/kpis", params=params)
        if r.status_code != 200:
            st.error(f"Failed KPIs: {r.text}")
        else:
            kpis = r.json()
            if not kpis:
                st.info("No KPI data found.")
            else:
                for k in kpis:
                    st.metric(
                        label=k["metric_name"],
                        value=f'{k["total_value"]:.2f}',
                        help=f'avg={k["average_value"]:.2f} | count={k["count"]}'
                    )

    # ---- Chart ----
    with col2:
        st.markdown("### Chart")
        metric = st.selectbox("Choose metric", ["revenue", "orders", "tickets", "uptime"])
        params = {"metric": metric}
        if dept_filter:
            params["department"] = dept_filter

        r = api_get("/dashboard/chart", params=params)
        if r.status_code != 200:
            st.error(f"Failed chart: {r.text}")
        else:
            rows = r.json()
            if not rows:
                st.info("No chart data.")
            else:
                df = pd.DataFrame(rows)
                # Expect: date, value, metric_name, department
                if "date" in df.columns:
                    df["date"] = pd.to_datetime(df["date"])
                    df = df.sort_values("date")
                    st.line_chart(df.set_index("date")["value"])
                else:
                    st.write(df)

    # ---- Table ----
    st.markdown("### Records Table")
    params = {"limit": 100, "offset": 0}
    if dept_filter:
        params["department"] = dept_filter

    r = api_get("/dashboard/table", params=params)
    if r.status_code != 200:
        st.error(f"Failed table: {r.text}")
    else:
        df = pd.DataFrame(r.json())
        st.dataframe(df, use_container_width=True)

# -----------------------------
# Admin UI
# -----------------------------
def admin_users_ui():
    st.subheader("🛡️ Admin: Users")

    r = api_get("/admin/users")
    if r.status_code != 200:
        st.error(f"Failed /admin/users: {r.text}")
        return

    users = r.json()
    df = pd.DataFrame(users)
    st.dataframe(df, use_container_width=True)

    st.markdown("### Update a user's role/department")
    with st.form("update_user_form"):
        user_id = st.number_input("Target user_id", min_value=1, step=1)
        new_role = st.selectbox("New role", ["admin", "manager", "viewer"])
        new_dept = st.selectbox("New department (optional)", ["(none)", "Sales", "IT"])
        submitted = st.form_submit_button("Update user")

    if submitted:
        payload = {"role": new_role, "department": None if new_dept == "(none)" else new_dept}
        rr = requests.patch(
            f"{API_BASE}/admin/users/{int(user_id)}",
            headers=api_headers(),
            json=payload,
            timeout=20
        )
        if rr.status_code == 200:
            st.success("User updated!")
            st.rerun()
        else:
            st.error(f"Update failed: {rr.text}")

def admin_audit_ui():
    st.subheader("🧾 Admin: Audit Logs")

    r = api_get("/admin/audit-logs")
    if r.status_code != 200:
        st.error(f"Failed /admin/audit-logs: {r.text}")
        return

    logs = r.json()
    df = pd.DataFrame(logs)
    st.dataframe(df, use_container_width=True)

# -----------------------------
# App Router
# -----------------------------
def app_ui():
    st.sidebar.title("RBAC Dashboard")
    st.sidebar.write(f"👤 {st.session_state.get('username')} ({st.session_state.get('role')})")

    if st.sidebar.button("Logout"):
        logout()

    role = st.session_state.get("role")

    menu = ["Dashboard"]
    if role == "admin":
        menu += ["Admin - Users", "Admin - Audit Logs"]

    choice = st.sidebar.radio("Navigation", menu)

    if choice == "Dashboard":
        dashboard_ui()
    elif choice == "Admin - Users":
        admin_users_ui()
    elif choice == "Admin - Audit Logs":
        admin_audit_ui()

# -----------------------------
# Main
# -----------------------------
token = st.session_state.get("token")
if not token:
    login_ui()
else:
    # ensure /me is loaded
    if not st.session_state.get("me"):
        if not fetch_me():
            st.error("Session expired. Please login again.")
            logout()
    app_ui()