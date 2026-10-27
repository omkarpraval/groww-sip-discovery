"""Build docs/data.json for the public site (GitHub Pages) from the engine outputs.
Runs after aggregate/golden in the workflow, so the site always shows the latest validated numbers.
Uses the same loading + quality gates as aggregate.py, so site numbers == dashboard numbers."""
import glob, json, os, re, time
from collections import Counter
import pandas as pd
from aggregate import load, CLUSTERS, quote_ok, to_num, ADDRESSABILITY, EARLY, ROOT

OUT = os.path.join(ROOT, "docs", "data.json")
TARGETS = {"primary_trigger": 70, "relevant": 90, "sip_action": 80}  # fixed before any scoring (see evidence log)
FUND = re.compile(r"parikh|ppfas|quant|nippon|hdfc|icici|sbi|axis|kotak|mirae|tata|uti|dsp|motilal|bandhan|"
                  r"flexi|small ?cap|mid ?cap|large ?cap|nifty|sensex|elss|index fund|lic\b", re.I)
FIRST = re.compile(r"\b(i|i'm|im|my|me|mine|mujhe|mera|meri|mere|maine)\b", re.I)  # first-person voice only
SRC = {"play_store": "Play Store", "app_store": "App Store", "reddit_post": "Reddit", "reddit_comment": "Reddit",
       "tradingqna": "TradingQnA", "youtube": "YouTube"}
DESC = {
    "Can't tell if my SIP is working": "Red or flat returns, doubting their fund choice, conflicting advice.",
    "Money got tight / life changed": "Unplanned expenses, weddings, low balance on debit day.",
    "Debit or mandate failed": "Autopay errors and bounce charges they didn’t see coming.",
    "App friction or distrust": "Refund delays, duplicate SIPs, units not allocated, support loops.",
    "No reason to stay": "No goal, social doubt, “SIP is an illusion” posts.",
}
THEME = {
    "market_fall_negative_returns": "Portfolio in the red", "underwhelming_returns": "Returns feel too slow",
    "expectation_mismatch": "Expected something else", "cash_flow_squeeze": "Money got tight",
    "payment_mandate_failure": "Debit / mandate failed", "app_ux_or_control_gap": "App friction",
    "platform_trust_doubt": "Doubts the platform", "information_overload_conflict": "Conflicting advice",
    "wrong_fund_doubt": "Doubts own fund choice", "goal_disconnect": "No goal / disengaged",
    "life_event": "Life event", "lock_in_or_tax": "Lock-in or tax", "social_influence": "Others stopped",
}
SEG = {
    "income_type": ("How they earn", {"salaried": "Salaried", "student_or_no_income": "Student / no income",
                                      "variable_or_business": "Variable or business income"}),
    "influencer": ("Who got them started", {"self_research": "Own research", "finfluencer_youtube": "YouTube finfluencer",
                                            "friend_family": "Friend or family", "app_or_ad": "App or ad"}),
    "age_band": ("Age", {"<25": "Under 25", "25-34": "25–34", "35-44": "35–44"}),
    "first_time": ("Investing before?", {"yes": "First-time investor", "no": "Has invested before"}),
}
OUTSIDE = {"reddit_forum": "Reddit / forums", "youtube_finfluencer": "YouTube finfluencers",
           "customer_support": "Customer support", "friend_family": "Friends & family",
           "amc_or_other_app": "Fund house / other app", "advisor_professional": "Advisor", "google_news": "Google / news"}
EMO = ["confused", "neutral", "frustrated", "anxious", "disappointed"]


def pct(a, b):
    return round(100 * a / b, 1) if b else 0.0


def short_url(u):
    m = re.match(r"(https://www\.reddit\.com/r/[^/]+/comments/[^/]+/)", u or "")
    return m.group(1) if m else u


def golden_summary(path):
    r = json.load(open(path))
    f = r.get("fields", {})
    return {"file": os.path.basename(path), "mode": r.get("mode", "corpus"), "n": r.get("n"),
            "prompt_version": r.get("prompt_version", ""), "models": r.get("models", {}),
            "fields": {k: {"agreement": v["agreement_pct"], "kappa": v["cohens_kappa"], "target": TARGETS.get(k)}
                       for k, v in f.items()}}


def main():
    df = load()
    gate_fail = df.relevant & ((df.confidence < 0.6) | ~df.quote_ok)
    rel = df[df.relevant & ~gate_fail].copy()
    early = rel[rel.early]
    ed = early[early.drop_event]
    src = {}
    for l in open(os.path.join(ROOT, "data", "stage1.jsonl"), encoding="utf-8"):
        r = json.loads(l)
        src[r["id"]] = (r.get("title") or "") + " " + r["text"]
    funnel = json.load(open(os.path.join(ROOT, "outputs", "funnel.json")))

    clusters, used = [], set()
    for name, trig in CLUSTERS.items():
        m = ed[ed.triggers.apply(lambda ts: bool(set(ts) & trig))]
        # quotes: the cluster must be the item's MAIN reason, verbatim, no fund names, never reused across clusters
        cand = m[m.triggers.apply(lambda ts: bool(ts) and ts[0] in trig) & m.evidence_quote.str.len().between(35, 170)]
        cand = cand[[not FUND.search(q) and quote_ok(q, src.get(i, "")) and q not in used and bool(FIRST.search(q))
                     for q, i in zip(cand.evidence_quote, cand.id)]]
        cand = cand.assign(_e=(cand.emotion != "neutral").astype(int)) \
                   .sort_values(["_e", "engagement"], ascending=False).drop_duplicates("evidence_quote")
        used.update(cand.evidence_quote.head(4))
        clusters.append({"name": name, "desc": DESC[name], "n": int(len(m)), "pct": pct(len(m), len(ed)),
                         "quotes": [{"text": r.evidence_quote, "source": SRC.get(r.source, r.source),
                                     "emotion": r.emotion.capitalize(), "url": short_url(r.url)}
                                    for r in cand.head(4).itertuples()]})
    clusters.sort(key=lambda c: -c["pct"])

    emo = ed.emotion.value_counts()
    emotion = [[e.capitalize(), pct(emo.get(e, 0), len(ed))] for e in EMO]
    emotion.append(["Other", round(100 - sum(x[1] for x in emotion), 1)])

    base = pct(rel.drop_event.sum(), len(rel))
    segments = []
    for col, (title, labels) in SEG.items():
        rows = []
        for val, g in rel[rel[col].isin(labels)].groupby(col):
            if len(g) >= 40:
                rows.append({"label": labels[val], "n": int(len(g)), "dropoff": pct(g.drop_event.sum(), len(g))})
        if len(rows) >= 2:
            segments.append({"title": title, "rows": sorted(rows, key=lambda r: -r["dropoff"])})

    oc = Counter(a for x in early.outside_app_action for a in x if a in OUTSIDE)
    PEERS = set(OUTSIDE) - {"customer_support", "amc_or_other_app"}  # outside the app = not the app's own channels
    any_out = int(early.outside_app_action.apply(lambda x: any(a in PEERS for a in x)).sum())
    outside = [{"label": OUTSIDE[k], "n": v, "pct": pct(v, len(early))} for k, v in oc.most_common()]

    chk = rel[rel.checking_behaviour != "unknown"]
    checking = {"n": int(len(chk)), "daily_pct": pct((chk.checking_behaviour == "daily_or_more").sum(), len(chk)),
                "rarely_pct": pct((chk.checking_behaviour == "rarely").sum(), len(chk))}

    ins = json.load(open(os.path.join(ROOT, "outputs", "insights.json")))
    themes = [{"label": THEME.get(t["theme"], t["theme"]), "mentions": t["mentions"], "reach": t["reach_pct"],
               "proximity": t["dropoff_proximity_pct"], "early": t["early_or_first_time_pct"],
               "addr": t["addressability"], "score": t["opportunity_score"]} for t in ins["themes"]]

    reports = [golden_summary(p) for p in sorted(glob.glob(os.path.join(ROOT, "outputs", "golden_report_*.json")))]
    primary = next((r for r in reports if r["mode"] == "corpus"), None)

    # where the AI was wrong: golden-set disagreements on the hardest field, shown openly on the site
    gold = pd.read_csv(os.path.join(ROOT, "data", "golden", "golden_human.csv"), dtype=str).fillna("")
    corrections = []
    if primary:
        rep = json.load(open(os.path.join(ROOT, "outputs", primary["file"])))
        for d in rep["disagreements"]:
            if "sip_action" not in d["diff"]:
                continue
            g = gold[gold.id == d["id"]]
            if g.empty or FUND.search(g.text.iat[0]):
                continue
            t = g.text.iat[0]
            corrections.append({"gid": g.gid.iat[0], "text": (t[:230] + "…") if len(t) > 230 else t,
                                "ai": d["diff"]["sip_action"]["engine"], "human": d["diff"]["sip_action"]["human"]})
        corrections = sorted(corrections, key=lambda c: (c["ai"] != "considering_stop", len(c["text"])))[:3]

    ex = early[early.drop_event & early.quote_ok & (early.evidence_quote.str.len() > 40)]
    stopword = re.compile(r"\b(stop|stopped|stopping|pause|paused|cancel|cancelled|band kar)", re.I)
    ex = ex[[not FUND.search(src.get(i, "")) and len(src.get(i, "")) < 420 and bool(stopword.search(src.get(i, "")))
             for i in ex.id]]
    ex = ex.sort_values("engagement", ascending=False).head(1)
    example = None
    for r in ex.itertuples():
        example = {"text": src[r.id].strip(), "source": SRC.get(r.source, r.source), "url": short_url(r.url),
                   "labels": {"Investor stage": r.investor_stage, "First-time?": r.first_time, "What they did": r.sip_action,
                              "Why": [THEME.get(t, t) for t in r.triggers] or ["none stated"], "Emotion": r.emotion,
                              "Unmet need": r.unmet_need},
                   "quote": r.evidence_quote, "model": r.model, "prompt": r.prompt_version}

    coll = funnel["collected"]
    data = {
        "updated": time.strftime("%d %b %Y"),
        "models": df.model.value_counts().to_dict(), "prompts": df.prompt_version.value_counts().to_dict(),
        "funnel": {"collected": sum(coll.values()), "unique": sum(funnel["deduplicated"].values()),
                   "sip": sum(funnel["stage1_relevant"].values()), "coded": int(len(df)), "relevant_ok": int(len(rel)),
                   "early": int(len(early)), "early_drops": int(len(ed)),
                   "by_source": [{"source": SRC[k] if k != "reddit_comment" else "Reddit comments",
                                  "collected": coll[k], "sip": funnel["stage1_relevant"][k]} for k in coll]},
        "clusters": clusters, "no_reason_pct": pct(ed.triggers.apply(lambda t: not t).sum(), len(ed)),
        "emotion": emotion, "actions": ed.sip_action.value_counts().to_dict(),
        "segments": segments, "baseline_dropoff": base,
        "outside": outside, "outside_any_pct": pct(any_out, len(early)), "checking": checking,
        "themes": themes,
        "golden": {"primary": primary, "all": reports, "items": int(len(gold)), "corrections": corrections},
        "quality": {"relevant_coded": int(df.relevant.sum()), "failed_quote": int((df.relevant & ~df.quote_ok).sum()),
                    "schema_repairs": int(df["_repaired"].notna().sum()) if "_repaired" in df else 0},
        "example": example,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(data, open(OUT, "w"), indent=1, ensure_ascii=False, default=int)
    print("site data written:", OUT, {k: data["funnel"][k] for k in ("sip", "relevant_ok", "early_drops")})


if __name__ == "__main__":
    main()
