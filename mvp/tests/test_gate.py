"""The gate must pass every template answer and catch the classic failures."""
from mvp.core import engine as E, gate, template


def facts(direction="down", attribution="market", hist=True, manual=False):
    f = {"months": 6, "monthly_amount": "₹4,000", "invested": "₹24,000", "value": "₹23,140", "gain": "-₹860",
         "gain_abs": "₹860", "direction": direction, "gain_pct": -3.6, "as_of": "30 Oct 2026",
         "path": "manual" if manual else "fund", "fund_name": "" if manual else "Parag Parikh Flexi Cap Fund - Direct Plan - Growth",
         "category_name": "diversified equity"}
    f["compare"] = {"available": False, "reason": "no fund chosen"} if manual else {
        "available": True, "attribution": attribution, "market_label": "the market (Nifty 50)", "market_value": "₹23,400",
        "market_gain": "-₹600", "market_gain_abs": "₹600", "market_direction": "down",
        "category_label": "broad market index (Nifty 500)", "category_value": "₹23,300", "category_gain": "-₹700",
        "category_gain_abs": "₹700", "category_direction": "down", "fund_vs_category": "-₹160", "fund_vs_category_abs": "₹160"}
    f["history"] = {"available": True, "series": "this fund", "since_year": 2013, "past_starts": 140, "red_in_10": 3,
                    "red_pct": 27, "horizons": [{"month": 24, "red_starts_seen": 30, "above_in_10": 8, "not_above_in_10": 2, "above_pct": 81},
                                                {"month": 36, "red_starts_seen": 28, "above_in_10": 9, "not_above_in_10": 1, "above_pct": 89}]} if hist else {"available": False}
    return E.finish(f)


def test_templates_always_pass():
    for d in ("down", "up", "flat"):
        for a in ("market", "fund", "both", "close", "not_red"):
            for h in (True, False):
                for man in (True, False):
                    f = facts(d, a, h, man)
                    ok, res = gate.check(template.answer(f), f)
                    assert ok, (d, a, h, man, res, template.answer(f))


def good():
    return {"normal": "You have put in ₹24,000 over 6 months. It is worth ₹23,140 today. About 3 in 10 past SIPs looked like this.",
            "market_or_fund": "Most of the dip is the market. The same SIP in the broad market index (Nifty 500) would be worth ₹23,300.",
            "patience": "About 8 in 10 were above by month 24. The past cannot promise what happens next."}


def test_good_answer_passes():
    f = facts(); f.pop("say")  # hand-written answer; the completeness rule is tested separately
    ok, res = gate.check(good(), f)
    assert ok, res


def failing(field, text):
    a = good(); a[field] = text
    ok, res = gate.check(a, facts())
    return not ok, {n: (p, d) for n, p, d in res}


def test_catches_new_number():
    bad, r = failing("normal", "You put in ₹24,000 and lost 12% this year.")
    assert bad and not r["numbers_match"][0]


def test_catches_advice():
    for t in ("You should keep investing.", "Consider switching to an index fund.", "Stay invested and it will recover.",
              "This is a good fund, so don't stop."):
        bad, r = failing("patience", t + " The past cannot promise what happens next.")
        assert bad and not r["no_advice"][0], t


def test_catches_other_fund_name():
    bad, r = failing("market_or_fund", "HDFC funds did better than yours.")
    assert bad and not r["no_advice"][0]


def test_catches_pressure():
    bad, r = failing("normal", "Don't panic about the crash.")
    assert bad and not r["no_pressure"][0]


def test_requires_uncertainty_line():
    bad, r = failing("patience", "About 8 in 10 were above by month 24.")
    assert bad and not r["complete"][0]


def test_catches_jargon_and_long_sentences():
    bad, r = failing("normal", "Your XIRR is negative.")
    assert bad and not r["plain_words"][0]
    bad, r = failing("normal", " ".join(["word"] * 30) + ".")
    assert bad and not r["plain_words"][0]


def test_catches_loss_called_gain():
    # Found in eval run 1 (writer-v1, case M04): a loss described as "a gain of ₹1,639".
    bad, r = failing("normal", "You have put in ₹24,000. It is worth ₹23,140, a gain of ₹860.")
    assert bad and not r["numbers_match"][0]


def test_catches_field_names():
    # Found in eval run 1: raw field names such as not_above_in_10 and "attribution" leaked into answers.
    bad, r = failing("market_or_fund", "The attribution is not_red for your fund.")
    assert bad and not r["plain_words"][0]


def test_catches_false_common_claim():
    # Found in eval run 2 (writer-v2): "a dip like this is common" when only 2 in 10 past SIPs were red.
    f = facts(); f["history"]["red_in_10"] = 2
    a = good(); a["normal"] = "You have put in ₹24,000. It is ₹860 less. A dip like this is common at this stage."
    ok, res = gate.check(a, f)
    assert not ok and not dict((n, p) for n, p, _ in res)["numbers_match"]


def test_catches_dip_talk_when_green():
    f = facts(direction="up")
    a = good(); a["normal"] = "You have put in ₹24,000. A dip like this happens."
    ok, _ = gate.check(a, f)
    assert not ok


def test_catches_dropped_facts():
    # Found in eval run 4 (writer-v4): the AI dropped prepared sentences, e.g. the depth-of-drop line.
    ok, res = gate.check(good(), facts())
    assert not ok and not dict((n, p) for n, p, _ in res)["complete"]


def test_v6_label_follows_shown_number():
    # Found in human review of writer-v5: "about 1 in 10" was called "rare" in some answers, "happens" in others.
    f = facts(); f["history"].update(deep_share_pct=8, deep_in_10=1, deep_rare=False)
    assert "rare" not in template.meaning(f)
    f["history"].update(deep_share_pct=3, deep_in_10=0, deep_rare=True)
    assert "rare" in template.meaning(f)


def test_v6_no_repeated_horizon_line():
    # Found in human review of writer-v5: "all of them by month 24. By month 36, it was all of them."
    f = facts()
    for x in f["history"]["horizons"]:
        x["above_in_10"] = 10
    p = template.patience(f)
    assert p.count("all of them") == 1 and "still true at month 36" in p


def test_v6_typed_numbers_do_not_contradict():
    # Found in human review of writer-v5: part 1 used the market, part 2 said "we can only compare with the market".
    f = facts(manual=True)
    assert "compare with the market" not in template.market_or_fund(f)
    assert template.normal(f).count("Nifty 50") == 1


def test_v6_index_shown_against_money_put_in():
    a = template.market_or_fund(facts())
    assert "less than you put in" in a
