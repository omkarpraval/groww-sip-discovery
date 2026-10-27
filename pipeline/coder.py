"""Stage 2: LLM coding of the Stage-1 population with Gemini (structured JSON output).
Resumable: already-coded ids are skipped, so it can run across several free-tier sessions."""
import argparse, json, os, random, time
import llm
from llm import code_items, PROMPT_VERSION, LLMError, resolve_model

ROOT = os.path.join(os.path.dirname(__file__), "..")
STATUS = os.path.join(ROOT, "outputs", "coder_status.json")


def write_status(**kw):
    """Committed with the results so failures are visible without opening the Actions log."""
    json.dump({"prompt_version": PROMPT_VERSION, "time": time.strftime("%Y-%m-%d %H:%M:%S"), **kw},
              open(STATUS, "w"), indent=2)
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
        done = {json.loads(l)["id"] for l in open(OUT, encoding="utf-8")}
    todo = [r for r in rows if r["id"] not in done][: limit or None]
    try:
        model, avail = resolve_model()
    except LLMError as e:
        msg = str(e).replace(os.getenv("GEMINI_API_KEY", "~~"), "***")
        write_status(ok=False, stage="resolve_model", error=msg)
        print("stopping:", msg); return
    llm.MODEL = model
    print(f"to code: {len(todo)} (already {len(done)}) model={model} prompt={PROMPT_VERSION}")
    gap, coded_n, error = 60.0 / rpm, 0, None
    with open(OUT, "a", encoding="utf-8") as f:
        for i in range(0, len(todo), batch):
            chunk, t0 = todo[i:i + batch], time.time()
            try:
                coded = code_items(chunk, model=model)
            except LLMError as e:
                error = str(e).replace(os.getenv("GEMINI_API_KEY", "~~"), "***")
                print("stopping:", error); break
            for r, c in zip(chunk, coded):
                if not c:
                    continue
                c.update({"id": r["id"], "source": r["source"], "date": r["date"], "url": r["url"],
                          "engagement": r["engagement"], "rating": r.get("rating"),
                          "model": model, "prompt_version": PROMPT_VERSION})
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
                coded_n += 1
            f.flush()
            print(f"{i + len(chunk)}/{len(todo)}")
            time.sleep(max(0, gap - (time.time() - t0)))
    write_status(ok=error is None, model=model, coded_this_run=coded_n, already=len(done), todo=len(todo),
                 error=error, models_available=[m for m in avail if "gemini" in m][:15])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=15)
    ap.add_argument("--max-per-source", type=int, default=0)
    ap.add_argument("--rpm", type=float, default=8)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    main(a.batch, a.max_per_source, a.rpm, a.limit)
