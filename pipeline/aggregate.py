"""Stage 3: turn coded rows into decision-ready numbers:
theme frequency, drop-off proximity, stage x trigger, segment cuts, and an opportunity score.
Addressability weights are a documented human judgement (see ADDRESSABILITY) -- kept separate so
reviewers can disagree with them without touching the AI output."""
import json, os
from collections import Counter, defaultdict
import pandas as pd

ROOT = os.path.join(os.path.dirname(__file__), "..")
CODED = os.path.join(ROOT, "data", "coded", "coded.jsonl")
OUT = os.path.join(ROOT, "outputs")
DROP = {"considering_stop", "paused_or_skipped", "reduced", "stopped_or_cancelled", "redeemed", "failed_involuntary"}
EARLY = {"considering", "first_months", "within_year"}

# Can a Groww growth PM move this, within the constraints (no fund/stock recommendations,
# no fear/FOMO/urgency)? 1.0 = squarely in product control, 0.3 = mostly external.
ADDRESSABILITY = {
    "market_fall_negative_returns": 0.6,   # can't change markets; CAN change how a fall is understood
    "underwhelming_returns": 0.8,          # expectation-setting & progress framing are product levers
    "expectation_mismatch": 0.9,
    "cash_flow_squeeze": 0.8,              # flexible pause/skip/reduce instead of cancel
    "payment_mandate_failure": 0.9,
    "app_ux_or_control_gap": 1.0,
    "platform_trust_doubt": 0.6,
    "information_overload_conflict": 0.6,
    "wrong_fund_doubt": 0.3,               # constrained: cannot recommend funds
    "goal_disconnect": 0.9,
    "life_event": 0.4,
    "lock_in_or_tax": 0.5,
    "social_influence": 0.4,
}


def to_num(v):
    """Engagement arrives as int (reviews/Reddit) or text like '1.2K' (YouTube)."""
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v or "0").strip().upper().replace(",", "")
    mult = 1000.0 if s.endswith("K") else 1e6 if s.endswith("M") else 1.0
    try:
        return float(s.rstrip("KM") or 0) * mult
    except ValueError:
        return 0.0


def load():
    rows = [json.loads(l) for l in open(CODED, encoding="utf-8")]
    df = pd.DataFrame(rows)
    df["engagement"] = df["engagement"].apply(to_num)
    df["triggers"] = df["triggers"].apply(lambda t: [x for x in (t or []) if x != "none"])
    df["drop_event"] = df["sip_action"].isin(DROP)
    df["early"] = df["investor_stage"].isin(EARLY) | (df["first_time"] == "yes")
    return df


def main():
    if not os.path.exists(CODED) or os.path.getsize(CODED) == 0:
        print("no coded rows yet; skipping aggregation"); return
    df = load()
    n_all = len(df)
    rel = df[df.relevant & (df.confidence >= 0.6)].copy()
    low_conf = int((df.relevant & (df.confidence < 0.6)).sum())
    ex = rel.explode("triggers").dropna(subset=["triggers"]).reset_index(drop=True)

    themes = []
    for trig, g in ex.groupby("triggers"):
        ids = set(g.id)
        sub = rel[rel.id.isin(ids)]
        reach = len(ids) / len(rel)
        severity = sub.drop_event.mean()
        early_share = sub.early.mean()
        addr = ADDRESSABILITY.get(trig, 0.5)
        sources = sub.source.nunique()
        themes.append({
            "theme": trig, "mentions": len(ids), "reach_pct": round(100 * reach, 1),
            "dropoff_proximity_pct": round(100 * severity, 1),
            "early_or_first_time_pct": round(100 * early_share, 1),
            "sources_present": int(sources), "addressability": addr,
            "opportunity_score": round(100 * reach * (0.5 + severity) * addr * (0.5 + early_share), 2),
            "top_emotion": sub.emotion.mode().iat[0] if len(sub) else "",
            "top_needs": sub.sort_values("engagement", ascending=False).unmet_need.head(5).tolist(),
            "quotes": sub.sort_values("engagement", ascending=False)[["evidence_quote", "source", "url"]]
                        .head(6).to_dict("records"),
        })
    themes = sorted(themes, key=lambda t: -t["opportunity_score"])

    def share(col, frame):
        return frame[col].value_counts(normalize=True).mul(100).round(1).to_dict()

    drops = rel[rel.drop_event]
    stage_x = pd.crosstab(ex.triggers, ex.investor_stage, normalize="columns").mul(100).round(1)
    seg = {}
    for col in ["income_type", "money_source", "influencer", "age_band", "first_time"]:
        known = rel[rel[col] != "unknown"]
        recs = []
        for val, g in known.groupby(col):
            tc = Counter(t for ts in g.triggers for t in ts).most_common(3)
            recs.append({col: val, "n": int(len(g)), "dropoff_pct": round(100 * g.drop_event.mean(), 1),
                         "early_pct": round(100 * g.early.mean(), 1), "top_triggers": tc})
        seg[col] = sorted(recs, key=lambda r: -r["n"])

    insights = {
        "funnel": {"coded": n_all, "relevant_high_conf": int(len(rel)), "relevant_low_conf_review": low_conf,
                   "dropoff_events": int(len(drops)),
                   "by_source": rel.source.value_counts().to_dict()},
        "sip_action": share("sip_action", rel),
        "emotion_in_dropoffs": share("emotion", drops),
        "checking": share("checking_behaviour", rel[rel.checking_behaviour != "unknown"]),
        "checks_what": rel[rel.checks_what.str.len() > 0].checks_what.str.lower().value_counts().head(15).to_dict(),
        "outside_app": rel.explode("outside_app_action").outside_app_action.value_counts().to_dict(),
        "themes": themes,
        "stage_x_trigger": stage_x.to_dict(),
        "segments": seg,
        "model": df.model.iat[0] if "model" in df else "", "prompt_version": df.prompt_version.iat[0] if "prompt_version" in df else "",
    }
    json.dump(insights, open(os.path.join(OUT, "insights.json"), "w"), indent=2, default=str)
    pd.DataFrame([{k: v for k, v in t.items() if k not in ("quotes", "top_needs")} for t in themes]) \
        .to_csv(os.path.join(OUT, "opportunity_table.csv"), index=False)
    print(pd.DataFrame(themes)[["theme", "mentions", "reach_pct", "dropoff_proximity_pct",
                                "early_or_first_time_pct", "addressability", "opportunity_score"]].to_string())


if __name__ == "__main__":
    main()
