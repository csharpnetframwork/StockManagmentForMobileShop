import decimal
from sqlalchemy import func
from db import Product, Sale, SaleItem
def get_stock_summary(session):
    units = session.query(func.sum(Product.qty_on_hand)).scalar() or 0
    value = session.query(func.sum(Product.qty_on_hand * Product.sell_price)).scalar() or decimal.Decimal(0)
    return int(units), float(value)
def get_sales_summary(session, start, end):
    q = session.query(func.sum(Sale.total_amount)).filter(Sale.sale_datetime >= start, Sale.sale_datetime < end)
    total = q.scalar() or decimal.Decimal(0)
    cash = session.query(func.sum(Sale.total_amount)).filter(
        Sale.payment_type=="cash",
        Sale.sale_datetime >= start,
        Sale.sale_datetime < end
    ).scalar() or decimal.Decimal(0)
    emi = session.query(func.sum(Sale.total_amount)).filter(
        Sale.payment_type=="emi",
        Sale.sale_datetime >= start,
        Sale.sale_datetime < end
    ).scalar() or decimal.Decimal(0)
    return float(total), float(cash), float(emi)
def get_top_sellers(session, start, end, limit=10):
    from sqlalchemy import desc
    rows = (
        session.query(
            Product.name,
            func.sum(SaleItem.qty).label("units"),
            func.sum(SaleItem.line_total).label("revenue")
        )
        .join(SaleItem.product)
        .join(SaleItem.sale)
        .filter(Sale.sale_datetime >= start, Sale.sale_datetime < end)
        .group_by(Product.id)
        .order_by(desc("units"))
        .limit(limit)
        .all()
    )
    return rows
