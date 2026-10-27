"""Gemini client + the coding schema. Shared by the batch pipeline and the live Streamlit app,
so mentors test exactly the same prompt/model that coded the corpus."""
import json, os, time, requests

MODEL = os.getenv("GEMINI_MODEL") if os.getenv("GEMINI_MODEL") not in (None, "", "auto") else "gemini-3.8-flash"
PROMPT_VERSION = "coder-v1.1"
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
- You are NOT giving investment advice; you are only labelling text.
Return a JSON array with one object per input item, same ids, same order."""


class LLMError(Exception):
    pass


# Newest first. Google retires older models for new API keys (run #2 got a 404 on gemini-2.5-flash).
FALLBACK_MODELS = ["gemini-3.8-flash", "gemini-3-flash", "gemini-flash-latest", "gemini-2.5-flash",
                   "gemini-2.5-flash-lite"]


def list_models(key=None):
    """Model ids this key can call with generateContent (used to pick a working model)."""
    key = key or os.getenv("GEMINI_API_KEY")
    r = requests.get("https://generativelanguage.googleapis.com/v1beta/models", params={"key": key, "pageSize": 200},
                     timeout=60)
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
    others = sorted([m for m in avail if "flash" in m and m not in FALLBACK_MODELS], key=_version_key, reverse=True)
    tried = []
    for m in dict.fromkeys([preferred] + FALLBACK_MODELS + others):
        if m not in avail or m == "auto":
            continue
        try:
            call_gemini("Reply with the word ok.", key=key, model=m, retries=2)
            return m, avail
        except LLMError as e:
            tried.append(f"{m}: {str(e)[:120]}")
    raise LLMError(f"no usable Gemini model; tried {tried[:6]}; available {avail[:20]}")


def call_gemini(prompt, schema=None, system=None, key=None, model=None, temperature=0.0, retries=5):
    key = key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise LLMError("GEMINI_API_KEY not set")
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature}}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    if schema:
        body["generationConfig"].update({"responseMimeType": "application/json", "responseSchema": schema})
    wait, last = 4, ""
    for attempt in range(retries):
        r = requests.post(API.format(m=model or MODEL), params={"key": key}, json=body, timeout=180)
        if r.status_code == 200:
            try:
                txt = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(txt) if schema else txt
            except Exception as e:
                raise LLMError(f"bad response: {e}: {r.text[:300]}")
        if r.status_code in (429, 500, 503):
            last = f"HTTP {r.status_code}: {r.text[:300]}"
            time.sleep(wait); wait = min(wait * 2, 90); continue
        raise LLMError(f"HTTP {r.status_code}: {r.text[:300]}")
    raise LLMError(f"gave up after {retries} retries; last error {last}")


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
