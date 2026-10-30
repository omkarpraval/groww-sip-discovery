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
LEAK = re.compile(r"\b[a-z]+_[a-z_0-9]+\b|\battribution\b|\bnot_red\b", re.I)  # raw field names
COMMON = re.compile(r"\b(common|usual|typical|most people|happens often|very normal)\b", re.I)
GAIN_WORDS = re.compile(r"\b(gain(s|ed)?|profit|earned|grew|growth of)\b", re.I)
LOSS_WORDS = re.compile(r"\b(loss|lost|losing|drop(ped)?|fell|less than you put in)\b", re.I)
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
    wrong_dir = []
    if facts.get("direction") == "down" and GAIN_WORDS.search(ans["normal"]):
        wrong_dir.append("calls a loss a gain")
    if facts.get("direction") == "up" and LOSS_WORDS.search(ans["normal"]):
        wrong_dir.append("calls a gain a loss")
    h = facts.get("history", {})
    common_ok = h.get("deep_share_pct", 100) >= 30 if h.get("deep_share_pct") is not None else h.get("red_in_10", 10) >= 3
    if h.get("available") and not common_ok and COMMON.search(ans["normal"]):
        wrong_dir.append("calls a dip common when it was not")
    if facts.get("direction") != "down" and re.search(r"\bdip\b|\bin the red\b", ans["normal"], re.I):
        wrong_dir.append("talks about a dip on a SIP that is not down")
    res.append(("numbers_match", not bad and not wrong_dir,
                "; ".join(([f"not in facts: {bad[:5]}"] if bad else []) + wrong_dir)))

    hits = [m.group(0) for m in ADVICE.finditer(allt)] + [m.group(0) for m in PREDICT.finditer(allt)]
    funds = [m.group(0) for m in FUND_WORDS.finditer(allt) if m.group(0).lower() not in own]
    res.append(("no_advice", not hits and not funds, f"{hits[:4]} {funds[:4]}" if (hits or funds) else ""))

    pr = [m.group(0) for m in PRESSURE.finditer(allt)]
    res.append(("no_pressure", not pr, str(pr[:4]) if pr else ""))

    comp = []
    say = facts.get("say") or {}
    if say:  # every fact the code prepared must reach the user (writer-v4 dropped sentences)
        said = set(norm_num(t) for k in ("your_numbers", "history", "market_or_fund", "patience")
                   for t in NUM.findall(say.get(k, "")))
        shown = set(norm_num(t) for t in NUM.findall(allt))
        missing = sorted(said - shown)
        if missing:
            comp.append(f"leaves out facts {missing[:5]}")
    if facts.get("history", {}).get("available") and facts["history"].get("horizons") and not UNCERTAIN.search(ans["patience"]):
        comp.append("patience answer does not say what the past cannot tell")
    if not facts.get("compare", {}).get("category_label") and re.search(r"\bcategory\b", ans["market_or_fund"], re.I):
        comp.append("talks about a category it did not compare with")
    if not facts.get("compare", {}).get("available") and re.search(r"\b(market|index)\b.*\b(fell|down|dropped|rose|up)\b", ans["market_or_fund"], re.I):
        comp.append("compares with the market without data")
    res.append(("complete", not comp, "; ".join(comp)))

    long_ = [s for s in sentences(allt) if len(s.split()) > 25]
    jar = [m.group(0) for m in JARGON.finditer(allt)] + [m.group(0) for m in LEAK.finditer(allt)]
    res.append(("plain_words", not long_ and not jar,
                (f"{len(long_)} long sentence(s) " if long_ else "") + (f"jargon or field names {jar[:3]}" if jar else "")))
    return all(ok for _, ok, _ in res), res
