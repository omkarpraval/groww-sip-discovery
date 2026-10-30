"""AI writer: turns computed facts into three plain answers. Gemini first, Groq as backup.
The model never sees anything personal: only the facts dict (rupee amounts, months, rates)."""
import json, os, time

import requests

PROMPT_VERSION = "writer-v2"
GEMINI_MODEL = os.getenv("GEMINI_MODEL") or "gemini-flash-lite-latest"
GROQ_MODEL = os.getenv("GROQ_MODEL") or "openai/gpt-oss-120b"

SYSTEM = """You explain a first-time investor's own SIP numbers in plain, calm English for someone new to investing.
You are NOT an adviser. You only explain the FACTS given to you.

FACTS.say holds checked, plain sentences for each answer. Build each answer from them: you may reorder, join or
lightly reword them and add ONE short sentence of plain meaning (e.g. "So a dip like this is common at this stage.").
Keep every number exactly as written in FACTS.say. Never use field names (anything with an underscore).

Write three answers, 2-3 sentences each, every sentence under 22 words:
- "normal": use say.your_numbers and say.history. If direction is "down" it is a LOSS: say "less than you put in",
  never "gain". If direction is "up" it is above what was put in.
- "market_or_fund": use say.market_or_fund. Start with the conclusion (mostly the market / the fund did less well /
  both / about the same / cannot compare), then the rupee comparison.
- "patience": use say.patience, then end with say.uncertainty word for word.

Hard rules (an automatic checker rejects any answer that breaks one):
1. No numbers other than those in FACTS.say. No percentages.
2. Never advise: no "should", "recommend", "suggest", "consider", "switch", "buy", "sell", "redeem", "add more",
   "invest more", "keep investing", "stay invested", "continue", "don't stop", "hold on". Do not say what to do.
3. Never predict or promise: no "will recover", "will go up", "guaranteed", "sure to", "definitely", "certainly".
4. No fear, urgency or FOMO: no "panic", "crash", "hurry", "don't miss", "regret", "worrying".
5. Name no fund, fund house or index fund. Refer to comparisons only by the labels in FACTS.say.
6. No jargon: never XIRR, NAV, CAGR, volatility, drawdown, benchmark, attribution. Never call a fund good, bad, right or wrong.
7. Talk to the user as "you". Calm and specific. No exclamation marks.
Return JSON: {"normal": "...", "market_or_fund": "...", "patience": "..."}"""

SCHEMA = {"type": "OBJECT", "properties": {k: {"type": "STRING"} for k in ("normal", "market_or_fund", "patience")},
          "required": ["normal", "market_or_fund", "patience"]}


class WriterError(Exception):
    pass


def public_facts(f):
    """Facts the model may see: drop private helper fields and the checker's own list."""
    def clean(o):
        if isinstance(o, dict):
            return {k: clean(v) for k, v in o.items() if not k.startswith("_") and k not in ("allowed_numbers", "price_source")}
        if isinstance(o, list):
            return [clean(v) for v in o]
        return o
    return clean(f)


def _gemini(prompt, key, timeout):
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": SYSTEM}]},
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json", "responseSchema": SCHEMA}}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    r = requests.post(url, params={"key": key}, json=body, timeout=timeout)
    if r.status_code != 200:
        raise WriterError(f"gemini HTTP {r.status_code}: {r.text[:160]}")
    parts = r.json()["candidates"][0]["content"]["parts"]
    return json.loads("".join(p.get("text", "") for p in parts if not p.get("thought"))), GEMINI_MODEL


def _groq(prompt, key, timeout):
    body = {"model": GROQ_MODEL, "temperature": 0.2, "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]}
    r = requests.post("https://api.groq.com/openai/v1/chat/completions", json=body, timeout=timeout,
                      headers={"Authorization": f"Bearer {key}"})
    if r.status_code != 200:
        raise WriterError(f"groq HTTP {r.status_code}: {r.text[:160]}")
    return json.loads(r.json()["choices"][0]["message"]["content"]), GROQ_MODEL


def write(facts, provider=None, timeout=20, keys=None):
    """Returns (answer dict, meta). Raises WriterError if every provider fails."""
    keys = keys or {}
    gk = keys.get("gemini") or os.getenv("GEMINI_API_KEY")
    qk = keys.get("groq") or os.getenv("GROQ_API_KEY")
    provider = provider or os.getenv("LLM_PROVIDER") or "auto"
    order = {"gemini": ["gemini"], "groq": ["groq"]}.get(provider, ["gemini", "groq"])
    prompt = "FACTS:\n" + json.dumps(public_facts(facts), ensure_ascii=False, indent=1)
    errors = []
    for p in order:
        k = gk if p == "gemini" else qk
        if not k:
            errors.append(f"{p}: no key"); continue
        t0 = time.time()
        try:
            ans, model = (_gemini if p == "gemini" else _groq)(prompt, k, timeout)
            return ans, {"provider": p, "model": model, "seconds": round(time.time() - t0, 1),
                         "prompt_version": PROMPT_VERSION}
        except (WriterError, requests.RequestException, KeyError, IndexError, ValueError) as e:
            errors.append(f"{p}: {str(e)[:120]}")
    raise WriterError("; ".join(errors))
