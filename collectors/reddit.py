"""Reddit posts + comments from Indian investing communities via the Arctic Shift archive API
(public Reddit archive; no login). Query set targets the SIP lifecycle: starting, checking,
pausing, stopping, continuing."""
import requests
from common import rec, save, HEADERS, polite_sleep

API = "https://arctic-shift.photon-reddit.com/api"
SUBS = ["mutualfunds", "IndiaInvestments", "personalfinanceindia", "FIREIndia",
        "IndianStockMarket", "StockMarketIndia", "Groww"]
POST_Q = ["stop SIP", "stopped SIP", "pause SIP", "paused SIP", "first SIP", "started SIP", "new to SIP",
          "SIP negative", "SIP loss", "SIP red", "should I continue SIP", "SIP returns", "beginner mutual fund",
          "first time investor", "Groww SIP", "SIP mandate", "SIP failed", "missed SIP", "skip SIP",
          "redeem SIP", "SIP not growing", "SIP worth it", "continue SIP", "discontinue SIP", "SIP 1 year",
          "SIP 6 months", "emergency SIP", "SIP portfolio down"]
COMMENT_Q = ["stopped my SIP", "paused my SIP", "stop my SIP", "my first SIP", "started my SIP",
             "still negative", "SIP in red", "cancel SIP", "skip SIP", "SIP for 1 year", "SIP since", "groww SIP"]
AFTER = "2024-01-01"


def get(path, params):
    for _ in range(3):
        try:
            r = requests.get(f"{API}/{path}", params=params, headers=HEADERS, timeout=60)
            if r.ok:
                return r.json().get("data", []) or []
        except Exception:
            pass
        polite_sleep(2)
    return []


def main():
    recs = []
    for s in SUBS:
        for q in POST_Q:
            for p in get("posts/search", {"subreddit": s, "query": q, "limit": 100, "after": AFTER}):
                body = p.get("selftext") or ""
                if body in ("[removed]", "[deleted]"):
                    body = ""
                recs.append(rec("reddit_post", p["id"], (body or "")[:4000], title=p.get("title", ""),
                                date=p.get("created_utc"), engagement=p.get("score", 0),
                                url="https://www.reddit.com" + p.get("permalink", ""),
                                subreddit=s, n_comments=p.get("num_comments", 0), query=q))
            polite_sleep(0.4)
        for q in COMMENT_Q:
            for c in get("comments/search", {"subreddit": s, "body": q, "limit": 100, "after": AFTER}):
                recs.append(rec("reddit_comment", c["id"], (c.get("body") or "")[:3000],
                                date=c.get("created_utc"), engagement=c.get("score", 0),
                                url=f"https://www.reddit.com/comments/{(c.get('link_id') or '')[3:]}/_/{c['id']}",
                                subreddit=s, query=q))
            polite_sleep(0.4)
        print(s, len(recs))
    # posts with empty body still carry signal in the title
    for r in recs:
        if not r["text"] and r["title"]:
            r["text"] = r["title"]
    save("reddit", recs)


if __name__ == "__main__":
    main()
