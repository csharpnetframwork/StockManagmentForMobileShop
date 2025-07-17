import re, pathlib
from typing import List
IMEI_RE = re.compile(r'(?:\D|^)(\d{15})(?:\D|$)')
def extract_imeis_from_text(text: str) -> List[str]:
    return list({m.group(1) for m in IMEI_RE.finditer(text)})
def extract_imeis_from_filename(name: str) -> List[str]:
    return extract_imeis_from_text(name)
def extract_imeis_from_file(path: str) -> List[str]:
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            txt = f.read()
        vals = extract_imeis_from_text(txt)
        if vals:
            return vals
    except Exception:
        pass
    return extract_imeis_from_filename(pathlib.Path(path).name)
