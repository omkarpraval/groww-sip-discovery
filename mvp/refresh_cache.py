"""Refresh the committed price cache (run by GitHub Actions). Public NAVs only."""
import json, os, sys

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mvp.core import data as D  # noqa: E402

# Popular first-SIP funds across categories (used by the golden set and as a search fallback).
QUERIES = [
    "Parag Parikh Flexi Cap Fund - Direct Plan - Growth", "HDFC Flexi Cap Fund - Growth Option - Direct Plan",
    "Quant Small Cap Fund - Growth - Direct Plan", "Nippon India Small Cap Fund - Direct Plan Growth",
    "SBI Small Cap Fund - Direct Plan - Growth", "Axis Small Cap Fund - Direct Plan - Growth",
    "Motilal Oswal Midcap Fund-Direct Plan-Growth", "HDFC Mid-Cap Opportunities Fund - Growth Option - Direct Plan",
    "Kotak Emerging Equity Fund - Direct Plan - Growth", "ICICI Prudential Bluechip Fund - Direct Plan - Growth",
    "Mirae Asset Large Cap Fund - Direct Plan - Growth", "Axis Bluechip Fund - Direct Plan - Growth",
    "Mirae Asset ELSS Tax Saver Fund - Direct Plan - Growth", "Quant ELSS Tax Saver Fund - Growth Option - Direct Plan",
    "Axis ELSS Tax Saver Fund - Direct Plan - Growth", "Canara Robeco Bluechip Equity Fund - Direct Plan - Growth",
    "Quant Active Fund - Growth Option - Direct Plan", "Tata Digital India Fund-Direct Plan-Growth",
    "ICICI Prudential Equity & Debt Fund - Direct Plan - Growth", "HDFC Balanced Advantage Fund - Growth Plan - Direct Plan",
    "Groww Nifty Total Market Index Fund - Direct Growth", "Groww Large Cap Fund - Direct Plan Growth",
    "Groww Value Fund - Direct Plan - Growth", "Quant Mid Cap Fund - Growth Option - Direct Plan",
    "Bandhan Small Cap Fund - Direct Plan - Growth", "Tata Small Cap Fund-Direct Plan-Growth",
    "SBI Contra Fund - Direct Plan - Growth", "ICICI Prudential Technology Fund - Direct Plan - Growth",
]


def resolve(q):
    r = requests.get(f"{D.API}/search", params={"q": q}, timeout=30).json()
    exact = [x for x in r if x["schemeName"].strip().lower() == q.lower()]
    return (exact or r or [None])[0]


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
