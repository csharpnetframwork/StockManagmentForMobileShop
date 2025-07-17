import streamlit as st
from auth import require_role
from db import (
    SessionLocal, Product, Company, Customer, Sale, SaleItem, EmiDetail, StockMovement, IST
)
import datetime
import pandas as pd


def app():
    user = require_role(["owner", "admin", "employee"])
    st.title("New Sale")

    session = SessionLocal()

    # ------------------------ Customer Info ------------------------
    st.header("Customer Info")
    colA, colB = st.columns(2)
    with colA:
        cust_phone = st.text_input("Customer Phone")
    with colB:
        cust_name = st.text_input("Customer Name")

    # ------------------------ Load Products ------------------------
    products = session.query(Product).order_by(Product.name).all()
    prod_map = {
        f"{p.name} (₹{p.sell_price}, Qty {p.qty_on_hand})": p
        for p in products
        if p.qty_on_hand > 0
    }

    cart = st.session_state.setdefault("cart", [])

    # ------------------------ Manual Add ------------------------
    st.header("Add Product Manually")
    with st.form("add_to_cart_form", clear_on_submit=True):
        prod_choice = st.selectbox(
            "Select Product", list(prod_map.keys()) if prod_map else ["-- No stock --"]
        )
        qty = st.number_input("Qty", min_value=1, value=1, step=1)
        imei_override = st.text_input("IMEI (optional)")
        add_btn = st.form_submit_button("Add Item")
        if add_btn and prod_map and prod_choice in prod_map:
            p = prod_map[prod_choice]
            if qty > p.qty_on_hand:
                st.warning(f"Only {p.qty_on_hand} units in stock.")
            else:
                cart.append(
                    {
                        "product_id": p.id,
                        "name": p.name,
                        "qty": qty,
                        "price": float(p.sell_price),
                        "imei": imei_override or p.imei,
                    }
                )
                st.success(f"Added {qty} x {p.name} to cart.")

    # ------------------------ Bulk Add (Excel/CSV) ------------------------
    st.subheader("Bulk Add from Excel/CSV")
    st.caption(
        "Columns: imei, sku, name, qty, price. At least one of imei/sku/name required; qty required."
    )

    bulk_file = st.file_uploader(
        "Upload Sale Items", type=["csv", "xlsx", "xls"], key="bulk_sale_file"
    )

    sample_csv_data = (
        "imei,sku,name,qty,price\n"
        "123456789012345,MOB001,Demo Phone A,1,12000\n"
        ",ACC001,Fast Charger,2,800\n"
    )
    st.download_button(
        label="Download Sample Sale Template (CSV)",
        data=sample_csv_data,
        file_name="sale_import_template.csv",
        mime="text/csv",
        key="sale_template_dl",
    )

    addable_rows = []
    if bulk_file is not None:
        try:
            if bulk_file.name.lower().endswith(".csv"):
                bulk_df = pd.read_csv(bulk_file)
            else:
                bulk_df = pd.read_excel(bulk_file)
        except Exception as e:
            st.error(f"Could not read file: {e}")
            bulk_df = None

        if bulk_df is not None:
            bulk_df.columns = [c.strip().lower() for c in bulk_df.columns]
            if "qty" not in bulk_df.columns and "quantity" in bulk_df.columns:
                bulk_df["qty"] = bulk_df["quantity"]
            for col in ["imei", "sku", "name", "qty", "price"]:
                if col not in bulk_df.columns:
                    bulk_df[col] = None

            preview_rows = []
            for _, r in bulk_df.iterrows():
                imei_val = str(r.get("imei") or "").strip()
                sku_val = str(r.get("sku") or "").strip()
                name_val = str(r.get("name") or "").strip()
                qty_val = r.get("qty")
                price_val = r.get("price")

                try:
                    qty_val = int(qty_val)
                except Exception:
                    qty_val = 0

                prod = None
                if imei_val:
                    prod = session.query(Product).filter(Product.imei == imei_val).first()
                if not prod and sku_val:
                    prod = session.query(Product).filter(Product.sku == sku_val).first()
                if not prod and name_val:
                    prod = (
                        session.query(Product)
                        .filter(Product.name.ilike(name_val))
                        .first()
                    )

                if not prod:
                    status = "Not found"
                elif qty_val <= 0:
                    status = "Bad qty"
                elif qty_val > prod.qty_on_hand:
                    status = f"Stock short (have {prod.qty_on_hand})"
                else:
                    status = "OK"
                    addable_rows.append(
                        {
                            "product_id": prod.id,
                            "name": prod.name,
                            "qty": qty_val,
                            "price": float(price_val)
                            if pd.notna(price_val)
                            else float(prod.sell_price),
                            "imei": imei_val or prod.imei,
                        }
                    )

                preview_rows.append(
                    {
                        "Matched": prod.name if prod else "",
                        "IMEI": imei_val,
                        "SKU": sku_val,
                        "Name": name_val,
                        "Qty": qty_val,
                        "Price": price_val,
                        "Status": status,
                    }
                )

            st.write("Preview Import:")
            st.dataframe(pd.DataFrame(preview_rows), use_container_width=True)

            add_bulk = st.button(
                f"Add {len(addable_rows)} Valid Rows to Cart", key="bulk_add_btn"
            )
            if add_bulk:
                if not addable_rows:
                    st.warning("No valid rows to add.")
                else:
                    cart.extend(addable_rows)
                    st.success(f"Added {len(addable_rows)} items to cart.")
                    st.rerun()

    # ------------------------ Cart ------------------------
    if cart:
        st.subheader("Cart")
        df = pd.DataFrame(cart)
        df["line_total"] = df["qty"] * df["price"]
        st.dataframe(df, use_container_width=True)
        subtotal = float(df["line_total"].sum())
        st.write(f"**Subtotal: ₹{subtotal:,.2f}**")
    else:
        subtotal = 0.0

    # ------------------------ Payment ------------------------
    st.header("Payment")
    pay_type = st.radio("Payment Type", ["cash", "emi"], horizontal=True)

    emi_info = {}
    if pay_type == "emi":
        companies = (
            session.query(Company)
            .filter(Company.active == True)
            .order_by(Company.company_name)
            .all()
        )
        comp_names = [c.company_name for c in companies]
        comp_choice = st.selectbox(
            "Finance Company", comp_names + ["+ Add New Company"]
        )
        if comp_choice == "+ Add New Company":
            new_name = st.text_input("New Company Name")
            new_type = st.text_input("Company Type", value="NBFC")
            save_new = st.button("Save Company")
            if save_new and new_name:
                comp = Company(company_name=new_name, company_type=new_type)
                session.add(comp)
                session.commit()
                st.success("Company added. Select it above.")
                st.rerun()
        else:
            comp = next((c for c in companies if c.company_name == comp_choice), None)
            down_payment = st.number_input(
                "Down Payment (₹)", min_value=0.0, step=100.0, value=0.0
            )
            tenure = st.number_input("Tenure (months)", min_value=1, step=1, value=3)
            interest = st.number_input(
                "Interest Rate (%)", min_value=0.0, step=0.5, value=0.0
            )
            financed_amount = max(0.0, subtotal - down_payment)
            emi_amount = financed_amount / tenure if tenure else financed_amount
            emi_info = {
                "company": comp,
                "down": down_payment,
                "tenure": tenure,
                "interest": interest,
                "financed": financed_amount,
                "emi_amount": emi_amount,
                "next_due_date": datetime.datetime.now(IST)
                + datetime.timedelta(days=30),
            }
            st.write(f"**EMI Amount (approx): ₹{emi_amount:,.2f} / month**")

    # ------------------------ Submit ------------------------
    submit_sale = st.button("Submit Sale", type="primary")
    if submit_sale:
        if not cart or subtotal <= 0:
            st.error("Cart is empty. Add products before saving.")
            st.stop()

        # find/create customer
        cust = None
        if cust_phone:
            cust = (
                session.query(Customer)
                .filter(Customer.phone == cust_phone)
                .first()
            )
        if not cust:
            cust = Customer(
                full_name=cust_name or cust_phone or "Unknown",
                phone=cust_phone,
                email=None,
            )
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

        # sale items
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
                line_total=line_total,
            )
            session.add(item)
            p.qty_on_hand -= qty
            session.add(
                StockMovement(
                    product=p,
                    change_qty=-qty,
                    reason="sale",
                    ref_sale_id=sale.id,
                    user_id=user["id"],
                )
            )

        # EMI record
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
                next_due_date=emi_info["next_due_date"],
            )
            session.add(em)

        session.commit()
        st.success(f"Sale #{sale.id} saved.")
        st.session_state["cart"] = []
        st.rerun()

    session.close()
