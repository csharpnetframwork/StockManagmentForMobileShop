import streamlit as st
from db import init_db
init_db()  # ensures tables & seed admin if empty

from auth import require_login
from pages import dashboard, sales, inventory, emi_tracker, bill_scan, users as users_page

st.set_page_config(
    page_title="Mobile Shop Management",
    layout="wide",
    initial_sidebar_state="expanded",
)

user = require_login()

st.sidebar.markdown(f"**Logged in:** {user['username']} ({user['role']})")
nav = ["Dashboard", "New Sale", "Inventory", "EMI Tracker", "Bill Scan"]
if user['role'] == 'admin':
    nav.append("Users")
page = st.sidebar.radio("Go to", nav)

if st.sidebar.button("Logout"):
    st.session_state["user"] = None
    st.rerun()

if page == "Dashboard":
    dashboard.app()
elif page == "New Sale":
    sales.app()
elif page == "Inventory":
    inventory.app()
elif page == "EMI Tracker":
    emi_tracker.app()
elif page == "Bill Scan":
    bill_scan.app()
elif page == "Users":
    users_page.app()
else:
    st.error("Unknown page.")
