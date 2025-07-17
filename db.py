"""
Database models & session setup.

- Uses Streamlit secrets if available: st.secrets["db"]["url"]
- Else uses environment variable DB_URL
- Else falls back to local SQLite (for dev only)

Auto-seeds admin user + demo data when empty.
"""
import os
import datetime
import pytz
import streamlit as st

from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Float, Boolean,
    ForeignKey, Text, Numeric
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from passlib.hash import bcrypt

IST = pytz.timezone("Asia/Kolkata")
Base = declarative_base()

# ------------------------------------------------------------------
# Connection URL resolution
# ------------------------------------------------------------------
def _get_db_url():
    # 1. Streamlit secrets
    try:
        return st.secrets["db"]["url"]
    except Exception:
        pass
    # 2. Env var
    env_url = os.getenv("DB_URL")
    if env_url:
        return env_url
    # 3. Fallback to local sqlite (dev only)
    return "sqlite:///data/shop.db"

DB_URL = _get_db_url()
engine = create_engine(DB_URL, connect_args={} if not DB_URL.startswith("sqlite") else {"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


# ------------------------------------------------------------------
# Models
# ------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    email = Column(String(255))
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="employee")  # owner/admin/employee
    full_name = Column(String(128))
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(IST))
    sales = relationship("Sale", back_populates="user")


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    sku = Column(String(64))
    imei = Column(String(32), unique=True, nullable=True)
    name = Column(String(255), nullable=False)
    category = Column(String(64), default="phone")  # phone/accessory/service
    cost_price = Column(Numeric(12,2), default=0)
    sell_price = Column(Numeric(12,2), default=0)
    qty_on_hand = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(IST))
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(IST), onupdate=lambda: datetime.datetime.now(IST))
    sale_items = relationship("SaleItem", back_populates="product")
    stock_movements = relationship("StockMovement", back_populates="product")


class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True)
    company_name = Column(String(255), nullable=False, unique=True)
    company_type = Column(String(64), default="NBFC")  # NBFC/Bank/StoreFinance/Other
    active = Column(Boolean, default=True)
    emi_details = relationship("EmiDetail", back_populates="company")


class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True)
    full_name = Column(String(255))
    phone = Column(String(32))
    email = Column(String(255))
    govt_id = Column(String(64))
    notes = Column(Text)
    sales = relationship("Sale", back_populates="customer")


class Sale(Base):
    __tablename__ = "sales"
    id = Column(Integer, primary_key=True)
    sale_datetime = Column(DateTime, default=lambda: datetime.datetime.now(IST))
    user_id = Column(Integer, ForeignKey("users.id"))
    customer_id = Column(Integer, ForeignKey("customers.id"))
    payment_type = Column(String(16), default="cash")  # cash/emi
    total_amount = Column(Numeric(12,2), default=0)
    notes = Column(Text)
    bill_image_path = Column(String(255))
    user = relationship("User", back_populates="sales")
    customer = relationship("Customer", back_populates="sales")
    items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")
    emi_detail = relationship("EmiDetail", back_populates="sale", uselist=False, cascade="all, delete-orphan")


class SaleItem(Base):
    __tablename__ = "sale_items"
    id = Column(Integer, primary_key=True)
    sale_id = Column(Integer, ForeignKey("sales.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    imei = Column(String(32))
    qty = Column(Integer, default=1)
    unit_price = Column(Numeric(12,2), default=0)
    line_total = Column(Numeric(12,2), default=0)
    sale = relationship("Sale", back_populates="items")
    product = relationship("Product", back_populates="sale_items")


class EmiDetail(Base):
    __tablename__ = "emi_details"
    id = Column(Integer, primary_key=True)
    sale_id = Column(Integer, ForeignKey("sales.id"))
    company_id = Column(Integer, ForeignKey("companies.id"))
    down_payment = Column(Numeric(12,2), default=0)
    financed_amount = Column(Numeric(12,2), default=0)
    tenure_months = Column(Integer, default=0)
    interest_rate = Column(Float, default=0.0)
    emi_amount = Column(Numeric(12,2), default=0)
    next_due_date = Column(DateTime, nullable=True)
    sale = relationship("Sale", back_populates="emi_detail")
    company = relationship("Company", back_populates="emi_details")


class StockMovement(Base):
    __tablename__ = "stock_movements"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    change_qty = Column(Integer, default=0)
    reason = Column(String(64))  # purchase/sale/adjustment/return
    ref_sale_id = Column(Integer, ForeignKey("sales.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(IST))
    product = relationship("Product", back_populates="stock_movements")


# ------------------------------------------------------------------
# Init & seed
# ------------------------------------------------------------------
def init_db():
    """Create tables & seed admin if missing."""
    # Ensure schema exists
    Base.metadata.create_all(bind=engine)
    seed_admin_if_empty()


def seed_admin_if_empty():
    """Create admin + demo products if DB empty."""
    session = SessionLocal()
    try:
        if session.query(User).count() == 0:
            admin_user = User(
                username="admin",
                email="vishalaws7007@gmail.com",
                password_hash=bcrypt.hash("vishal@7007"),
                role="admin",
                full_name="Admin User",
                active=True,
            )
            session.add(admin_user)
            # sample stock
            session.add_all([
                Product(sku="MOB001", imei="123456789012345", name="Demo Phone A", category="phone", cost_price=10000, sell_price=12000, qty_on_hand=5),
                Product(sku="MOB002", imei="123456789012346", name="Demo Phone B", category="phone", cost_price=15000, sell_price=18000, qty_on_hand=3),
                Product(sku="ACC001", name="Fast Charger", category="accessory", cost_price=500, sell_price=800, qty_on_hand=20),
                Product(sku="ACC002", name="Screen Protector", category="accessory", cost_price=50, sell_price=150, qty_on_hand=100),
            ])
            session.add_all([
                Company(company_name="Bajaj Finance", company_type="NBFC"),
                Company(company_name="HDFC Bank", company_type="Bank"),
            ])
            session.commit()
    finally:
        session.close()


# ------------------------------------------------------------------
# Convenience helpers (used in auth / pages)
# ------------------------------------------------------------------
def get_user_by_username(username: str, session):
    return session.query(User).filter(User.username == username).first()

def verify_password(user: User, password: str) -> bool:
    try:
        return bcrypt.verify(password, user.password_hash)
    except Exception:
        return False
