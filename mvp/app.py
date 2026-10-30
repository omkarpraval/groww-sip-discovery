"""'Is this normal for me?' — prototype for first-time SIP investors whose SIP is in the red.
Explains the user's own numbers; never recommends a fund or an action. Not investment advice."""
import os, sys
from datetime import date

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mvp.core import data as D, engine as E  # noqa: E402
from mvp.core.explain import explain  # noqa: E402

st.set_page_config(page_title="Is this normal for me?", page_icon="🧭", layout="centered")
for k in ("GEMINI_API_KEY", "GROQ_API_KEY", "GEMINI_MODEL", "GROQ_MODEL"):
    try:
        if k in st.secrets and not os.getenv(k):
            os.environ[k] = st.secrets[k]
    except Exception:  # noqa: BLE001  (no secrets file locally)
        pass

BLUE, ORANGE, GREY, INK, MUTED = "#0072B2", "#D55E00", "#8A8F98", "#1B1F24", "#5B616B"
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stApp {{ font-family: 'Inter', sans-serif; color: {INK}; }}
.stApp {{ background: #F6F7F9; }}
.block-container {{ max-width: 520px; padding-top: 1.2rem; padding-bottom: 4rem; }}
h1 {{ font-size: 1.55rem !important; line-height: 1.25 !important; font-weight: 700 !important; }}
.tag {{ display:inline-block; font-size:.75rem; color:{MUTED}; background:#E9ECF0; border-radius:99px; padding:3px 10px; }}
.card {{ background:#fff; border:1px solid #E3E6EA; border-radius:16px; padding:18px 18px 14px; margin:12px 0; }}
.card h3 {{ font-size:1.05rem; margin:0 0 8px; font-weight:600; }}
.card p {{ font-size:1rem; line-height:1.55; margin:0 0 8px; }}
.qnum {{ font-size:.75rem; color:{MUTED}; letter-spacing:.04em; text-transform:uppercase; margin-bottom:2px; }}
.big {{ display:flex; gap:12px; flex-wrap:wrap; }}
.big div {{ flex:1 1 120px; }}
.big .lbl {{ font-size:.8rem; color:{MUTED}; }}
.big .val {{ font-size:1.3rem; font-weight:700; }}
.dots {{ font-size:1.35rem; letter-spacing:3px; margin:4px 0 2px; }}
.dots .on {{ color:{ORANGE}; }} .dots .off {{ color:#D3D7DD; }} .dots .up {{ color:{BLUE}; }}
.cap {{ font-size:.85rem; color:{MUTED}; }}
.bar {{ margin:8px 0 2px; font-size:.9rem; }}
.track {{ background:#EEF0F3; border-radius:6px; height:14px; position:relative; overflow:visible; }}
.fill {{ height:14px; border-radius:6px; }}
.mark {{ position:absolute; top:-4px; width:2px; height:22px; background:{INK}; }}
.badge {{ border-radius:12px; padding:10px 12px; font-size:.9rem; margin:12px 0 4px; }}
.badge.ok {{ background:#E6F2F9; border:1px solid {BLUE}; }}
.badge.std {{ background:#F0F1F3; border:1px solid {GREY}; }}
.opt {{ background:#fff; border:1px solid #E3E6EA; border-radius:14px; padding:14px; margin:8px 0; }}
.opt b {{ font-size:1rem; }} .opt div {{ font-size:.92rem; line-height:1.5; margin-top:4px; }}
.notice {{ font-size:.85rem; color:{MUTED}; border-top:1px solid #E3E6EA; padding-top:10px; margin-top:18px; }}
div.stButton > button {{ border-radius:12px; min-height:46px; font-weight:600; width:100%; }}
@media (max-width: 480px) {{ .block-container {{ padding-left: 14px; padding-right: 14px; }} }}
</style>""", unsafe_allow_html=True)

NOTICE = "This explains your own numbers using public fund prices. It is not investment advice."
EXAMPLES = {  # real public prices, replayed as they stood on that date
    "Small-cap SIP, month 5 (as on 3 Mar 2025)": dict(code=118778, y=2024, m=10, day=5, amt=3000, as_of=date(2025, 3, 3)),
    "Flexi-cap SIP, month 6 (as on 20 Jun 2022)": dict(code=122639, y=2022, m=1, day=10, amt=5000, as_of=date(2022, 6, 20)),
    "Mid-cap SIP behind its index, month 12 (as on 3 Mar 2026)": dict(code=120841, y=2025, m=3, day=5, amt=2000, as_of=date(2026, 3, 3)),
}

st.markdown('<span class="tag">Prototype · first-time SIP investors</span>', unsafe_allow_html=True)
st.title("Is this normal for me?")
st.markdown("Your SIP is in the red. See how SIPs like yours usually look at this stage, whether it is the market or "
            "your fund, and what patience has looked like before. **No login, PAN or account details.**")


@st.cache_data(ttl=3600, show_spinner=False)
def cached_search(q):
    return D.search(q)


@st.cache_data(ttl=3600, show_spinner=False)
def fund_facts(code, y, m, day, amt, as_of):
    return E.facts_from_fund(code, y, m, day, amt, as_of=as_of)


@st.cache_data(ttl=3600, show_spinner=False)
def manual_facts(inv, val, months):
    return E.facts_from_manual(inv, val, months)


# ---------------------------------------------------------------- inputs
mode = st.radio("How do you want to start?", ["Find my fund", "Type my numbers", "Try an example"], horizontal=True,
                label_visibility="collapsed")
req = None
today = date.today()
if mode == "Find my fund":
    q = st.text_input("Your fund's name", placeholder="e.g. flexi cap, small cap, bluechip")
    res = cached_search(q) if q else []
    if q and not res:
        st.info("We couldn't find that fund. Try fewer words, or choose **Type my numbers**.")
    if res:
        pick = st.selectbox("Pick your fund", res, format_func=lambda f: f["schemeName"])
        c1, c2 = st.columns(2)
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        y = c1.selectbox("Started in (year)", list(range(today.year, today.year - 6, -1)))
        m = c2.selectbox("Month", list(range(1, 13)), index=max(0, today.month - 5) if y == today.year else 0,
                         format_func=lambda i: months[i - 1])
        c3, c4 = st.columns(2)
        amt = c3.number_input("Monthly amount (₹)", min_value=100, max_value=200000, value=2000, step=100)
        day = c4.number_input("SIP date (day of month)", min_value=1, max_value=28, value=5)
        req = ("fund", pick["schemeCode"], y, m, int(day), float(amt), None)
elif mode == "Type my numbers":
    c1, c2 = st.columns(2)
    inv = c1.number_input("Total put in so far (₹)", min_value=100, value=12000, step=500)
    val = c2.number_input("Worth today (₹)", min_value=0, value=11400, step=100)
    n = st.slider("Months since your first instalment", 1, 24, 6)
    req = ("manual", float(inv), float(val), int(n))
else:
    ex = st.radio("Pick an example", list(EXAMPLES), label_visibility="collapsed")
    e = EXAMPLES[ex]
    st.caption("Examples replay a real fund's public prices as they stood on that date.")
    req = ("example", e)

go = st.button("Explain my SIP", type="primary", disabled=req is None)
if go:
    st.session_state.pop("result", None)
    with st.spinner("Reading public prices and writing your answer…"):
        try:
            if req[0] == "fund":
                f = fund_facts(*req[1:])
            elif req[0] == "manual":
                f = manual_facts(*req[1:])
            else:
                e = req[1]
                f = fund_facts(e["code"], e["y"], e["m"], e["day"], float(e["amt"]), e["as_of"])
            st.session_state["result"] = explain(f, timeout=20)
        except D.DataError as ex:
            st.error(f"We couldn't work this out: {ex}. You can choose **Type my numbers** instead.")


# ---------------------------------------------------------------- results
def dots(k, cls="on"):
    k = max(0, min(10, int(k)))
    return f'<div class="dots"><span class="{cls}">{"●" * k}</span><span class="off">{"●" * (10 - k)}</span></div>'


def bar_row(label, gain, biggest, colour):
    """Diverging bar: the centre line is what you put in; left = below it, right = above it."""
    w = abs(gain) / (biggest or 1) * 50
    left = 50 - w if gain < 0 else 50
    sign = "−" if gain < 0 else "+"
    return (f'<div class="bar">{label}: <b>{sign}{E.inr(abs(gain))}</b><div class="track"><div class="fill" '
            f'style="position:absolute;left:{left:.1f}%;width:{max(w, 0.6):.1f}%;background:{colour}"></div>'
            f'<div class="mark" style="left:50%"></div></div></div>')


r = st.session_state.get("result")
if r:
    f, a = r["facts"], r["answer"]
    sign = "−" if f["direction"] == "down" else ("+" if f["direction"] == "up" else "")
    colour = ORANGE if f["direction"] == "down" else BLUE
    head = f"<div class='cap'>{f.get('fund_name') or 'Your SIP'} · as of {f['as_of']}</div>" if f.get("fund_name") else f"<div class='cap'>Your SIP · {f['months']} months</div>"
    st.markdown(f"""<div class="card">{head}<div class="big">
      <div><div class="lbl">You put in</div><div class="val">{f['invested']}</div></div>
      <div><div class="lbl">Worth today</div><div class="val">{f['value']}</div></div>
      <div><div class="lbl">Difference</div><div class="val" style="color:{colour}">{sign}{f['gain_abs']}</div></div>
    </div><div class="cap">{f['months']} monthly instalments of {f['monthly_amount']}</div></div>""", unsafe_allow_html=True)

    h = f["history"]
    if h.get("available") and f["direction"] == "down" and h.get("deep_in_10") is not None:
        k = 0 if h.get("deep_rare") else h["deep_in_10"]
        vis = dots(k) + f"<div class='cap'>● = past SIPs with a drop this big or bigger at month {f['months']}, out of 10</div>"
    elif h.get("available"):
        vis = dots(h["red_in_10"]) + f"<div class='cap'>● = past SIPs below what was put in at month {f['months']}, out of 10</div>"
    else:
        vis = ""
    st.markdown(f'<div class="card"><div class="qnum">1 of 3</div><h3>Is this normal for my stage?</h3>{vis}<p>{a["normal"]}</p></div>',
                unsafe_allow_html=True)

    c = f["compare"]
    vis = ""
    if c.get("available"):
        rows = [("Your SIP", f["_val"], colour)]
        if c.get("_cat") is not None:
            rows.append(("Same SIP in the category index", c["_cat"], GREY))
        if c.get("_mkt") is not None:
            rows.append(("Same SIP in the market (Nifty 50)", c["_mkt"], GREY))
        gains = [(l, v - f["_inv"], col) for l, v, col in rows]
        big = max(abs(g) for _, g, _ in gains)
        vis = "".join(bar_row(l, g, big, col) for l, g, col in gains)
        vis += (f"<div class='cap'>Centre line = what you put in ({f['invested']}). Bars to the left are below it,"
                f" bars to the right are above it.</div>")
    st.markdown(f'<div class="card"><div class="qnum">2 of 3</div><h3>Is it the market or my fund?</h3>{vis}<p style="margin-top:10px">{a["market_or_fund"]}</p></div>',
                unsafe_allow_html=True)

    vis = ""
    if h.get("available") and h.get("horizons"):
        hz = h["horizons"][0]
        vis = dots(hz["above_in_10"], "up") + f"<div class='cap'>● = of past SIPs red at month {f['months']}, above what was put in by month {hz['month']}, out of 10</div>"
    st.markdown(f'<div class="card"><div class="qnum">3 of 3</div><h3>What does patience look like?</h3>{vis}<p>{a["patience"]}</p></div>',
                unsafe_allow_html=True)

    if r["source"] == "ai":
        st.markdown('<div class="badge ok">✓ <b>Checked</b>: numbers match your data · no advice · plain words</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="badge std">● <b>Standard answer</b>: built directly from your numbers</div>', unsafe_allow_html=True)
    with st.expander("How this answer was checked"):
        names = {"numbers_match": "Every number comes from your data", "no_advice": "No advice, no fund names, no predictions",
                 "no_pressure": "No fear or urgency words", "complete": "All three answers, with what the past can't tell",
                 "plain_words": "Short sentences, no jargon"}
        if r["checks"]:
            for n, ok, _ in r["checks"]:
                st.markdown(f"{'✓' if ok else '✗'} {names.get(n, n)}")
        if r["source"] == "template":
            st.caption("The AI's wording didn't pass every check (or the AI was unavailable), so you are seeing the "
                       "standard answer, built directly from your numbers.")
        m = r.get("meta") or {}
        st.caption(f"Writer: {m.get('model', '—')} · {m.get('prompt_version', '')} · prices: {f.get('price_source')}")

    st.subheader("Your options")
    st.caption("Shown side by side so you can see what each one does. None of them is a suggestion.")
    opts = [("Skip one instalment", "You keep the units you own. Only the next instalment is skipped.",
             "One skip at a time. Three skips in a row cancel the SIP."),
            ("Change the amount or date", "You keep your units. Future instalments use the new amount or date.",
             "If the next instalment is within 2 working days, the change starts after it."),
            ("Cancel the SIP", "You keep the units you own. No more instalments are taken.",
             "No cancellation charge. You can start a new SIP later.")]
    for t, what, note in opts:
        st.markdown(f'<div class="opt"><b>{t}</b><div>{what}</div><div class="cap">{note}</div></div>', unsafe_allow_html=True)
    st.caption("Rules as described on Groww's help pages; check the app for the latest. Banks may charge for a failed auto-debit.")

st.markdown(f'<div class="notice">{NOTICE} Prices: public AMFI data via mfapi.in. Comparisons use index-tracking '
            f'prices. A prototype for a product-management project; not affiliated with any fund house or app.</div>',
            unsafe_allow_html=True)
