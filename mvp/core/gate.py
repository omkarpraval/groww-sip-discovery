"""Quality gate: five checks every AI answer must pass before a user sees it.
If any check fails the app shows the template answer (template.py) built from the same facts."""
import re

from .engine import norm_num

KEYS = ("normal", "market_or_fund", "patience")

ADVICE = re.compile(
    r"\b(you should|you must|we recommend|i recommend|recommend(ed)?|suggest(ed)?|consider (switching|stopping|"
    r"pausing|moving|selling|redeeming|investing|adding)|switch(ing)? (to|funds?)|buy|sell|redeem (now|it|your)|"
    r"add more|invest more|top[- ]?up|step[- ]?up|keep investing|stay invested|continue (your|the|investing)|"
    r"don.t stop|do not stop|stop your sip|better fund|best fund|good fund|bad fund|right fund|wrong fund|"
    r"wrong choice|mistake|poor choice|exit (the|this|your) fund|hold on|ride it out|best (time|thing))\b", re.I)
PREDICT = re.compile(
    r"\b(will (recover|bounce|go up|grow|rise|come back|turn green|improve|be fine|make)|guarantee[ds]?|sure to|"
    r"certain(ly)?|definitely|bound to|always recover|never lose|risk[- ]free|safe bet|soon recover)\b", re.I)
PRESSURE = re.compile(
    r"\b(hurry|don.t miss|before it.s too late|act (now|fast)|urgent(ly)?|last chance|fomo|panic|crash(ing|ed)?|"
    r"lose everything|regret|missing out|scary|alarming|worrying|disaster)\b", re.I)
JARGON = re.compile(r"\b(xirr|nav|cagr|alpha|beta|drawdown|volatility|benchmark|rolling returns?|sharpe|"
                    r"rupee[- ]cost averaging|standard deviation|expense ratio)\b", re.I)
FUND_WORDS = re.compile(r"\b(parag|parikh|ppfas|quant|nippon|hdfc|icici|sbi|axis|kotak|mirae|tata|uti|dsp|"
                        r"motilal|bandhan|canara|edelweiss|franklin|aditya|invesco|groww|index fund|etf)\b", re.I)
UNCERTAIN = re.compile(r"(past|history|earlier)[^.]*\b(doesn.t|does not|can.t|cannot|won.t|not)\b[^.]*"
                       r"\b(promise|guarantee|predict|tell|mean|say)", re.I)
NUM = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")


def numbers_ok(text, allowed):
    bad = []
    for t in NUM.findall(text):
        n = norm_num(t)
        if n not in allowed:
            bad.append(t)
    return bad


def sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]


def check(ans, facts):
    """Returns (passed: bool, results: list of (check_name, ok, detail))."""
    res = []
    if not isinstance(ans, dict) or not all(isinstance(ans.get(k), str) and ans[k].strip() for k in KEYS):
        return False, [("complete", False, "missing answer text")]
    allowed = set(facts.get("allowed_numbers", []))
    own = (facts.get("fund_name") or "").lower()
    allt = " ".join(ans[k] for k in KEYS)

    bad = numbers_ok(allt, allowed)
    res.append(("numbers_match", not bad, f"not in facts: {bad[:5]}" if bad else ""))

    hits = [m.group(0) for m in ADVICE.finditer(allt)] + [m.group(0) for m in PREDICT.finditer(allt)]
    funds = [m.group(0) for m in FUND_WORDS.finditer(allt) if m.group(0).lower() not in own]
    res.append(("no_advice", not hits and not funds, f"{hits[:4]} {funds[:4]}" if (hits or funds) else ""))

    pr = [m.group(0) for m in PRESSURE.finditer(allt)]
    res.append(("no_pressure", not pr, str(pr[:4]) if pr else ""))

    comp = []
    if facts.get("history", {}).get("available") and facts["history"].get("horizons") and not UNCERTAIN.search(ans["patience"]):
        comp.append("patience answer does not say what the past cannot tell")
    if not facts.get("compare", {}).get("available") and re.search(r"\b(market|index)\b.*\b(fell|down|dropped|rose|up)\b", ans["market_or_fund"], re.I):
        comp.append("compares with the market without data")
    res.append(("complete", not comp, "; ".join(comp)))

    long_ = [s for s in sentences(allt) if len(s.split()) > 25]
    jar = [m.group(0) for m in JARGON.finditer(allt)]
    res.append(("plain_words", not long_ and not jar,
                (f"{len(long_)} long sentence(s) " if long_ else "") + (f"jargon {jar[:3]}" if jar else "")))
    return all(ok for _, ok, _ in res), res
