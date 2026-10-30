"""Safe fallback: plain answers built only from the computed facts (no AI)."""


def _plural(n, word):
    return f"{n} {word}" + ("" if n == 1 else "s")


UNCERTAIN = "The past cannot promise what happens next, and markets can stay down for a long time."


def your_numbers(f):
    m = _plural(f["months"], "month")
    if f["direction"] == "down":
        return f"You have put in {f['invested']} over {m}. Today it is worth {f['value']}, which is {f['gain_abs']} less."
    if f["direction"] == "up":
        return f"You have put in {f['invested']} over {m}. Today it is worth {f['value']}, which is {f['gain_abs']} more."
    return f"You have put in {f['invested']} over {m}. Today it is worth about the same, {f['value']}."


def deep_phrase(h):
    if h.get("deep_in_10") is None:
        return ""
    return "fewer than 1 in 10" if h.get("deep_rare") else f"about {h['deep_in_10']} in 10"


def history_line(f):
    """One statistic only. When the SIP is down it is the depth of the user's drop (human review of writer-v3:
    "any loss" understated deep losses); otherwise how often SIPs were below at this stage."""
    h = f["history"]
    if not h.get("available"):
        return "The price history is too short to compare with past SIPs at this stage."
    m = _plural(f["months"], "month")
    # writer-v6 (human review of v5): typed numbers named the market twice and then said "we can only compare
    # with the market once we know your fund". Now the market is named once, as the guide for history only.
    if f["path"] == "manual":
        lead = (f"We do not know your fund, so we use past SIPs in the market (Nifty 50) as a guide. "
                f"Since {h['since_year']}, ")
    else:
        lead = f"Looking at {h['series']} since {h['since_year']}, "
    if f["direction"] == "down" and h.get("deep_in_10") is not None:
        return f"{lead}{deep_phrase(h)} past SIPs had a drop this big or bigger after {m}."
    return f"{lead}about {h['red_in_10']} in 10 past SIPs were below what was put in after {m}."


def meaning(f):
    """The one sentence of interpretation, decided by code from how DEEP the user's drop is (human review of
    writer-v3 found "common" understated deep losses when it was based on any loss)."""
    h = f["history"]
    if f["direction"] != "down" or not h.get("available") or h.get("deep_share_pct") is None:
        return ""
    # writer-v6: the label follows the rounded number the user sees, so "about 1 in 10" never reads "rare"
    # in one answer and "happens" in another (human review of v5).
    if h.get("deep_rare"):
        return "So a drop this deep at this stage was rare in this history."
    if h.get("deep_in_10", 0) >= 3:
        return "So a drop of this size at this stage is common."
    return "So a drop this deep has happened before, but not often."


def _the(label):
    return label if label.startswith("the ") else "the " + label


def normal(f):
    return " ".join(x for x in (your_numbers(f), history_line(f), meaning(f)) if x)


def market_or_fund(f):
    c = f["compare"]
    if not c.get("available"):
        if f["path"] == "manual":
            return ("To see whether your own fund did better or worse than others of its type, pick your fund."
                    " With typed numbers we only know your totals.")
        if c.get("reason", "").startswith("not an equity"):
            return ("Your fund does not invest only in shares, so comparing it with a share-market index would not be"
                    " fair. We have left this comparison out.")
        return "We could not load the index prices to compare right now."
    has_cat = bool(c.get("category_label"))
    lab = _the(c.get("category_label") or c.get("market_label"))
    val = c.get("category_value") or c.get("market_value")
    gap = c.get("fund_vs_category_abs") if has_cat else c.get("fund_vs_market_abs")
    above = c.get("fund_above_category") if has_cat else c.get("fund_above_market")
    gap_line = f" Yours is {gap} {'more' if above else 'less'} than that." if gap and gap != "₹0" else ""
    kind = "the index for its type of fund" if has_cat else "the market"
    # writer-v6: always say where the index itself stands against what was put in, so a reader can check
    # "most of this dip is the market" or "both played a part" (human review of v5).
    idx_gap = c.get("category_gain_abs") if has_cat else c.get("market_gain_abs")
    idx_down = (c.get("category_direction") if has_cat else c.get("market_direction")) == "down"
    if idx_gap and idx_gap != "₹0":
        idx = f"The same SIP in {lab} would be worth {val}, which is {idx_gap} {'less' if idx_down else 'more'} than you put in."
    else:
        idx = f"The same SIP in {lab} would be worth {val}, about what you put in."
    a = c["attribution"]
    lead = {"market": "Most of this dip comes from the market, not your fund.",
            "fund": f"Your fund has done less well than {kind}.",
            "both": "Both the market and your fund played a part.",
            "close": f"Your fund and {kind} moved about the same."}.get(a, "Your SIP is not below what you put in.")
    return f"{lead} {idx}{gap_line}"


def patience_lines(f):
    h = f["history"]
    hz = h.get("horizons") if h.get("available") else None
    if not hz:
        return "The price history is too short to show what usually came next for SIPs like yours."
    return patience(f).replace(" " + UNCERTAIN, "")


def patience(f):
    h = f["history"]
    hz = h.get("horizons") if h.get("available") else None
    if not hz:
        return ("The price history is too short to show what usually came next for SIPs like yours. "
                "The past cannot promise the future either way.")
    a = hz[0]
    def share(k):
        return "all of them" if k == 10 else f"about {k} in 10"
    s = (f"Of past SIPs in the red by any amount at month {f['months']}, {share(a['above_in_10'])} were above"
         f" what was put in by month {a['month']}.")
    if len(hz) > 1:
        b = hz[1]
        # writer-v6: no second line that only repeats the first (human review of v5)
        s += (f" That was still true at month {b['month']}." if b["above_in_10"] == a["above_in_10"]
              else f" By month {b['month']}, it was {share(b['above_in_10'])}.")
    s += " " + UNCERTAIN
    return s


def answer(f):
    return {"normal": normal(f), "market_or_fund": market_or_fund(f), "patience": patience(f)}
