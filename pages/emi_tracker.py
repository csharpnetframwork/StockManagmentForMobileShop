import streamlit as st
from auth import require_role
from db import SessionLocal, EmiDetail, Sale, Customer, Company
from sqlalchemy.orm import joinedload
import pandas as pd

def app():
    user = require_role(["owner","admin","employee"])
    st.title("EMI Tracker")

    session = SessionLocal()
    rows = (
        session.query(EmiDetail)
        .options(joinedload(EmiDetail.sale).joinedload(Sale.customer),
                 joinedload(EmiDetail.company))
        .all()
    )

    data = []
    for em in rows:
        sale = em.sale
        cust = sale.customer if sale else None
        comp = em.company if em.company else None
        row = {
            "SaleID": sale.id if sale else None,
            "Customer": cust.full_name if cust else None,
            "Phone": cust.phone if cust else None,
            "Company": comp.company_name if comp else None,
            "Tenure": em.tenure_months,
            "Next Due": em.next_due_date,
        }
        if user['role'] == 'admin':
            row["DownPayment"] = float(em.down_payment or 0)
            row["Financed"] = float(em.financed_amount or 0)
            row["EMI"] = float(em.emi_amount or 0)
            row["Interest%"] = em.interest_rate
        data.append(row)
    session.close()

    if data:
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No EMI records.")
