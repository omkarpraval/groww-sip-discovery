"""Refresh the committed price cache (run by GitHub Actions). Public NAVs only."""
import json, os, re, sys

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mvp.core import data as D  # noqa: E402

# Popular first-SIP funds across categories (used by the golden set and as a search fallback).
QUERIES = [  # every word must appear in the scheme name (direct growth plans only)
    "parag parikh flexi cap", "hdfc flexi cap", "quant small cap", "nippon india small cap", "sbi small cap",
    "axis small cap", "motilal oswal midcap", "hdfc mid cap opportunities", "kotak emerging equity",
    "icici prudential bluechip", "mirae asset large cap", "axis bluechip", "mirae asset elss",
    "quant elss", "axis elss", "canara robeco bluechip", "quant active", "tata digital india",
    "icici prudential equity debt", "hdfc balanced advantage", "groww nifty total market index",
    "groww large cap", "groww value", "quant mid cap", "bandhan small cap", "tata small cap", "sbi contra",
    "icici prudential technology",
]


def resolve(q):
    r = requests.get(f"{D.API}/search", params={"q": q}, timeout=30).json()
    words = q.lower().split()
    def ok(x):
        n = re.sub(r"[^a-z0-9 ]", " ", x["schemeName"].lower()).split()
        return (all(w in n for w in words) and "direct" in n and "growth" in n
                and not set(n) & {"us", "idcw", "dividend", "bonus", "regular", "fof", "etf"})
    hits = sorted([x for x in r if ok(x)], key=lambda x: len(x["schemeName"]))
    return hits[0] if hits else None


def main():
    codes = {k: v["code"] for k, v in D.PROXIES.items()}
    funds = []
    for q in QUERIES:
        try:
            x = resolve(q)
        except Exception as e:  # noqa: BLE001
            print("search failed", q, e); continue
        if x:
            funds.append({"schemeCode": x["schemeCode"], "schemeName": x["schemeName"]})
            codes[x["schemeName"]] = x["schemeCode"]
        else:
            print("not found:", q)
    ok = 0
    for name, c in codes.items():
        try:
            n = D.save_cache(c); ok += 1
            print(f"cached {c} {name}: {n} prices")
        except Exception as e:  # noqa: BLE001
            print("failed", c, name, e)
    json.dump(funds, open(os.path.join(D.CACHE, "funds.json"), "w", encoding="utf-8"), indent=0, ensure_ascii=False)
    print(f"{ok}/{len(codes)} cached")


if __name__ == "__main__":
    main()
