import streamlit as st
from auth import require_role
from db import SessionLocal, Product, StockMovement
import pandas as pd

REQUIRED_COLS = ["name", "sku", "category", "price", "qty"]
OPTIONAL_COLS = ["imei"]


def app():
    user = require_role(["owner", "admin", "employee"])
    st.title("Inventory")

    session = SessionLocal()

    # ------------------------------------------------------------------
    # Manual Add
    # ------------------------------------------------------------------
    with st.expander("Add New Product"):
        sku = st.text_input("SKU / Code")
        imei = st.text_input("IMEI (optional)")
        name = st.text_input("*Name / Model")
        category = st.selectbox("Category", ["phone", "accessory", "service"])
        cost_price = st.number_input("Cost Price", min_value=0.0, step=100.0)
        sell_price = st.number_input("Sell Price", min_value=0.0, step=100.0)
        qty = st.number_input("Initial Qty", min_value=0, step=1)

        if st.button("Add Product", type="primary"):
            if not name:
                st.error("Name required.")
            else:
                p = Product(
                    sku=sku or None,
                    imei=imei or None,
                    name=name,
                    category=category,
                    cost_price=cost_price,
                    sell_price=sell_price,
                    qty_on_hand=qty,
                )
                session.add(p)
                session.flush()
                if qty:
                    session.add(
                        StockMovement(
                            product=p,
                            change_qty=qty,
                            reason="purchase",
                            user_id=user["id"],
                        )
                    )
                session.commit()
                st.success(f"Added {name}.")
                st.rerun()

    # ------------------------------------------------------------------
    # CSV / Excel Bulk Upload
    # ------------------------------------------------------------------
    st.subheader("Upload Stock via CSV/Excel")
    st.caption("Required: name,sku,category,price,qty. Optional: imei.")
    uploaded = st.file_uploader(
        "Choose File", type=["csv", "xlsx", "xls"], key="inv_csv"
    )

    sample_csv = (
        "name,sku,category,price,qty,imei\n"
        "Demo Phone C,MOB003,phone,20000,4,123456789012347\n"
        "Charger 20W,ACC020,accessory,900,15,\n"
    )
    st.download_button(
        "Download Sample Stock Template (CSV)",
        data=sample_csv,
        file_name="sample_stock.csv",
        mime="text/csv",
        key="inv_sample_dl",
    )

    if uploaded is not None:
        try:
            if uploaded.name.lower().endswith(".csv"):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)
        except Exception as e:
            st.error(f"Error reading file: {e}")
            df = None

        if df is not None:
            df.columns = [c.strip().lower() for c in df.columns]
            missing = [c for c in REQUIRED_COLS if c not in df.columns]
            if missing:
                st.error(f"Missing required columns: {missing}")
            else:
                st.write("Preview:")
                st.dataframe(df.head(), use_container_width=True)
                if st.button("Import CSV/Excel Rows", type="primary", key="import_csv_btn"):
                    added = 0
                    updated = 0
                    for _, row in df.iterrows():
                        name = str(row.get("name", "")).strip()
                        if not name:
                            continue
                        sku = str(row.get("sku") or "").strip() or None
                        category = str(row.get("category") or "phone").strip() or "phone"
                        price = float(row.get("price") or 0)
                        qty = int(row.get("qty") or 0)
                        imei = str(row.get("imei") or "").strip() or None

                        prod = None
                        if imei:
                            prod = (
                                session.query(Product)
                                .filter(Product.imei == imei)
                                .first()
                            )
                        if not prod and sku:
                            prod = (
                                session.query(Product)
                                .filter(Product.sku == sku, Product.name == name)
                                .first()
                            )
                        if not prod and name:
                            prod = (
                                session.query(Product)
                                .filter(Product.name == name)
                                .first()
                            )

                        if not prod:
                            prod = Product(
                                sku=sku,
                                imei=imei,
                                name=name,
                                category=category,
                                cost_price=price,
                                sell_price=price,
                                qty_on_hand=qty,
                            )
                            session.add(prod)
                            session.flush()
                            if qty:
                                session.add(
                                    StockMovement(
                                        product=prod,
                                        change_qty=qty,
                                        reason="purchase",
                                        user_id=user["id"],
                                    )
                                )
                            added += 1
                        else:
                            prod.qty_on_hand += qty
                            # set sell_price if not yet priced
                            if price and float(prod.sell_price or 0) == 0:
                                prod.sell_price = price
                            session.add(
                                StockMovement(
                                    product=prod,
                                    change_qty=qty,
                                    reason="purchase",
                                    user_id=user["id"],
                                )
                            )
                            updated += 1
                    session.commit()
                    st.success(f"Imported. Added {added}, updated {updated}.")
                    st.rerun()

    # ------------------------------------------------------------------
    # Inventory Table
    # ------------------------------------------------------------------
    products = session.query(Product).order_by(Product.name).all()
    if products:
        df = pd.DataFrame(
            [
                {
                    "ID": p.id,
                    "SKU": p.sku,
                    "IMEI": p.imei,
                    "Name": p.name,
                    "Category": p.category,
                    "Cost": float(p.cost_price),
                    "Sell": float(p.sell_price),
                    "Qty": p.qty_on_hand,
                }
                for p in products
            ]
        )
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No products.")

    # ------------------------------------------------------------------
    # Adjust Stock
    # ------------------------------------------------------------------
    with st.expander("Adjust Stock"):
        prod_options = {f"{p.name} (ID {p.id})": p.id for p in products}
        if prod_options:
            prod_choice = st.selectbox("Product", list(prod_options.keys()))
            adj_qty = st.number_input("Change Qty (+/-)", value=0, step=1)
            if st.button("Apply Adjustment"):
                pid = prod_options[prod_choice]
                prod = session.get(Product, pid)
                prod.qty_on_hand += adj_qty
                session.add(
                    StockMovement(
                        product=prod,
                        change_qty=adj_qty,
                        reason="adjustment",
                        user_id=user["id"],
                    )
                )
                session.commit()
                st.success("Stock updated.")
                st.rerun()
        else:
            st.info("Add products first.")

    session.close()
