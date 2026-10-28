"""Gemini client + the coding schema. Shared by the batch pipeline and the live Streamlit app,
so mentors test exactly the same prompt/model that coded the corpus."""
import json, os, time, requests

MODEL = os.getenv("GEMINI_MODEL") if os.getenv("GEMINI_MODEL") not in (None, "", "auto") else "gemini-3.8-flash"
PROMPT_VERSION = "coder-v1.3"
API = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"

E = lambda *v: {"type": "STRING", "enum": list(v)}
TRIGGERS = ["market_fall_negative_returns", "underwhelming_returns", "expectation_mismatch", "cash_flow_squeeze",
            "payment_mandate_failure", "app_ux_or_control_gap", "platform_trust_doubt",
            "information_overload_conflict", "wrong_fund_doubt", "goal_disconnect", "life_event",
            "lock_in_or_tax", "social_influence", "none"]
OUTSIDE = ["reddit_forum", "youtube_finfluencer", "friend_family", "advisor_professional", "google_news",
           "customer_support", "amc_or_other_app", "none_stated"]

ITEM_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "id": {"type": "STRING"},
        "relevant": {"type": "BOOLEAN"},
        "investor_stage": E("considering", "first_months", "within_year", "beyond_year", "unknown"),
        "first_time": E("yes", "no", "unknown"),
        "sip_action": E("started", "continuing", "considering_stop", "paused_or_skipped", "reduced",
                        "stopped_or_cancelled", "redeemed", "increased", "restarted", "failed_involuntary", "none"),
        "triggers": {"type": "ARRAY", "items": E(*TRIGGERS)},
        "checking_behaviour": E("daily_or_more", "weekly", "monthly_statement", "rarely", "unknown"),
        "checks_what": {"type": "STRING"},
        "emotion": E("anxious", "regretful", "confused", "frustrated", "disappointed", "confident",
                     "indifferent", "neutral"),
        "outside_app_action": {"type": "ARRAY", "items": E(*OUTSIDE)},
        "income_type": E("salaried", "variable_or_business", "student_or_no_income", "unknown"),
        "age_band": E("<25", "25-34", "35-44", "45+", "unknown"),
        "money_source": E("salary", "family_or_pocket_money", "business", "windfall_bonus", "unknown"),
        "influencer": E("friend_family", "finfluencer_youtube", "app_or_ad", "colleague_employer",
                        "self_research", "unknown"),
        "unmet_need": {"type": "STRING"},
        "evidence_quote": {"type": "STRING"},
        "confidence": {"type": "NUMBER"},
    },
    "required": ["id", "relevant", "investor_stage", "first_time", "sip_action", "triggers", "checking_behaviour",
                 "emotion", "outside_app_action", "income_type", "age_band", "money_source", "influencer",
                 "unmet_need", "evidence_quote", "confidence"],
}
BATCH_SCHEMA = {"type": "ARRAY", "items": ITEM_SCHEMA}

_HERE = os.path.dirname(__file__)
CODEBOOK = open(os.path.join(_HERE, "..", "prompts", "codebook.md"), encoding="utf-8").read()

SYSTEM = f"""You are a qualitative user researcher coding public Indian investor feedback (English, Hindi,
Hinglish) about mutual fund SIPs, for a product team studying why first-time investors stop SIPs.
Follow this codebook exactly:

{CODEBOOK}

Rules:
- Code ONLY what the text states or very directly implies. If not stated -> "unknown"/"none"/"none_stated".
- Never invent age, income, or influencer. A mention of "salary" implies income_type=salaried.
- triggers: at most 3, most important first; use "none" alone when nothing is stated.
- evidence_quote must be copied verbatim from the text (<=25 words); "" if not relevant.
- If the text is not relevant, still return the object with relevant=false, sip_action="none",
  triggers=["none"], and all other fields unknown/neutral, confidence reflecting certainty it is irrelevant.
- sip_action=considering_stop ONLY if the author states they are thinking of stopping/pausing/cancelling/
  redeeming THEIR OWN SIP. Seeking advice or reassurance is not considering_stop - BUT an explicit question about
  stopping or pausing their own SIP ("should I stop my SIP?", "continue or stop?") IS considering_stop.
- first_time=yes ONLY when the author explicitly says they are new/first-time; otherwise unknown.
- Advice written for someone else, with no first-person SIP behaviour -> relevant=false, sip_action="none".
- Step-up / top-up / added more -> increased; cut the amount -> reduced (never "continuing").
- You are NOT giving investment advice; you are only labelling text.
Return a JSON array with one object per input item, same ids, same order."""


class LLMError(Exception):
    pass


class ProviderExhausted(LLMError):
    """Daily quota used up, model retired, or persistently overloaded: move to the next provider."""


# Newest first. Google retires older models for new API keys (run #2 got a 404 on gemini-2.5-flash).
FALLBACK_MODELS = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3-flash", "gemini-flash-latest",
                   "gemini-3.8-flash-lite", "gemini-flash-lite-latest", "gemini-2.5-flash"]
NON_TEXT = ("tts", "image", "audio", "live", "embedding", "native")  # not usable for JSON text coding


def list_models(key=None):
    """Model ids this key can call with generateContent (used to pick a working model)."""
    key = key or os.getenv("GEMINI_API_KEY")
    try:
        r = requests.get("https://generativelanguage.googleapis.com/v1beta/models",
                         params={"key": key, "pageSize": 200}, timeout=60)
    except requests.exceptions.RequestException as e:
        raise LLMError(f"ListModels network {type(e).__name__}")
    if r.status_code != 200:
        raise LLMError(f"ListModels HTTP {r.status_code}: {r.text[:300]}")
    return [m["name"].split("/", 1)[1] for m in r.json().get("models", [])
            if "generateContent" in m.get("supportedGenerationMethods", [])]


def _version_key(m):
    nums = [float(x) for x in __import__("re").findall(r"\d+(?:\.\d+)?", m)]
    return (("lite" not in m and "preview" not in m and "exp" not in m), nums)


def resolve_model(preferred=None, key=None):
    """Pick the first model that is listed for this key AND answers a tiny test call.
    Order: preferred -> curated fallbacks -> any other Flash model, newest first."""
    preferred = preferred or MODEL
    avail = list_models(key)
    others = sorted([m for m in avail if "flash" in m and m not in FALLBACK_MODELS
                     and not any(x in m for x in NON_TEXT)], key=_version_key, reverse=True)
    global PROBES
    PROBES = []
    for m in dict.fromkeys([preferred] + FALLBACK_MODELS + others):
        if m not in avail or m == "auto":
            continue
        t0 = time.time()
        try:
            call_gemini("Reply with the word ok.", key=key, model=m, retries=2, timeout=150)
            PROBES.append({"model": m, "ok": True, "seconds": round(time.time() - t0, 1)})
            return m, avail
        except LLMError as e:
            PROBES.append({"model": m, "ok": False, "seconds": round(time.time() - t0, 1), "error": str(e)[:160]})
        if len(PROBES) >= 6:
            break
    raise LLMError(f"no usable Gemini model; probes {PROBES}; available {avail[:20]}")


PROBES = []


def call_gemini(prompt, schema=None, system=None, key=None, model=None, temperature=0.0, retries=5, timeout=240):
    key = key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise LLMError("GEMINI_API_KEY not set")
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature}}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    if schema:
        body["generationConfig"].update({"responseMimeType": "application/json", "responseSchema": schema})
    m = model or MODEL
    if m.startswith("gemini-3") or "latest" in m:
        # Labelling needs little reasoning; low thinking keeps latency/cost down. Dropped if the model rejects it.
        body["generationConfig"]["thinkingConfig"] = {"thinkingLevel": "low"}
    wait, last = 4, ""
    for attempt in range(retries):
        try:
            r = requests.post(API.format(m=m), params={"key": key}, json=body, timeout=timeout)
        except requests.exceptions.RequestException as e:  # timeouts / dropped connections are retryable
            last = f"network {type(e).__name__}"
            time.sleep(wait); wait = min(wait * 2, 90); continue
        if r.status_code == 400 and "thinking" in r.text.lower() and "thinkingConfig" in body["generationConfig"]:
            body["generationConfig"].pop("thinkingConfig")
            continue
        if r.status_code == 200:
            try:
                parts = r.json()["candidates"][0]["content"]["parts"]
                txt = "".join(p["text"] for p in parts if "text" in p and not p.get("thought"))
                return json.loads(txt) if schema else txt
            except Exception as e:
                raise LLMError(f"bad response: {e}: {r.text[:300]}")
        if r.status_code == 429 and "perday" in r.text.lower().replace(" ", "").replace("_", ""):
            raise ProviderExhausted(f"Gemini daily quota: {r.text[:200]}")  # no point retrying today
        if r.status_code in (429, 500, 503):
            last = f"HTTP {r.status_code}: {r.text[:300]}"
            time.sleep(wait); wait = min(wait * 2, 90); continue
        if r.status_code == 404:
            raise ProviderExhausted(f"HTTP 404: {r.text[:300]}")
        raise LLMError(f"HTTP {r.status_code}: {r.text[:300]}")
    raise ProviderExhausted(f"gave up after {retries} retries; last error {last}")


def code_items(items, key=None, model=None):
    """items: list of {id, text, title?, source?}. Returns list of coded dicts."""
    lines = []
    for it in items:
        t = (it.get("title", "") + " | " if it.get("title") else "") + it["text"]
        lines.append(json.dumps({"id": it["id"], "source": it.get("source", "user_input"), "text": t[:2500]},
                                ensure_ascii=False))
    prompt = "Code each item:\n" + "\n".join(lines)
    out = call_gemini(prompt, BATCH_SCHEMA, SYSTEM, key=key, model=model)
    byid = {o.get("id"): o for o in out if isinstance(o, dict)}
    return [byid.get(it["id"]) for it in items]


# ---------------------------------------------------------------------------------------------
# Secondary provider: Groq (free tier, OpenAI-compatible). Used automatically when Gemini hits its
# daily quota or is unavailable. Every coded row records which model produced it, and the golden
# set is scored per model, so a mixed-model corpus stays auditable.
GROQ_API = "https://api.groq.com/openai/v1"
GROQ_PREFERRED = ["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "moonshotai/kimi-k2-instruct",
                  "meta-llama/llama-4-maverick-17b-128e-instruct", "openai/gpt-oss-20b",
                  "meta-llama/llama-4-scout-17b-16e-instruct"]
GROQ_BATCH = 6  # free-tier tokens-per-minute is small; smaller requests avoid 413/429


def _enum_spec():
    lines = []
    for k, v in ITEM_SCHEMA["properties"].items():
        if "enum" in v:
            lines.append(f'"{k}": one of {v["enum"]}')
        elif v.get("type") == "ARRAY":
            lines.append(f'"{k}": array, each one of {v["items"]["enum"]}')
        else:
            lines.append(f'"{k}": {v["type"].lower()}')
    return "\n".join(lines)


GROQ_JSON = ('\n\nOutput format: return ONLY a JSON object {"items": [...]} with one object per input item. '
             "Each object has exactly these keys and allowed values:\n" + _enum_spec())


def normalize(o):
    """Repair schema drift (a model without native schema enforcement can emit an unknown enum value).
    Out-of-vocabulary values fall back to unknown/none/neutral; repairs are listed in _repaired."""
    if not isinstance(o, dict):
        return None
    fixed = []
    for k, v in ITEM_SCHEMA["properties"].items():
        val = o.get(k)
        if "enum" in v:
            if val not in v["enum"]:
                fb = next(x for x in ("unknown", "none", "neutral", v["enum"][-1]) if x in v["enum"])
                fixed.append(k); o[k] = fb
        elif v.get("type") == "ARRAY":
            ok = v["items"]["enum"]
            arr = [x for x in (val if isinstance(val, list) else [val] if val else []) if x in ok]
            if arr != val:
                fixed.append(k)
            o[k] = arr or [ok[-1]]
        elif v.get("type") == "BOOLEAN":
            if not isinstance(val, bool):
                fixed.append(k); o[k] = str(val).lower() == "true"
        elif v.get("type") == "NUMBER":
            try:
                o[k] = max(0.0, min(1.0, float(val)))
            except (TypeError, ValueError):
                fixed.append(k); o[k] = 0.0
        else:
            o[k] = "" if val is None else str(val)
    if fixed:
        o["_repaired"] = fixed
    return o


def groq_models(key=None):
    key = key or os.getenv("GROQ_API_KEY")
    try:
        r = requests.get(f"{GROQ_API}/models", headers={"Authorization": f"Bearer {key}"}, timeout=60)
    except requests.exceptions.RequestException as e:
        raise ProviderExhausted(f"Groq models network {type(e).__name__}")
    if r.status_code != 200:
        raise ProviderExhausted(f"Groq models HTTP {r.status_code}: {r.text[:200]}")
    return [m["id"] for m in r.json().get("data", []) if m.get("active", True)]


def call_groq(prompt, system, model, key=None, retries=5, timeout=180):
    key = key or os.getenv("GROQ_API_KEY")
    body = {"model": model, "temperature": 0, "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system + GROQ_JSON}, {"role": "user", "content": prompt}]}
    if "gpt-oss" in model:
        body["reasoning_effort"] = "low"
    last = ""
    for attempt in range(retries):
        try:
            r = requests.post(f"{GROQ_API}/chat/completions", json=body, timeout=timeout,
                              headers={"Authorization": f"Bearer {key}"})
        except requests.exceptions.RequestException as e:
            last = f"network {type(e).__name__}"; time.sleep(5 * (attempt + 1)); continue
        if r.status_code == 400 and "reasoning" in r.text.lower() and "reasoning_effort" in body:
            body.pop("reasoning_effort"); continue
        if r.status_code == 200:
            try:
                out = json.loads(r.json()["choices"][0]["message"]["content"])
            except Exception as e:
                raise LLMError(f"Groq bad response: {e}")
            return out.get("items", out) if isinstance(out, dict) else out
        if r.status_code == 413:
            raise LLMError("Groq request too large")  # caller splits the batch
        if r.status_code == 429:
            wait = float(r.headers.get("retry-after", 20) or 20)
            if wait > 120 or "per day" in r.text.lower():
                raise ProviderExhausted(f"Groq {model} daily limit: {r.text[:200]}")
            last = f"HTTP 429"; time.sleep(wait + 1); continue
        if r.status_code in (500, 502, 503):
            last = f"HTTP {r.status_code}"; time.sleep(10 * (attempt + 1)); continue
        if r.status_code in (401, 403, 404):
            raise ProviderExhausted(f"Groq {model} HTTP {r.status_code}: {r.text[:200]}")
        raise LLMError(f"Groq HTTP {r.status_code}: {r.text[:200]}")
    raise ProviderExhausted(f"Groq {model} gave up; last {last}")


def code_items_groq(items, model, key=None):
    if len(items) > GROQ_BATCH:
        return sum((code_items_groq(items[i:i + GROQ_BATCH], model, key)
                    for i in range(0, len(items), GROQ_BATCH)), [])
    lines = [json.dumps({"id": it["id"], "source": it.get("source", "user_input"),
                         "text": ((it.get("title", "") + " | ") if it.get("title") else "") + it["text"][:2500]},
                        ensure_ascii=False) for it in items]
    try:
        out = call_groq("Code each item:\n" + "\n".join(lines), SYSTEM, model, key)
    except LLMError as e:
        if "too large" in str(e) and len(items) > 1:
            h = len(items) // 2
            return code_items_groq(items[:h], model, key) + code_items_groq(items[h:], model, key)
        raise
    byid = {o.get("id"): o for o in (out if isinstance(out, list) else []) if isinstance(o, dict)}
    return [byid.get(it["id"]) for it in items]


# Router: Gemini first, then Groq models. Exhausted providers are dropped for the rest of the run.
CHAIN, SWITCHES = [], []


def build_chain(provider=None):
    """provider: auto | gemini | groq (env LLM_PROVIDER). Returns the ordered list of (provider, model)."""
    provider = (provider or os.getenv("LLM_PROVIDER") or "auto").lower()
    CHAIN.clear()
    if provider in ("auto", "gemini") and os.getenv("GEMINI_API_KEY"):
        try:
            CHAIN.append(("gemini", resolve_model()[0]))
        except LLMError as e:
            SWITCHES.append({"skipped": "gemini", "reason": str(e)[:200]})
    if provider in ("auto", "groq") and os.getenv("GROQ_API_KEY"):
        try:
            avail = groq_models()
            CHAIN.extend(("groq", m) for m in GROQ_PREFERRED if m in avail)
        except LLMError as e:
            SWITCHES.append({"skipped": "groq", "reason": str(e)[:200]})
    if not CHAIN:
        raise LLMError(f"no usable provider (provider={provider}); {SWITCHES}")
    return list(CHAIN)


def label(prov, m):
    return m if prov == "gemini" else f"groq:{m}"


def code_items_auto(items):
    """Returns (coded_list, model_label). Falls through the chain; quota/retired -> drop provider."""
    if not CHAIN:
        build_chain()
    errors = []
    for prov, m in list(CHAIN):
        try:
            out = code_items(items, model=m) if prov == "gemini" else code_items_groq(items, m)
            return [normalize(o) if o else None for o in out], label(prov, m)
        except ProviderExhausted as e:
            CHAIN.remove((prov, m))
            SWITCHES.append({"dropped": label(prov, m), "reason": str(e)[:200], "time": time.strftime("%H:%M:%S")})
            print("switching provider:", label(prov, m), "->", str(e)[:120])
        except LLMError as e:  # one bad batch: try the next provider for this batch only
            errors.append(f"{label(prov, m)}: {str(e)[:120]}")
    raise LLMError(f"all providers failed for this batch: {errors or SWITCHES[-3:]}")
