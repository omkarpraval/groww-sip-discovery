"""Safe fallback: plain answers built only from the computed facts (no AI)."""


def _plural(n, word):
    return f"{n} {word}" + ("" if n == 1 else "s")


def normal(f):
    m = _plural(f["months"], "month")
    if f["direction"] == "down":
        s = f"You have put in {f['invested']} over {m}. Today it is worth {f['value']}, which is {f['gain_abs']} less."
    elif f["direction"] == "up":
        s = f"You have put in {f['invested']} over {m}. Today it is worth {f['value']}, which is {f['gain_abs']} more."
    else:
        s = f"You have put in {f['invested']} over {m}. Today it is worth about the same, {f['value']}."
    h = f["history"]
    if not h.get("available"):
        return s + " The price history is too short to compare with past SIPs at this stage."
    s += (f" Looking at {h['series']} since {h['since_year']}, about {h['red_in_10']} in 10 SIPs were below what was"
          f" put in after {m}.")
    if h["red_in_10"] >= 3:
        s += " So being in the red at this stage is common."
    elif h["red_in_10"] >= 1:
        s += " So it happens, though less often."
    else:
        s += " Being in the red at this stage was rare in this history."
    return s


def market_or_fund(f):
    c = f["compare"]
    if not c.get("available"):
        if f["path"] == "manual":
            return "We can only compare with the market once we know your fund. Pick your fund to see this part."
        if c.get("reason", "").startswith("not an equity"):
            return ("Your fund is not a pure share fund, so comparing it with a share-market index would not be fair."
                    " We have left this comparison out.")
        return "We could not load the index prices to compare right now."
    lab = c.get("category_label") or c.get("market_label")
    val = c.get("category_value") or c.get("market_value")
    a = c["attribution"]
    if a == "market":
        return (f"Most of this dip comes from the market, not your fund. The same SIP in the {lab} would be worth"
                f" {val}, also below what you put in.")
    if a == "fund" and c.get("category_label"):
        return (f"Your fund has done less well than its category. The same SIP in the {lab} would be worth {val},"
                f" which is {c['fund_vs_category_abs']} more than yours.")
    if a == "fund":
        return f"Your fund has done less well than the market. The same SIP in {lab} would be worth {val}."
    if a == "both":
        extra = f", {c['fund_vs_category_abs']} more than yours" if c.get("fund_vs_category_abs") else ""
        return (f"Both the market and your fund played a part. The same SIP in the {lab} would be worth {val}:"
                f" below what you put in{extra}.")
    if a == "close":
        return f"Your fund and its comparison index moved about the same. The same SIP in the {lab} would be worth {val}."
    return f"Your SIP is not below what you put in. The same SIP in the {lab} would be worth {val}."


def patience(f):
    h = f["history"]
    hz = h.get("horizons") if h.get("available") else None
    if not hz:
        return ("The price history is too short to show what usually came next for SIPs like yours. "
                "The past cannot promise the future either way.")
    a = hz[0]
    def share(k):
        return "all of them" if k == 10 else f"about {k} in 10"
    s = (f"Of the past SIPs that were in the red at month {f['months']}, {share(a['above_in_10'])} were above"
         f" what was put in by month {a['month']}.")
    if len(hz) > 1:
        s += f" By month {hz[1]['month']}, it was {share(hz[1]['above_in_10'])}."
    if a["not_above_in_10"] > 0:
        s += f" About {a['not_above_in_10']} in 10 were still below at month {a['month']}."
    s += " The past cannot promise what happens next, and markets can stay down for a long time."
    return s


def answer(f):
    return {"normal": normal(f), "market_or_fund": market_or_fund(f), "patience": patience(f)}
