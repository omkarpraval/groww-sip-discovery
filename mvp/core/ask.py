"""'Ask about your SIP': a first-timer types their worry in their own words (English, Hinglish, typos, several
questions at once). The AI works out what is being asked and answers ONLY from the user's computed facts, the
glossary and the platform rules. Questions that ask for advice or a prediction get a fixed, polite decline.

Why AI: a fixed FAQ or keyword router misses real phrasing ("sip band karu kya", "is it my fund or the market,
and should I stop?"). The eval compares the AI router with a keyword router on the same golden questions.
Safety: every AI answer goes through the same kind of gate as the main answers; if it fails, or the AI is
unavailable, the user sees a template answer built from the same facts."""
import json, re

from . import gate, writer

PROMPT_VERSION = "ask-v2"
INTENTS = ("explain_normal", "explain_market", "explain_patience", "meaning", "choices", "affordability",
           "advice", "prediction", "off_topic")
BLOCKED = ("advice", "prediction")

CHOICES = {
    "skip": "Skip one instalment: you keep the units you own and only the next instalment is not taken. "
            "Three skips in a row cancel the SIP.",
    "change": "Change the amount or date: you keep your units and later instalments use the new amount or date. "
              "If the next one is due within 2 working days, the change starts after it.",
    "cancel": "Cancel the SIP: you keep the units you own, no more instalments are taken, and there is no charge. "
              "To restart, you set up a new SIP.",
}
DECLINE_ADVICE = ("I can't make that choice for you or pick a fund, because that would be investment advice. "
                  "The choices step shows what skip, change and cancel each do, and a SEBI-registered investment "
                  "adviser can give advice for your situation.")
DECLINE_PREDICT = ("No one can know what markets do next, so I can't say when, or if, your SIP turns green. "
                   "What I can show is what happened to past SIPs, and the past cannot promise what happens next.")
AFFORD = ("Only you know whether the next instalment fits your budget this month. If money is tight, the choices "
          "step shows what skip, change and cancel each do; none of them is a suggestion.")
OFF_TOPIC = "I can only explain your SIP's numbers, words like these, and your choices here."

SYSTEM = """You help a first-time SIP investor understand THEIR OWN numbers. You are NOT an adviser.
Read the QUESTION (it may be English, Hinglish or have typos, and may ask several things) and return JSON:
{"intents": [...], "term": "", "choice": "", "answer": "..."}

intents: ONLY what the question explicitly asks, from this list. Do not add related topics the user did not ask
about. Most questions have exactly one intent; use two only when the question clearly asks two things
(for example "X, and should I Y?"). (ask-v1 added unasked topics such as market and past SIPs to "is this normal?")
- explain_normal: is my loss/dip normal, why is it red, how bad is it
- explain_market: is it the market or my fund, did the index/market fall too, is my fund doing worse
- explain_patience: what happened to past SIPs like mine later
- meaning: what a word means (put the word in "term")
- choices: what skip, change amount/date or cancel DO (put skip, change or cancel in "choice"); pause = skip
- affordability: can't pay, money is tight, lost job, income changed
- advice: asks what to DO or which fund (stop? continue? switch? buy? sell? invest more? is my fund good/bad?)
- prediction: asks what WILL happen (will it recover, when will it be green, will the market fall)
- off_topic: anything not about this SIP

answer: 1-3 short sentences that answer ONLY the explain_*, meaning and choices parts, using ONLY sentences and
numbers from FACTS.say, GLOSSARY or CHOICES (you may shorten or join them). Leave the advice, prediction,
affordability and off_topic parts out; the app adds its own text for those. If nothing is left, answer "".
Rules: no numbers that are not in FACTS.say; never advise, recommend, predict or reassure; no fear or urgency
words; never call a fund good or bad; no field names; plain English even if the question is in Hinglish."""

# keyword router: the non-AI baseline (and the fallback when the AI is unavailable)
KW = [
    ("advice", r"\b(should|shud|kya karu|karu kya|kar du|band kar|stop kar|switch|change (my |the )?fund|which fund|"
               r"better fund|buy|sell|redeem|invest more|continue|good fund|bad fund|kharab)\b"),
    ("prediction", r"\b(will|recover|kab tak|kab hoga|future|next (month|year)|go up|green hoga|fall more)\b"),
    ("affordability", r"\b(afford|job|salary|money is tight|paise nahi|can'?t pay|income)\b"),
    ("choices", r"\b(skip|pause|cancel|change (the )?(amount|date)|stop sip|missed)\b"),
    ("meaning", r"\b(what is|what's|meaning|matlab|mean)\b"),
    ("explain_market", r"\b(market|index|nifty|my fund or)\b"),
    ("explain_patience", r"\b(past|history|later|people like me|pehle)\b"),
    ("explain_normal", r"\b(normal|why|loss|red|down|minus|dip)\b"),
]


def keyword_route(q):
    ql = q.lower()
    found = [name for name, rx in KW if re.search(rx, ql)]
    return found or ["off_topic"]


TERMS = {"nifty 50", "nifty 500", "nifty 100", "nifty midcap 150", "nifty smallcap 250", "index", "sip",
         "instalment", "units", "nav", "xirr", "cagr", "in the red", "past sips", "small-cap", "mid-cap",
         "large-cap", "index fund", "benchmark"}


def _term(q, glossary):
    ql = q.lower()
    for t in sorted(list(glossary) + list(TERMS), key=len, reverse=True):
        if t.lower() in ql:
            return t
    return ""


def _choice(q):
    ql = q.lower()
    for k, rx in (("cancel", r"cancel|band|stop"), ("change", r"change|amount|date|reduce|kam"), ("skip", r"skip|pause|miss")):
        if re.search(rx, ql):
            return k
    return "skip"


def template_parts(intents, facts, q, glossary):
    """The safe answer for each understood part, built only from facts, glossary and rules."""
    say, out = facts.get("say") or {}, []
    if "explain_normal" in intents:
        out.append(" ".join(x for x in (say.get("your_numbers"), say.get("history"), say.get("meaning")) if x))
    if "explain_market" in intents:
        out.append(say.get("market_or_fund", ""))
    if "explain_patience" in intents:
        out.append(say.get("patience", ""))
    if "meaning" in intents:
        t = _term(q, glossary)
        g = {k.lower(): v for k, v in glossary.items()}
        if t and t.lower() in g:
            out.append(f"{t}: {g[t.lower()]}")
        elif t:
            out.append(f"'{t}' isn't used in your answers here, so it isn't explained.")
    if "choices" in intents:
        out.append(CHOICES[_choice(q)])
    return [x for x in out if x]


def tail(intents):
    t = []
    if "affordability" in intents:
        t.append(AFFORD)
    if "advice" in intents:
        t.append(DECLINE_ADVICE)
    if "prediction" in intents:
        t.append(DECLINE_PREDICT)
    if intents == ["off_topic"]:
        t.append(OFF_TOPIC)
    return t


def check(text, facts, defined_term=""):
    """Gate for a free-text answer (the fixed decline and rule texts are checked by the tests)."""
    res = []
    allowed = set(facts.get("allowed_numbers", []))
    bad = gate.numbers_ok(text, allowed)
    res.append(("numbers_match", not bad, f"not in facts: {bad[:5]}" if bad else ""))
    hits = [m.group(0) for m in gate.ADVICE.finditer(text)] + [m.group(0) for m in gate.PREDICT.finditer(text)]
    own = (facts.get("fund_name") or "").lower()
    funds = [m.group(0) for m in gate.FUND_WORDS.finditer(text) if m.group(0).lower() not in own]
    res.append(("no_advice", not hits and not funds, f"{hits[:4]} {funds[:4]}" if (hits or funds) else ""))
    pr = [m.group(0) for m in gate.PRESSURE.finditer(text)]
    res.append(("no_pressure", not pr, str(pr[:4]) if pr else ""))
    jar = [m.group(0) for m in gate.JARGON.finditer(text) if m.group(0).lower() != defined_term.lower()]
    jar += [m.group(0) for m in gate.LEAK.finditer(text)]
    long_ = [s for s in gate.sentences(text) if len(s.split()) > 30]
    res.append(("plain_words", not jar and not long_, f"{jar[:3]} {len(long_)} long" if (jar or long_) else ""))
    return all(ok for _, ok, _ in res), res


def ask(question, facts, glossary, provider=None, timeout=20, keys=None):
    """Returns dict(intents, router, answer, source, checks, ai_answer, meta)."""
    q = (question or "").strip()[:400]
    out = {"question": q, "router": "keyword", "ai_answer": None, "checks": [], "meta": {}, "fallback_reason": None}
    intents, term, ai_text = keyword_route(q), "", None
    payload = {"QUESTION": q, "FACTS": {"say": facts.get("say"), "direction": facts.get("direction"),
                                        "months": facts.get("months")},
               "GLOSSARY": glossary, "CHOICES": CHOICES}
    try:
        res, meta = writer.complete_json(SYSTEM, json.dumps(payload, ensure_ascii=False), provider=provider,
                                         timeout=timeout, keys=keys)
        got = [i for i in (res.get("intents") or []) if i in INTENTS]
        if got:
            intents, out["router"] = got, "ai"
        term = (res.get("term") or "").strip()
        ai_text = (res.get("answer") or "").strip()
        out["meta"] = dict(meta, prompt_version=PROMPT_VERSION)
        out["ai_answer"] = ai_text
    except writer.WriterError as e:
        out["fallback_reason"] = f"AI unavailable: {str(e)[:120]}"
    if any(i != "off_topic" for i in intents):
        intents = [i for i in intents if i != "off_topic"]
    parts_tpl = template_parts(intents, facts, q if not term else term, glossary)
    body, source = " ".join(parts_tpl), "template"
    if ai_text:
        ok, checks = check(ai_text, facts, term or _term(q, glossary))
        out["checks"] = checks
        if ok:
            body, source = ai_text, "ai"
        else:
            out["fallback_reason"] = "failed: " + ", ".join(n for n, p, _ in checks if not p)
    if any(i in intents for i in ("explain_normal", "explain_patience")) and "past cannot promise" not in body:
        if body:
            body += " " + "The past cannot promise what happens next."
    text = " ".join(x for x in [body] + tail(intents) if x).strip()
    out.update(intents=intents, answer=text, source=source if body else "rules")
    return out
