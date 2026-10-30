"""facts -> AI words -> quality gate -> shown answer (or the template fallback)."""
from . import gate, template, writer


def explain(facts, provider=None, timeout=20, keys=None):
    out = {"facts": facts, "fallback_reason": None, "checks": [], "meta": {}}
    try:
        ans, meta = writer.write(facts, provider=provider, timeout=timeout, keys=keys)
        out["meta"] = meta
        out["ai_answer"] = ans
        ok, checks = gate.check(ans, facts)
        out["checks"] = checks
        if ok:
            out.update({"answer": {k: ans[k].strip() for k in gate.KEYS}, "source": "ai"})
            return out
        out["fallback_reason"] = "failed: " + ", ".join(n for n, passed, _ in checks if not passed)
    except writer.WriterError as e:
        out["fallback_reason"] = f"AI unavailable: {str(e)[:160]}"
    out.update({"answer": template.answer(facts), "source": "template"})
    return out
