"""Google Play reviews for Groww (com.nextbillion.groww), India / English.
Pulls newest + most-relevant + per-star newest to avoid a recency/rating skew."""
import argparse
from google_play_scraper import reviews, Sort
from common import rec, save, polite_sleep

APP = "com.nextbillion.groww"


def pull(sort, score=None, max_items=20000):
    out, token, got = [], None, 0
    while got < max_items:
        try:
            res, token = reviews(APP, lang="en", country="in", sort=sort, count=200,
                                 filter_score_with=score, continuation_token=token)
        except Exception as e:  # transient network errors
            print("retry", e); polite_sleep(3); continue
        out += res; got += len(res)
        if not res or not token:
            break
        polite_sleep(0.3)
    return out


def main(max_newest):
    rows = pull(Sort.NEWEST, None, max_newest) + pull(Sort.MOST_RELEVANT, None, 8000)
    for s in [1, 2, 3, 4, 5]:
        rows += pull(Sort.NEWEST, s, 12000)
    recs = [rec("play_store", r["reviewId"], r["content"], rating=r["score"], date=r["at"],
                engagement=r.get("thumbsUpCount", 0),
                url="https://play.google.com/store/apps/details?id=" + APP,
                app_version=r.get("reviewCreatedVersion"), has_reply=bool(r.get("replyContent")))
            for r in rows]
    save("play_store", recs)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--max", type=int, default=50000)
    main(ap.parse_args().max)
