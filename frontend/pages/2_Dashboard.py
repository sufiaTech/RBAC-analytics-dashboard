import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from utils import APIClient, check_auth, inject_custom_css

st.set_page_config(page_title="Dashboard - RBAC", page_icon="📊", layout="wide")
inject_custom_css()

def dashboard_page():
    if not check_auth():
        st.stop()

    st.title("📊 RBAC Insights Dashboard")
    
    me = st.session_state["me"]
    role = me.get("role")
    user_dept = me.get("department")

    # --- Sidebar Filters ---
    st.sidebar.title("Filters")
    
    # Department filtering logic
    dept_options = ["(All)"]
    if role == "admin":
        dept_options = ["(All)", "Sales", "IT"]
    elif user_dept:
        dept_options = [user_dept]
    
    selected_dept = st.sidebar.selectbox("Department", dept_options)
    dept_filter = None if selected_dept == "(All)" else selected_dept

    # Date Range Filter
    today = datetime.now().date()
    last_30_days = today - timedelta(days=30)
    date_range = st.sidebar.date_input("Date Range", value=(last_30_days, today))
    
    start_date, end_date = None, None
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range

    # --- Data Fetching ---
    params = {}
    if dept_filter: params["department"] = dept_filter
    if start_date: params["start_date"] = start_date.isoformat()
    if end_date: params["end_date"] = end_date.isoformat()

    # --- KPI Row ---
    st.subheader("Key Performance Indicators")
    kpi_resp = APIClient.get("/dashboard/kpis", params=params)
    if kpi_resp and kpi_resp.status_code == 200:
        kpis = kpi_resp.json()
        if kpis:
            cols = st.columns(len(kpis))
            for i, k in enumerate(kpis):
                with cols[i]:
                    st.metric(
                        label=k["metric_name"].capitalize(),
                        value=f"{k['total_value']:,.2f}",
                        delta=f"Avg: {k['average_value']:,.1f}"
                    )
        else:
            st.info("No KPI data available for this selection.")
    else:
        st.error("Could not fetch KPI data.")

    st.divider()

    # --- Chart & Table Row ---
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Trend Analysis")
        metric_to_chart = st.selectbox("Select Metric to Chart", ["revenue", "orders", "tickets", "uptime"])
        
        chart_params = params.copy()
        chart_params["metric"] = metric_to_chart
        
        chart_resp = APIClient.get("/dashboard/chart", params=chart_params)
        if chart_resp and chart_resp.status_code == 200:
            chart_data = chart_resp.json()
            if chart_data:
                df_chart = pd.DataFrame(chart_data)
                df_chart['date'] = pd.to_datetime(df_chart['date'])
                df_chart = df_chart.sort_values('date')
                
                fig = px.line(df_chart, x='date', y='value', color='department',
                             title=f"{metric_to_chart.capitalize()} over Time",
                             labels={"value": "Value", "date": "Date"})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No trend data available.")
        else:
            st.error("Failed to load chart data.")

    with col2:
        st.subheader("Data Summary")
        if 'df_chart' in locals() and not df_chart.empty:
            summary = df_chart.groupby('department')['value'].agg(['sum', 'mean', 'count']).reset_index()
            st.dataframe(summary, hide_index=True, use_container_width=True)
        else:
            st.write("Statistics will appear when data is loaded.")

    st.divider()

    # --- Full Data Table ---
    st.subheader("Detailed Records")
    table_resp = APIClient.get("/dashboard/table", params=params)
    if table_resp and table_resp.status_code == 200:
        table_data = table_resp.json()
        if table_data:
            df_table = pd.DataFrame(table_data)
            st.dataframe(df_table, use_container_width=True)
            
            # Export functionality
            csv = df_table.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Data as CSV",
                data=csv,
                file_name='dashboard_data.csv',
                mime='text/csv',
            )
        else:
            st.info("No records found.")
    else:
        st.error("Could not fetch table data.")

if __name__ == "__main__":
    dashboard_page()
