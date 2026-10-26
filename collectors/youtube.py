"""YouTube comments on Indian personal-finance videos about starting/stopping SIPs.
Uses yt-dlp search for video discovery and youtube-comment-downloader for comments (no API key)."""
import itertools, subprocess, json
from youtube_comment_downloader import YoutubeCommentDownloader, SORT_BY_POPULAR
from common import rec, save

QUERIES = ["should I stop my SIP", "SIP negative returns what to do", "first SIP beginner mutual fund",
           "SIP mistakes beginners India", "stopped SIP market crash", "SIP 1 year returns experience",
           "mutual fund SIP for beginners Groww", "why SIP returns are low", "SIP pause or stop",
           "how to start SIP Groww", "SIP kab band kare", "SIP loss me hai kya kare",
           "mutual fund SIP experience 1 saal", "is SIP worth it", "SIP vs FD first salary"]
PER_QUERY, PER_VIDEO = 6, 160


def search(q):
    out = subprocess.run(["yt-dlp", f"ytsearch{PER_QUERY}:{q}", "--flat-playlist", "-J"],
                         capture_output=True, text=True, timeout=120)
    try:
        return [(e["id"], e.get("title", ""), e.get("channel", "")) for e in json.loads(out.stdout)["entries"]]
    except Exception:
        return []


def main():
    dl, vids = YoutubeCommentDownloader(), {}
    for q in QUERIES:
        for vid, title, ch in search(q):
            vids.setdefault(vid, (title, ch, q))
    recs = []
    for vid, (title, ch, q) in vids.items():
        try:
            for c in itertools.islice(dl.get_comments(vid, sort_by=SORT_BY_POPULAR), PER_VIDEO):
                recs.append(rec("youtube", c["cid"], c["text"], date="", engagement=c.get("votes", 0),
                                url=f"https://www.youtube.com/watch?v={vid}&lc={c['cid']}",
                                video_title=title, channel=ch, query=q, published=c.get("time")))
        except Exception as e:
            print("skip", vid, e)
    print("videos", len(vids))
    save("youtube", recs)


if __name__ == "__main__":
    main()
