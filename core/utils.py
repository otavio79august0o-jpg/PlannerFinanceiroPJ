
import hashlib
from datetime import datetime
from typing import Optional


def parse_date(date_str: str) -> Optional[str]:
    if not date_str:
        return None
    s = str(date_str).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y%m%d"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def br_to_float(value: str) -> float:
    if value is None:
        return 0.0
    s = str(value).strip()
    if not s:
        return 0.0
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def make_hash_unique(*parts: str) -> str:
    joined = "|".join(str(p) for p in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()
