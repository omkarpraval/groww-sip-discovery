"""Apple App Store reviews for Groww (id 1404871703), India storefront, via the public RSS feed
(max 10 pages x 50 per sort order)."""
import requests
from common import rec, save, HEADERS, polite_sleep

APP_ID = 1404871703


def main():
    recs = []
    for sort in ["mostrecent", "mosthelpful"]:
        for page in range(1, 11):
            url = f"https://itunes.apple.com/in/rss/customerreviews/page={page}/id={APP_ID}/sortby={sort}/json"
            try:
                feed = requests.get(url, headers=HEADERS, timeout=30).json().get("feed", {})
            except Exception as e:
                print("skip", url, e); continue
            for e in feed.get("entry", []) or []:
                if "im:rating" not in e:
                    continue
                recs.append(rec("app_store", e["id"]["label"], e["content"]["label"], title=e["title"]["label"],
                                rating=int(e["im:rating"]["label"]), date=e["updated"]["label"],
                                url=f"https://apps.apple.com/in/app/id{APP_ID}",
                                app_version=e.get("im:version", {}).get("label")))
            polite_sleep(0.5)
    save("app_store", recs)


if __name__ == "__main__":
    main()
