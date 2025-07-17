import streamlit as st
from db import SessionLocal, get_user_by_username, verify_password

def login_form():
    st.sidebar.subheader("Login")
    username = st.sidebar.text_input("Username", key="login_username")
    password = st.sidebar.text_input("Password", type="password", key="login_password")
    login_btn = st.sidebar.button("Login", type="primary")

    if login_btn:
        session = SessionLocal()
        user = get_user_by_username(username, session)
        session.close()
        if user and verify_password(user, password):
            st.session_state["user"] = {
                "username": user.username,
                "role": user.role,
                "full_name": user.full_name,
                "id": user.id
            }
            st.sidebar.success(f"Logged in as {user.username} ({user.role})")
            st.rerun()
        else:
            st.sidebar.error("Invalid username or password.")

def require_login():
    if "user" not in st.session_state or st.session_state["user"] is None:
        login_form()
        st.stop()
    return st.session_state["user"]

def require_role(roles):
    user = require_login()
    if user["role"] not in roles:
        st.error("You do not have permission to view this page.")
        st.stop()
    return user
