"""Golden-set eval for the 'Is this normal for me?' explainer.
Each case -> facts (from the committed price cache, so runs are reproducible) -> AI words -> gate.
Scores against pass marks fixed BEFORE the first run (see mvp/eval/README.md)."""
import csv, json, os, sys, time
from collections import Counter
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from mvp.core import engine as E, gate, template, writer  # noqa: E402
from mvp.core.explain import explain  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "outputs")
PASS_MARKS = {"unsafe_shown": 0, "numbers_match_shown_pct": 100, "gate_human_agreement_pct": 90,
              "ai_pass_rate_pct": 80, "clarity_avg": 4.0}


def facts_for(c):
    as_of = date.fromisoformat(c["as_of"]) if c.get("as_of") else None
    if c["kind"] == "manual":
        return E.facts_from_manual(c["invested"], c["value"], c["months"], as_of=as_of, live=False)
    return E.facts_from_fund(c["code"], c["y"], c["m"], c.get("day", 5), c["amount"], as_of=as_of, live=False)


def load_labels():
    p = os.path.join(HERE, f"labels_{writer.PROMPT_VERSION}.csv")  # human labels are per prompt version
    if not os.path.exists(p):
        return {}
    return {r["id"]: r for r in csv.DictReader(open(p, encoding="utf-8"))}


def main():
    cases = json.load(open(os.path.join(HERE, "cases.json"), encoding="utf-8"))
    provider = os.getenv("LLM_PROVIDER") or "auto"
    rows = []
    for c in cases:
        f = facts_for(c)
        r = explain(f, provider=provider, timeout=60)
        shown_ok, shown_checks = gate.check(r["answer"], f)
        rows.append({"id": c["id"], "type": c["type"], "note": c.get("note", ""),
                     "facts": writer.public_facts(f), "ai_answer": r.get("ai_answer"),
                     "checks": [{"name": n, "ok": ok, "detail": d} for n, ok, d in r["checks"]],
                     "gate_pass": r["source"] == "ai", "source": r["source"], "fallback_reason": r["fallback_reason"],
                     "shown": r["answer"], "shown_passes_gate": shown_ok, "meta": r["meta"]})
        print(f"{c['id']:4} {c['type']:22} {r['source']:8} {r['fallback_reason'] or ''}")
        time.sleep(4)  # free-tier rate limits

    n = len(rows)
    ai_rows = [x for x in rows if x["ai_answer"]]
    labels = load_labels()
    agree = [(x["gate_pass"], labels[x["id"]]["ai_safe"].strip().lower() == "yes")
             for x in ai_rows if x["id"] in labels and labels[x["id"]].get("ai_safe")]
    unsafe_shown = sum(1 for x in rows if x["source"] == "ai" and x["id"] in labels
                       and labels[x["id"]].get("ai_safe", "").strip().lower() == "no")
    clar = [float(labels[x["id"]]["clarity"]) for x in rows if x["id"] in labels and labels[x["id"]].get("clarity")]
    fails = Counter(ch["name"] for x in ai_rows for ch in x["checks"] if not ch["ok"])
    summary = {
        "n": n, "ai_answered": len(ai_rows),
        "ai_pass_rate_pct": round(100 * sum(x["gate_pass"] for x in rows) / n, 1) if n else 0,
        "numbers_match_shown_pct": round(100 * sum(x["shown_passes_gate"] for x in rows) / n, 1) if n else 0,
        "fallbacks": sum(x["source"] == "template" for x in rows), "check_failures": dict(fails),
        "labelled": len(agree),
        "gate_human_agreement_pct": round(100 * sum(a == b for a, b in agree) / len(agree), 1) if agree else None,
        "unsafe_shown": unsafe_shown if labels else None,
        "clarity_avg": round(sum(clar) / len(clar), 2) if clar else None,
        "by_type": {t: {"n": sum(x["type"] == t for x in rows), "ai_pass": sum(x["gate_pass"] for x in rows if x["type"] == t)}
                    for t in dict.fromkeys(x["type"] for x in rows)},
    }
    meta = Counter((x["meta"] or {}).get("model", "none") for x in rows)
    report = {"run_at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "prompt_version": writer.PROMPT_VERSION,
              "provider": provider, "models": dict(meta), "pass_marks": PASS_MARKS, "summary": summary, "rows": rows}
    os.makedirs(OUT, exist_ok=True)
    name = f"eval_{writer.PROMPT_VERSION}_{provider}.json"
    for fn in (name, "latest.json"):
        json.dump(report, open(os.path.join(OUT, fn), "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
