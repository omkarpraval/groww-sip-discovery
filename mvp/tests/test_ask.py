"""Ask about your SIP: fixed texts must pass the gate, blocked intents always get the decline."""
from mvp.core import ask, gate
from mvp.tests.test_gate import facts

GLOSS = {"index": "A fixed basket of many companies' shares, used as a yardstick.",
         "Nifty 50": "An index of 50 of India's largest companies."}


def test_fixed_texts_pass_gate():
    f = facts()
    for t in [ask.DECLINE_ADVICE, ask.DECLINE_PREDICT, ask.AFFORD, ask.OFF_TOPIC, *ask.CHOICES.values()]:
        ok, res = ask.check(t, f)
        assert ok, (t, res)


def test_keyword_router_basics():
    assert "advice" in ask.keyword_route("should I stop my SIP?")
    assert "prediction" in ask.keyword_route("will it recover?")
    assert "choices" in ask.keyword_route("what happens if I skip next month")
    assert ask.keyword_route("best credit card?") == ["off_topic"]


def test_advice_always_declined_without_ai(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False); monkeypatch.delenv("GROQ_API_KEY", raising=False)
    r = ask.ask("Should I stop my SIP?", facts(), GLOSS)
    assert "advice" in r["intents"] and ask.DECLINE_ADVICE in r["answer"]
    assert not gate.ADVICE.search(r["answer"].replace(ask.DECLINE_ADVICE, ""))


def test_ai_answer_with_advice_is_rejected(monkeypatch):
    f = facts()
    monkeypatch.setattr(ask.writer, "complete_json", lambda *a, **k: (
        {"intents": ["explain_market", "advice"], "answer": "It is the market, so you should stay invested."}, {}))
    r = ask.ask("is it my fund or the market and should i stop", f, GLOSS)
    assert r["source"] == "template" and "stay invested" not in r["answer"] and ask.DECLINE_ADVICE in r["answer"]


def test_ai_cannot_add_numbers(monkeypatch):
    monkeypatch.setattr(ask.writer, "complete_json", lambda *a, **k: (
        {"intents": ["explain_normal"], "answer": "You are down 37% and that happens 9 in 10 times."}, {}))
    r = ask.ask("is this normal?", facts(), GLOSS)
    assert r["source"] == "template"


def test_ai_non_object_falls_back(monkeypatch):
    for bad in ([], "text", 3, [{"intents": ["advice"], "answer": ""}]):
        monkeypatch.setattr(ask.writer, "complete_json", lambda *a, _b=bad, **k: (_b, {"provider": "x", "model": "y"}))
        r = ask.ask("should I stop my SIP?", facts(), GLOSS)
        assert ask.DECLINE_ADVICE in r["answer"]


def test_keyword_safety_net_adds_advice_decline(monkeypatch):
    monkeypatch.setattr(ask.writer, "complete_json", lambda *a, **k: ({"intents": ["off_topic"], "answer": ""}, {}))
    r = ask.ask("which fund should I buy today", facts(), GLOSS)
    assert "advice" in r["intents"] and ask.DECLINE_ADVICE in r["answer"] and r.get("safety_net")


def test_unasked_topics_are_dropped():
    assert ask.drop_unasked(["explain_normal", "explain_market", "explain_patience"], "is this loss bad") == ["explain_normal"]
    assert ask.drop_unasked(["explain_normal", "explain_market"], "is it normal or is it my fund") == ["explain_normal", "explain_market"]
    assert ask.drop_unasked(["explain_market"], "did small caps fall") == ["explain_market"]


def test_incomplete_ai_answer_uses_template(monkeypatch):
    f = facts()
    monkeypatch.setattr(ask.writer, "complete_json", lambda *a, **k: (
        {"intents": ["explain_normal"], "answer": "Your SIP is below what you put in."}, {}))
    r = ask.ask("is this normal?", f, GLOSS)
    assert r["source"] == "template" and r["fallback_reason"].startswith("incomplete")
