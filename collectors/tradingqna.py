"""TradingQnA (Zerodha's public Discourse forum): search SIP-lifecycle queries, then pull
the full thread (first 25 posts) for each matching topic."""
import requests, re
from common import rec, save, HEADERS, polite_sleep

BASE = "https://tradingqna.com"
QUERIES = ["stop SIP", "stopped SIP", "pause SIP", "first SIP", "start SIP", "SIP negative returns", "SIP loss",
           "continue SIP", "SIP beginner", "new to mutual funds", "SIP mandate", "SIP failed", "skip SIP",
           "redeem mutual fund", "SIP 1 year", "SIP returns low", "should I stop SIP", "mutual fund beginner",
           "SIP worth", "discontinue SIP"]


def main():
    topics = set()
    for q in QUERIES:
        for page in (1, 2, 3):
            try:
                j = requests.get(f"{BASE}/search.json", params={"q": q + " after:2023-01-01", "page": page},
                                 headers={**HEADERS, "Accept": "application/json"}, timeout=30).json()
            except Exception:
                break
            topics.update(t["id"] for t in j.get("topics", []))
            if not j.get("grouped_search_result", {}).get("more_full_page_results"):
                break
            polite_sleep(1)
    recs = []
    for t in sorted(topics):
        try:
            j = requests.get(f"{BASE}/t/{t}.json", headers=HEADERS, timeout=30).json()
        except Exception:
            continue
        for p in j.get("post_stream", {}).get("posts", [])[:25]:
            text = re.sub(r"<[^>]+>", " ", p.get("cooked", ""))
            recs.append(rec("tradingqna", p["id"], text[:3000], title=j.get("title", "") if p["post_number"] == 1 else "",
                            date=p.get("created_at"), engagement=p.get("like_count", 0) or 0,
                            url=f"{BASE}/t/{t}/{p['post_number']}", topic=j.get("title", ""),
                            post_number=p["post_number"], staff=p.get("staff", False)))
        polite_sleep(0.8)
    save("tradingqna", recs)


if __name__ == "__main__":
    main()
