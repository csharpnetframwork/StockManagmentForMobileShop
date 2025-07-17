import streamlit as st
from passlib.hash import bcrypt
from auth import require_role
from db import SessionLocal, User
import pandas as pd

def create_user(session, username, password, role="employee", full_name=None, email=None):
    u = User(
        username=username,
        password_hash=bcrypt.hash(password),
        role=role,
        full_name=full_name or username,
        email=email,
        active=True,
    )
    session.add(u)
    session.commit()
    session.refresh(u)
    return u

def app():
    user = require_role(["admin"])
    st.title("User Management")

    session = SessionLocal()

    with st.expander("Add User"):
        username = st.text_input("Username")
        full_name = st.text_input("Full Name")
        email = st.text_input("Email")
        role = st.selectbox("Role", ["owner","admin","employee"])
        pw1 = st.text_input("Password", type="password")
        pw2 = st.text_input("Confirm Password", type="password")
        if st.button("Create User", type="primary"):
            if not username or not pw1:
                st.error("Username & password required.")
            elif pw1 != pw2:
                st.error("Passwords do not match.")
            else:
                existing = session.query(User).filter(User.username==username).first()
                if existing:
                    st.error("Username already exists.")
                else:
                    create_user(session, username=username, password=pw1, role=role, full_name=full_name, email=email)
                    st.success(f"User '{username}' created.")
                    st.rerun()

    users = session.query(User).order_by(User.id).all()
    df = pd.DataFrame([{
        "ID": u.id,
        "Username": u.username,
        "Role": u.role,
        "Email": u.email,
        "Active": u.active
    } for u in users])
    st.dataframe(df, use_container_width=True)

    session.close()
