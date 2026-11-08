"""Speed and cost of the AI steps, worked out from the eval logs (no new AI calls).

Speed: every AI call in the eval runs logs `meta.seconds`. Cost: the runs did not log token counts, so tokens are
estimated from prompt and answer length (3.5 characters a token) and priced at Gemini Flash-Lite list prices
($0.25 per 1M input tokens, $1.50 per 1M output tokens; hidden thinking tokens are billed as output).
The low end assumes no thinking tokens, the high end assumes the 1,000-token thinking budget is used in full.

Run: python mvp/eval/speed_cost.py  ->  prints the table and writes outputs/speed_cost.json
"""
import json
import os
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "outputs")
PRICE_IN, PRICE_OUT = 0.25 / 1e6, 1.50 / 1e6
THINK_MAX = 1000
CHARS_PER_TOKEN = 3.5
TIMEOUT_S = 20


def pct(xs, q):
    """Percentile, 'lower' method: the observed value at or just below the q-th position (no interpolation)."""
    xs = sorted(xs)
    return xs[int((len(xs) - 1) * q)]


def timing(rows):
    secs = [r["meta"]["seconds"] for r in rows if (r.get("meta") or {}).get("seconds") is not None]
    backup = sum(1 for r in rows if (r.get("meta") or {}).get("provider") == "groq")
    return {"n": len(secs), "median_s": round(statistics.median(secs), 2), "p95_s": round(pct(secs, 0.95), 1),
            "max_s": round(max(secs), 1), "over_timeout": sum(s > TIMEOUT_S for s in secs), "backup_model": backup}


def cost(in_tokens, out_tokens):
    low = (in_tokens * PRICE_IN + out_tokens * PRICE_OUT) * 1000
    high = (in_tokens * PRICE_IN + (out_tokens + THINK_MAX) * PRICE_OUT) * 1000
    return round(low, 2), round(high, 2)


def main():
    w = json.load(open(os.path.join(OUT, "eval_writer-v6_auto.json"), encoding="utf-8"))
    a = json.load(open(os.path.join(OUT, "ask_ask-v6.json"), encoding="utf-8"))
    res = {"writer-v6": timing(w["rows"]), "ask-v6": timing(a["rows"])}
    # writer: about 4,400 prompt characters (rules + facts) and the three answers it returns
    w_out = statistics.mean(len(json.dumps(r.get("ai_answer") or {}, ensure_ascii=False)) for r in w["rows"]) / CHARS_PER_TOKEN
    res["writer-v6"]["tokens_in_est"], res["writer-v6"]["tokens_out_est"] = 1260, round(w_out)
    res["writer-v6"]["usd_per_1000_answers"] = cost(1260, w_out)
    # ask: two calls per question (router about 800 tokens in, answer writer about 1,000 tokens in) and one short answer
    a_out = statistics.mean(len(r["ai_answer"]) for r in a["rows"] if r.get("ai_answer")) / CHARS_PER_TOKEN
    res["ask-v6"]["tokens_in_est"], res["ask-v6"]["tokens_out_est"] = 1800, round(a_out)
    res["ask-v6"]["usd_per_1000_answers"] = cost(1800, a_out)
    json.dump(res, open(os.path.join(OUT, "speed_cost.json"), "w"), indent=1)
    for k, v in res.items():
        print(k, v)


if __name__ == "__main__":
    main()
