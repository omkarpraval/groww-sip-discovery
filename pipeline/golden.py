"""Golden-set validation: compare engine labels with hand labels.
data/golden/golden_human.csv columns: id, text, relevant, sip_action, primary_trigger, first_time, emotion
Engine labels come from data/coded/coded.jsonl (or are generated fresh with --recode on a held-out run).
Outputs per-field agreement %, Cohen's kappa, confusion matrix, and every disagreement."""
import argparse, json, os
from collections import Counter
import pandas as pd

ROOT = os.path.join(os.path.dirname(__file__), "..")
GOLD = os.path.join(ROOT, "data", "golden", "golden_human.csv")
CODED = os.path.join(ROOT, "data", "coded", "coded.jsonl")
OUT = os.path.join(ROOT, "outputs", "golden_report.json")
FIELDS = ["relevant", "sip_action", "primary_trigger", "first_time", "emotion", "dropoff_moment"]
# dropoff_moment is derived from sip_action (stop / pause / reduce / redeem / failed debit / considering stopping).
# Added after the first scoring round, so it has no pre-set pass mark; it is the field every headline number uses.
DROP = {"considering_stop", "paused_or_skipped", "reduced", "stopped_or_cancelled", "redeemed", "failed_involuntary"}


def kappa(a, b):
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    return round((po - pe) / (1 - pe), 3) if pe < 1 else 1.0


def engine_labels(recode):
    if recode:
        import sys; sys.path.insert(0, os.path.dirname(__file__))
        import llm
        print("recoding golden set with chain", llm.build_chain())  # LLM_PROVIDER=groq scores Groq alone
        g = pd.read_csv(GOLD)
        out = []
        for i in range(0, len(g), 10):
            items = [{"id": r.id, "text": r.text} for r in g.iloc[i:i + 10].itertuples()]
            coded, m = llm.code_items_auto(items)
            out += [dict(c, model=m) for c in coded if c]
        return {o["id"]: o for o in out}
    return {json.loads(l)["id"]: json.loads(l) for l in open(CODED, encoding="utf-8")}


def main(recode):
    g = pd.read_csv(GOLD, dtype=str).fillna("")
    eng = engine_labels(recode)
    vers = {e.get("prompt_version", "") for e in eng.values()} if not recode else {__import__("llm").PROMPT_VERSION}
    rows, report = [], {"n": 0, "mode": "recode" if recode else "corpus", "fields": {}, "disagreements": []}
    for r in g.itertuples():
        e = eng.get(r.id)
        if not e:
            continue
        e_vals = {"relevant": str(bool(e["relevant"])).lower(), "sip_action": e["sip_action"],
                  "primary_trigger": (e["triggers"] or ["none"])[0], "first_time": e["first_time"],
                  "emotion": e["emotion"]}
        e_vals["dropoff_moment"] = str(e_vals["sip_action"] in DROP).lower()
        h_vals = {f: str(getattr(r, f)).strip().lower() for f in FIELDS if f != "dropoff_moment"}
        h_vals["dropoff_moment"] = str(h_vals["sip_action"] in DROP).lower()
        rows.append((r.id, h_vals, e_vals, e.get("confidence")))
    report["n"] = len(rows)
    for f in FIELDS:
        h = [x[1][f] for x in rows]; e = [x[2][f] for x in rows]
        report["fields"][f] = {
            "agreement_pct": round(100 * sum(a == b for a, b in zip(h, e)) / max(1, len(rows)), 1),
            "cohens_kappa": kappa(h, e),
            "confusion": pd.crosstab(pd.Series(h, name="human"), pd.Series(e, name="engine")).to_dict(),
        }
    for rid, h, e, conf in rows:
        diff = {f: {"human": h[f], "engine": e[f]} for f in FIELDS if h[f] != e[f]}
        if diff:
            report["disagreements"].append({"id": rid, "engine_confidence": conf, "diff": diff})
    report["prompt_version"] = ",".join(sorted(v for v in vers if v))
    report["models"] = dict(Counter(e.get("model", "") for e in eng.values() if e.get("id") in set(g.id)))
    json.dump(report, open(OUT, "w"), indent=2, default=str)
    if not recode:  # the score of the labels actually behind the published numbers
        json.dump(report, open(OUT.replace(".json", "_corpus.json"), "w"), indent=2, default=str)
    if recode:  # keep each prompt version's score for the evidence log
        json.dump(report, open(OUT.replace(".json", f"_{report['prompt_version']}_{os.getenv('LLM_PROVIDER') or 'auto'}.json"), "w"), indent=2, default=str)
    for f, v in report["fields"].items():
        print(f"{f:16s} agreement={v['agreement_pct']}%  kappa={v['cohens_kappa']}")
    print("disagreements:", len(report["disagreements"]), "of", report["n"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--recode", action="store_true")
    ap.add_argument("--set", choices=["golden", "heldout"], default="golden",
                    help="heldout = fresh posts labelled after prompt tuning; never used to write rules")
    a = ap.parse_args()
    if a.set == "heldout":
        GOLD = os.path.join(ROOT, "data", "golden", "heldout_human.csv")
        OUT = os.path.join(ROOT, "outputs", "heldout_report.json")
    main(a.recode)
