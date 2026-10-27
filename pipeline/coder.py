"""Stage 2: LLM coding of the Stage-1 population (Gemini first, Groq as automatic fallback).
Resumable: ids already coded with the current prompt are skipped, so it can run across free-tier sessions."""
import argparse, json, os, random, time
import llm
from collections import Counter
from llm import PROMPT_VERSION, LLMError

ROOT = os.path.join(os.path.dirname(__file__), "..")
STATUS = os.path.join(ROOT, "outputs", "coder_status.json")


def write_status(**kw):
    """Committed with the results so failures are visible without opening the Actions log."""
    json.dump({"prompt_version": PROMPT_VERSION, "time": time.strftime("%Y-%m-%d %H:%M:%S"), **kw},
              open(STATUS, "w"), indent=2)
def redact(msg):
    for k in ("GEMINI_API_KEY", "GROQ_API_KEY"):
        if os.getenv(k):
            msg = msg.replace(os.getenv(k), "***")
    return msg


IN = os.path.join(ROOT, "data", "stage1.jsonl")
OUT = os.path.join(ROOT, "data", "coded", "coded.jsonl")


def main(batch, max_per_source, rpm, limit):
    rows = [json.loads(l) for l in open(IN, encoding="utf-8")]
    random.Random(42).shuffle(rows)  # fixed seed => reproducible sample
    if max_per_source:
        cnt, keep = {}, []
        for r in rows:
            src = r["source"]
            if cnt.get(src, 0) < max_per_source:
                keep.append(r); cnt[src] = cnt.get(src, 0) + 1
        rows = keep
    done = set()
    if os.path.exists(OUT):
        done = {r["id"] for r in map(json.loads, open(OUT, encoding="utf-8"))
                if r.get("prompt_version") == PROMPT_VERSION}  # older prompt versions get re-coded
    todo = [r for r in rows if r["id"] not in done][: limit or None]
    try:
        chain = llm.build_chain()
    except LLMError as e:
        write_status(ok=False, stage="build_chain", error=redact(str(e))[:300], probes=llm.PROBES)
        print("stopping:", redact(str(e))); return
    if chain[0][0] == "gemini":
        llm.MODEL = chain[0][1]
    print(f"to code: {len(todo)} (already {len(done)}) chain={chain} prompt={PROMPT_VERSION}")
    gap, coded_n, error, used = 60.0 / rpm, 0, None, Counter()
    with open(OUT, "a", encoding="utf-8") as f:
        for i in range(0, len(todo), batch):
            chunk, t0 = todo[i:i + batch], time.time()
            try:
                coded, model = llm.code_items_auto(chunk)
            except LLMError as e:
                error = redact(str(e))
                print("stopping:", error); break
            for r, c in zip(chunk, coded):
                if not c:
                    continue
                c.update({"id": r["id"], "source": r["source"], "date": r["date"], "url": r["url"],
                          "engagement": r["engagement"], "rating": r.get("rating"),
                          "model": model, "prompt_version": PROMPT_VERSION})
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
                coded_n += 1; used[model] += 1
            f.flush()
            print(f"{i + len(chunk)}/{len(todo)}")
            time.sleep(max(0, gap - (time.time() - t0)))
    gem = [c[1] for c in chain if c[0] == "gemini"]
    write_status(ok=error is None, model=(gem or [llm.label(*chain[0])])[0], coded_this_run=coded_n,
                 coded_by_model=dict(used), already=len(done), todo=len(todo), error=error,
                 chain=[llm.label(*c) for c in chain], switches=[{k: redact(str(v)) for k, v in s.items()}
                                                              for s in llm.SWITCHES], probes=llm.PROBES)


def safe_main(*args):
    """Any unexpected crash still leaves a readable status file in the repo."""
    try:
        main(*args)
    except Exception as e:
        msg = redact(f"{type(e).__name__}: {e}")[:500]
        write_status(ok=False, stage="crash", error=msg, probes=llm.PROBES)
        print("crashed:", msg)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=15)
    ap.add_argument("--max-per-source", type=int, default=0)
    ap.add_argument("--rpm", type=float, default=8)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    safe_main(a.batch, a.max_per_source, a.rpm, a.limit)
