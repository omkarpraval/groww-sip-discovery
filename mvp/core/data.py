"""Public fund prices (mfapi.in, AMFI data) with a committed cache as fallback.
Nothing personal is fetched or stored: only scheme codes and daily NAVs."""
import json, os, re, time
from datetime import date, datetime

import requests

API = "https://api.mfapi.in/mf"
CACHE = os.path.join(os.path.dirname(__file__), "..", "cache")

# Index funds used ONLY as proxies for an index. The app shows the index name, never the fund name.
PROXIES = {
    "market": {"code": 120716, "label": "the market (Nifty 50)"},
    "large": {"code": 147666, "label": "large-company index (Nifty 100)"},
    "mid": {"code": 147622, "label": "mid-company index (Nifty Midcap 150)"},
    "small": {"code": 147623, "label": "small-company index (Nifty Smallcap 250)"},
    "broad": {"code": 147625, "label": "broad market index (Nifty 500)"},
}
CATEGORY_RULES = [  # scheme_category text -> proxy key (first match wins)
    (r"large & mid", "broad"), (r"large cap", "large"), (r"mid cap", "mid"), (r"small cap", "small"),
    (r"flexi|multi cap|elss|focused|value|contra|dividend yield", "broad"),
]
CATEGORY_NAMES = {"large": "large-cap", "mid": "mid-cap", "small": "small-cap", "broad": "diversified equity"}


class DataError(Exception):
    pass


def _cache_path(code):
    return os.path.join(CACHE, f"{int(code)}.json")


def parse_series(raw):
    """mfapi payload -> (meta, sorted list of (date, nav))."""
    pts = []
    for row in raw.get("data", []):
        try:
            d = datetime.strptime(row["date"], "%d-%m-%Y").date()
            v = float(row["nav"])
        except (KeyError, ValueError):
            continue
        if v > 0:
            pts.append((d, v))
    pts.sort()
    return raw.get("meta", {}), pts


def load_fund(code, live=True, timeout=12):
    """Returns (meta, series, source) where source is 'live' or 'cache'."""
    if live:
        try:
            r = requests.get(f"{API}/{int(code)}", timeout=timeout)
            if r.status_code == 200 and r.json().get("data"):
                meta, pts = parse_series(r.json())
                if pts:
                    return meta, pts, "live"
        except (requests.RequestException, ValueError):
            pass
    p = _cache_path(code)
    if os.path.exists(p):
        meta, pts = parse_series(json.load(open(p, encoding="utf-8")))
        return meta, pts, "cache"
    raise DataError(f"no price data for scheme {code}")


def save_cache(code, timeout=30):
    r = requests.get(f"{API}/{int(code)}", timeout=timeout)
    r.raise_for_status()
    raw = r.json()
    raw["data"] = [{"date": x["date"], "nav": x["nav"]} for x in raw.get("data", [])]
    os.makedirs(CACHE, exist_ok=True)
    json.dump(raw, open(_cache_path(code), "w", encoding="utf-8"), separators=(",", ":"))
    return len(raw["data"])


def search(q, live=True, timeout=10):
    """Direct-or-regular growth plans matching q. Falls back to the cached fund list."""
    q = (q or "").strip()
    if len(q) < 3:
        return []
    out = []
    if live:
        try:
            r = requests.get(f"{API}/search", params={"q": q}, timeout=timeout)
            if r.status_code == 200:
                out = r.json()
        except (requests.RequestException, ValueError):
            out = []
    if not out:
        p = os.path.join(CACHE, "funds.json")
        if os.path.exists(p):
            words = q.lower().split()
            out = [f for f in json.load(open(p, encoding="utf-8")) if all(w in f["schemeName"].lower() for w in words)]
    keep = [f for f in out if re.search(r"growth", f["schemeName"], re.I)
            and not re.search(r"idcw|dividend|bonus|payout", f["schemeName"], re.I)]
    return keep[:25]


def proxy_for(category):
    c = (category or "").lower()
    if "equity" not in c:
        return None
    for pat, key in CATEGORY_RULES:
        if re.search(pat, c):
            return key
    return None
