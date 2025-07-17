import streamlit as st
from auth import require_role
from db import SessionLocal, SaleItem, Sale, Customer
from utils.scanning import extract_imeis_from_file, extract_imeis_from_text
import tempfile, io

# OCR optional
try:
    import pytesseract
    from PIL import Image
    _HAS_TESS = True
except Exception:
    _HAS_TESS = False

try:
    from pdf2image import convert_from_bytes
    _HAS_PDF2IMAGE = True
except Exception:
    _HAS_PDF2IMAGE = False


def ocr_image_bytes(data: bytes) -> str:
    if not _HAS_TESS:
        return ""
    try:
        img = Image.open(io.BytesIO(data))
        return pytesseract.image_to_string(img)
    except Exception:
        return ""

def ocr_pdf_bytes(data: bytes) -> str:
    if not (_HAS_TESS and _HAS_PDF2IMAGE):
        return ""
    try:
        pages = convert_from_bytes(data)
        txts = [pytesseract.image_to_string(p) for p in pages]
        return "\n".join(txts)
    except Exception:
        return ""


def app():
    user = require_role(["owner","admin","employee"])
    st.title("Bill Scan / Lookup")

    uploaded = st.file_uploader("Upload Bill (Image/PDF/Text)", type=["jpg","jpeg","png","pdf","txt"])
    if not uploaded:
        return

    data = uploaded.getbuffer()
    extracted_text = ""
    if uploaded.type == "text/plain":
        extracted_text = data.decode("utf-8", errors="ignore")
    elif uploaded.type in ("image/jpeg","image/png","image/jpg"):
        extracted_text = ocr_image_bytes(data)
    elif uploaded.type == "application/pdf":
        extracted_text = ocr_pdf_bytes(data)

    with tempfile.NamedTemporaryFile(delete=False, suffix="."+uploaded.name.split(".")[-1]) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    imeis = []
    if extracted_text:
        imeis = extract_imeis_from_text(extracted_text)
    if not imeis:
        imeis = extract_imeis_from_file(tmp_path)

    if not imeis:
        st.warning("No IMEI found. Try clearer image or enter manually.")
        return

    st.success(f"Found IMEI(s): {', '.join(imeis)}")
    session = SessionLocal()
    found_sales = []
    for imei in imeis:
        rows = (
            session.query(SaleItem, Sale, Customer)
            .join(SaleItem.sale)
            .join(Sale.customer)
            .filter(SaleItem.imei==imei)
            .all()
        )
        for si, s, c in rows:
            found_sales.append({
                "SaleID": s.id,
                "Customer": c.full_name,
                "Phone": c.phone,
                "Payment": s.payment_type,
                "Amount": float(s.total_amount),
                "IMEI": si.imei
            })
    session.close()

    import pandas as pd
    df = pd.DataFrame(found_sales)
    if user['role'] != 'admin' and 'Amount' in df.columns:
        df = df.drop(columns=['Amount'])
    st.dataframe(df, use_container_width=True)
