"""Shared helpers for all collectors.

Every record is normalised to one schema so the pipeline can treat sources uniformly:
  id, source, text, title, rating, date (YYYY-MM-DD), engagement, url, meta
No usernames or profile data are stored (privacy by design).
"""
import json, os, re, hashlib, time
from datetime import datetime, timezone

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (research; groww-sip-discovery)"}

PHONE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
ACCT = re.compile(r"\b\d{11,18}\b")


def scrub(text: str) -> str:
    """Remove personal identifiers before anything is stored or sent to an LLM."""
    if not text:
        return ""
    text = PHONE.sub("[phone]", text)
    text = EMAIL.sub("[email]", text)
    text = PAN.sub("[pan]", text)
    text = ACCT.sub("[number]", text)
    return re.sub(r"\s+", " ", text).strip()


def to_date(ts) -> str:
    if ts is None:
        return ""
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
    return str(ts)[:10]


def rec(source, sid, text, title="", rating=None, date="", engagement=0, url="", **meta):
    return {
        "id": f"{source}:{hashlib.md5(str(sid).encode()).hexdigest()[:12]}",
        "source": source,
        "title": scrub(title),
        "text": scrub(text),
        "rating": rating,
        "date": to_date(date),
        "engagement": engagement or 0,
        "url": url,
        "meta": meta,
    }


def save(name, records):
    path = os.path.join(RAW_DIR, f"{name}.jsonl")
    seen, n = set(), 0
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            if r["id"] in seen or not r["text"]:
                continue
            seen.add(r["id"])
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    print(f"[{name}] saved {n} records -> {path}")
    return n


def polite_sleep(s=1.0):
    time.sleep(s)
