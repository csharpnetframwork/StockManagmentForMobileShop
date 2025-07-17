import streamlit as st
from auth import require_role
from db import (
    SessionLocal, Product, Company, Customer, Sale, SaleItem, EmiDetail, StockMovement, IST
)
import datetime
import pandas as pd

def app():
    user = require_role(["owner","admin","employee"])
    st.title("New Sale")

    session = SessionLocal()

    # Customer
    st.header("Customer Info")
    colA, colB = st.columns(2)
    with colA:
        cust_phone = st.text_input("Customer Phone")
    with colB:
        cust_name = st.text_input("Customer Name")

    # Products
    st.header("Products")
    products = session.query(Product).order_by(Product.name).all()
    prod_map = {f"{p.name} (₹{p.sell_price}, Qty {p.qty_on_hand})": p for p in products if p.qty_on_hand>0}

    cart = st.session_state.setdefault("cart", [])

    with st.form("add_to_cart_form", clear_on_submit=True):
        prod_choice = st.selectbox("Select Product", list(prod_map.keys()) if prod_map else ["-- No stock --"])
        qty = st.number_input("Qty", min_value=1, value=1, step=1)
        imei_override = st.text_input("IMEI (optional)")
        add_btn = st.form_submit_button("Add Item")
        if add_btn and prod_map and prod_choice in prod_map:
            p = prod_map[prod_choice]
            if qty > p.qty_on_hand:
                st.warning(f"Only {p.qty_on_hand} units in stock.")
            else:
                cart.append({
                    "product_id": p.id,
                    "name": p.name,
                    "qty": qty,
                    "price": float(p.sell_price),
                    "imei": imei_override or p.imei
                })
                st.success(f"Added {qty} x {p.name} to cart.")

    if cart:
        st.subheader("Cart")
        df = pd.DataFrame(cart)
        df["line_total"] = df["qty"] * df["price"]
        st.dataframe(df, use_container_width=True)
        subtotal = df["line_total"].sum()
        st.write(f"**Subtotal: ₹{subtotal:,.2f}**")
    else:
        subtotal = 0

    # Payment
    st.header("Payment")
    pay_type = st.radio("Payment Type", ["cash","emi"], horizontal=True)

    emi_info = {}
    if pay_type == "emi":
        companies = session.query(Company).filter(Company.active==True).order_by(Company.company_name).all()
        comp_names = [c.company_name for c in companies]
        comp_choice = st.selectbox("Finance Company", comp_names + ["+ Add New Company"])
        if comp_choice == "+ Add New Company":
            new_name = st.text_input("New Company Name")
            new_type = st.text_input("Company Type", value="NBFC")
            save_new = st.button("Save Company")
            if save_new:
                if new_name:
                    comp = Company(company_name=new_name, company_type=new_type)
                    session.add(comp)
                    session.commit()
                    st.success("Company added. Select it above.")
                    st.rerun()
        else:
            comp = next((c for c in companies if c.company_name==comp_choice), None)
            down_payment = st.number_input("Down Payment (₹)", min_value=0.0, step=100.0, value=0.0)
            tenure = st.number_input("Tenure (months)", min_value=1, step=1, value=3)
            interest = st.number_input("Interest Rate (%)", min_value=0.0, step=0.5, value=0.0)
            financed_amount = max(0.0, subtotal - down_payment)
            emi_amount = financed_amount / tenure if tenure else financed_amount
            emi_info = {
                "company": comp,
                "down": down_payment,
                "tenure": tenure,
                "interest": interest,
                "financed": financed_amount,
                "emi_amount": emi_amount,
                "next_due_date": datetime.datetime.now(IST) + datetime.timedelta(days=30)
            }
            st.write(f"**EMI Amount (approx): ₹{emi_amount:,.2f} / month**")

    # Submit Sale
    if st.button("Submit Sale", type="primary", disabled=(subtotal<=0)):
        cust = None
        if cust_phone:
            cust = session.query(Customer).filter(Customer.phone==cust_phone).first()
        if not cust:
            cust = Customer(full_name=cust_name or cust_phone or "Unknown", phone=cust_phone, email=None)
            session.add(cust)
            session.flush()

        sale = Sale(
            user_id=user["id"],
            customer_id=cust.id,
            payment_type=pay_type,
            total_amount=subtotal,
        )
        session.add(sale)
        session.flush()

        for line in cart:
            p = session.get(Product, line["product_id"])
            qty = line["qty"]
            line_total = qty * float(p.sell_price)
            item = SaleItem(
                sale_id=sale.id,
                product_id=p.id,
                imei=line.get("imei"),
                qty=qty,
                unit_price=p.sell_price,
                line_total=line_total
            )
            session.add(item)
            p.qty_on_hand -= qty
            session.add(StockMovement(product=p, change_qty=-qty, reason="sale", ref_sale_id=sale.id, user_id=user["id"]))

        if pay_type == "emi" and emi_info.get("company"):
            comp = emi_info["company"]
            em = EmiDetail(
                sale_id=sale.id,
                company_id=comp.id,
                down_payment=emi_info["down"],
                financed_amount=emi_info["financed"],
                tenure_months=emi_info["tenure"],
                interest_rate=emi_info["interest"],
                emi_amount=emi_info["emi_amount"],
                next_due_date=emi_info["next_due_date"]
            )
            session.add(em)

        session.commit()
        st.success(f"Sale #{sale.id} saved.")
        st.session_state["cart"] = []
        st.rerun()

    session.close()
