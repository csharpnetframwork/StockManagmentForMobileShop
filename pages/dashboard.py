import streamlit as st
import pandas as pd
from datetime import datetime
from auth import require_login
from db import SessionLocal
from utils.dates import today_range_ist, IST
from utils.db_helpers import get_stock_summary, get_sales_summary, get_top_sellers

def app():
    user = require_login()
    st.title("Dashboard")

    today_start, _ = today_range_ist()
    dr = st.date_input("Date Range", (today_start.date(), today_start.date()))
    if isinstance(dr, tuple):
        start_date, end_date = dr
    else:
        start_date = end_date = dr

    start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=IST)
    end_dt = datetime.combine(end_date, datetime.min.time(), tzinfo=IST) + pd.Timedelta(days=1)

    session = SessionLocal()
    units, value = get_stock_summary(session)
    total, cash, emi = get_sales_summary(session, start_dt, end_dt)

    c1, c2, c3 = st.columns(3)
    c1.metric("Units in Stock", units)
    c2.metric("Stock Value (₹)", f"{value:,.2f}")
    if user['role'] == 'admin':
        c3.metric("Revenue (₹)", f"{total:,.2f}")
    else:
        c3.metric("Revenue (₹)", "—")

    if user['role'] == 'admin':
        st.subheader("Cash vs EMI")
        st.bar_chart(pd.DataFrame({"Amount":[cash, emi]}, index=["Cash","EMI"]))

    st.subheader("Most Sold Models")
    rows = get_top_sellers(session, start_dt, end_dt, limit=10)
    session.close()

    if rows:
        data = []
        for name, units_sold, revenue in rows:
            row = {"Product": name, "Units": int(units_sold or 0)}
            if user['role'] == 'admin':
                row["Revenue"] = float(revenue or 0)
            data.append(row)
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No sales in selected range.")
