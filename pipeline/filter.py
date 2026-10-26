"""Stage 1 (deterministic, full corpus): merge sources, de-duplicate, drop off-topic, and attach
keyword flags. Produces the population the LLM codes plus full-corpus counts for the funnel."""
import glob, json, os, re, hashlib
from collections import Counter

ROOT = os.path.join(os.path.dirname(__file__), "..")
RAW, OUT = os.path.join(ROOT, "data", "raw"), os.path.join(ROOT, "data")

SIP_RE = re.compile(r"\bsips?\b|s\.i\.p|mutual|\bmfs?\b|auto[- ]?pay|mandate|instal+ment|\bnav\b|xirr|redeem|"
                    r"redemption|step[- ]?up|\belss\b|index fund|lump ?sum|एसआईपी|म्यूचुअल|निवेश", re.I)
FLAGS = {
    "kw_stop_pause": r"\bstop|stopped|pause|paused|cancel|discontinu|skip|band kar|बंद",
    "kw_market_fall": r"\bred\b|negative|loss|crash|fall|down|dip|gir",
    "kw_payment_fail": r"mandate|auto ?pay|bounce|failed|nach|not deducted|debit",
    "kw_first_time": r"first (sip|time|investment)|beginner|new to|just started|naya|pehli",
    "kw_cashflow": r"emi|emergency|job|salary|no money|expense|loan|paisa nahi",
    "kw_returns_expect": r"returns?|xirr|cagr|growth|profit|fd\b",
}
FLAGS = {k: re.compile(v, re.I) for k, v in FLAGS.items()}
MIN_DATE = {"play_store": "2023-01-01", "app_store": "2023-01-01"}


def norm(t):
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()[:200]


def main():
    rows = []
    for f in sorted(glob.glob(os.path.join(RAW, "*.jsonl"))):
        rows += [json.loads(l) for l in open(f, encoding="utf-8")]
    funnel = {"collected": Counter(r["source"] for r in rows)}
    seen, kept = set(), []
    for r in rows:
        text = ((r.get("title") or "") + " " + r["text"]).strip()
        h = hashlib.md5(norm(text).encode()).hexdigest()
        if h in seen:
            continue
        seen.add(h)
        r["_full"] = text
        kept.append(r)
    funnel["deduplicated"] = Counter(r["source"] for r in kept)
    rel = []
    for r in kept:
        if len(r["_full"]) < 40:
            continue
        if r["date"] and r["date"] < MIN_DATE.get(r["source"], "2000-01-01"):
            continue
        # forum sources were already queried for SIP topics; app reviews need the keyword gate
        if r["source"] in ("play_store", "app_store") and not SIP_RE.search(r["_full"]):
            continue
        if r["source"] in ("youtube", "reddit_comment") and not SIP_RE.search(r["_full"]) \
                and not FLAGS["kw_stop_pause"].search(r["_full"]):
            continue
        r["flags"] = [k for k, rx in FLAGS.items() if rx.search(r["_full"])]
        r.pop("_full")
        rel.append(r)
    funnel["stage1_relevant"] = Counter(r["source"] for r in rel)
    with open(os.path.join(OUT, "stage1.jsonl"), "w", encoding="utf-8") as f:
        for r in rel:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    funnel = {k: dict(v) for k, v in funnel.items()}
    json.dump(funnel, open(os.path.join(ROOT, "outputs", "funnel.json"), "w"), indent=2)
    print(json.dumps(funnel, indent=2))


if __name__ == "__main__":
    main()
