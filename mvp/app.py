"""'Is this normal for me?' — prototype for first-time SIP investors whose SIP is in the red.
Explains the user's own numbers; never recommends a fund or an action. Not investment advice."""
import json, os, sys
from datetime import date

import streamlit as st
import streamlit.components.v1 as components

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

BLUE, ORANGE, GREY, INK, MUTED = "#0072B2", "#D55E00", "#8A8F98", "#14213D", "#5B6474"
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stApp {{ font-family: 'Inter', sans-serif; color: {INK}; }}
.stApp {{ background: radial-gradient(1200px 500px at 50% -120px, #DCEBF7 0%, #F4F7FB 55%) fixed; }}
.block-container {{ max-width: 580px; padding-top: 1rem; padding-bottom: 4rem; }}
header[data-testid="stHeader"] {{ background: transparent; }}
.hero {{ display:flex; gap:14px; align-items:center; margin: 6px 0 10px; }}
.hero h1 {{ font-size:1.7rem !important; line-height:1.15 !important; font-weight:800 !important; margin:0 !important; padding:0 !important; letter-spacing:-.02em; }}
.hero .sub {{ font-size:.95rem; color:{MUTED}; margin-top:4px; line-height:1.45; }}
.compass {{ width:58px; height:58px; flex:none; filter: drop-shadow(0 6px 14px rgba(20,33,61,.18)); }}
.compass .needle {{ transform-origin: 29px 29px; animation: settle 2.4s cubic-bezier(.3,1.6,.5,1) both; }}
@keyframes settle {{ 0% {{ transform: rotate(-140deg); }} 60% {{ transform: rotate(18deg); }} 100% {{ transform: rotate(0deg); }} }}
.pills {{ display:flex; gap:6px; flex-wrap:wrap; margin: 4px 0 14px; }}
.pill {{ font-size:.74rem; font-weight:600; color:{INK}; background:#fff; border:1px solid #DCE3EC; border-radius:99px; padding:4px 10px; }}
.panel-title {{ font-size:.75rem; letter-spacing:.08em; text-transform:uppercase; color:{MUTED}; font-weight:700; margin: 6px 0 4px; }}
div[role="radiogroup"] {{ gap: 6px !important; background:#E8EDF4; padding:4px; border-radius:14px; display:flex; flex-wrap:wrap; }}
div[role="radiogroup"] > label {{ flex:1 1 auto; justify-content:center; margin:0 !important; padding:8px 10px !important; border-radius:10px; transition: all .2s; }}
div[role="radiogroup"] > label:has(input:checked) {{ background:#fff; box-shadow:0 2px 8px rgba(20,33,61,.12); }}
div[role="radiogroup"] > label > div:first-child {{ display:none; }}
div[role="radiogroup"] p {{ font-weight:600; font-size:.9rem; }}
div[data-testid="stTextInput"] input, div[data-testid="stNumberInput"] input {{ border-radius:12px; }}
[data-testid="stButton"], .stElementContainer:has([data-testid="stButton"]) {{ width:100% !important; }}
[data-testid="stButton"] button, div.stButton > button {{ width:100% !important; border-radius:14px; min-height:48px; font-weight:700; width:100%; transition: transform .15s, box-shadow .2s; }}
[data-testid="stButton"] button[kind="primary"] {{ background: linear-gradient(135deg, {BLUE}, #0A5C8F); border:0; box-shadow: 0 8px 20px rgba(0,114,178,.28); }}
div.stButton > button:active {{ transform: scale(.98); }}
button:disabled, button[disabled] {{ opacity:.45 !important; box-shadow:none !important; filter: grayscale(.4); }}
.notice {{ font-size:.8rem; color:{MUTED}; border-top:1px solid #DCE3EC; padding-top:10px; margin-top:18px; line-height:1.5; }}
.tour-art {{ background: linear-gradient(135deg,#14213D,#0B4F75); border-radius:18px; padding:18px; color:#fff; margin-bottom:12px; min-height:150px; }}
.tour-art .big {{ font-size:1.25rem; font-weight:800; line-height:1.3; }}
.tour-art .row {{ display:flex; gap:8px; margin-top:12px; flex-wrap:wrap; }}
.tour-art .chipx {{ background:rgba(255,255,255,.12); border:1px solid rgba(255,255,255,.2); border-radius:12px; padding:8px 10px; font-size:.82rem; }}
.tour-dots {{ display:flex; gap:6px; justify-content:center; margin: 6px 0 2px; }}
.tour-dots i {{ width:8px; height:8px; border-radius:99px; background:#CFD8E3; display:block; transition: all .25s; }}
.tour-dots i.on {{ width:22px; background:{BLUE}; }}
.tour-p {{ font-size:.97rem; line-height:1.55; }}
@media (max-width: 480px) {{ .block-container {{ padding-left: 14px; padding-right: 14px; }} .hero h1 {{ font-size:1.45rem !important; }} }}
</style>""", unsafe_allow_html=True)

NOTICE = "This explains your own numbers using public fund prices. It is not investment advice."
EXAMPLES = {  # real public prices, replayed as they stood on that date
    "Small-cap SIP, month 5 (as on 3 Mar 2025)": dict(code=118778, y=2024, m=10, day=5, amt=3000, as_of=date(2025, 3, 3)),
    "Flexi-cap SIP, month 6 (as on 20 Jun 2022)": dict(code=122639, y=2022, m=1, day=10, amt=5000, as_of=date(2022, 6, 20)),
    "Mid-cap SIP behind its index, month 12 (as on 3 Mar 2026)": dict(code=120841, y=2025, m=3, day=5, amt=2000, as_of=date(2026, 3, 3)),
}

COMPASS = """<svg class="compass" viewBox="0 0 58 58"><defs><linearGradient id="cg" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="#14213D"/><stop offset="1" stop-color="#0B4F75"/></linearGradient></defs>
<circle cx="29" cy="29" r="28" fill="url(#cg)"/><circle cx="29" cy="29" r="21" fill="none" stroke="#56B4E9" stroke-opacity=".35" stroke-dasharray="2 4"/>
<g class="needle"><path d="M29 9 L34 29 L29 27 L24 29 Z" fill="#56B4E9"/><path d="M29 49 L24 29 L29 31 L34 29 Z" fill="#E69F00"/></g>
<circle cx="29" cy="29" r="3" fill="#fff"/></svg>"""
st.markdown(f"""<div class="hero">{COMPASS}<div><h1>Is this normal for me?</h1>
<div class="sub">Your first SIP is in the red. Get your bearings in three plain answers.</div></div></div>
<div class="pills"><span class="pill">🔒 No login, PAN or account</span><span class="pill">🧾 Your own numbers</span>
<span class="pill">🚫 Never advice</span></div>""", unsafe_allow_html=True)

# ---------------------------------------------------------------- first-time tour
TOUR = [
    ("What this is", "Your SIP is in the red. Is that normal?",
     ["① Is this normal for my stage?", "② Is it the market or my fund?", "③ What does patience look like?"],
     "First SIPs often go below what you put in, and it's hard to tell if that's a problem. This app answers "
     "three questions about <b>your own numbers</b>, using real past prices."),
    ("How to start", "Three ways in, no login",
     ["🔎 Find my fund", "⌨️ Type my numbers", "🎲 Try an example"],
     "Pick your fund and when you started, or just type what you put in and what it's worth today. "
     "We never ask for PAN, account numbers or screenshots."),
    ("How to read it", "Pictures you can read in a glance",
     ["🧍 10 people = 10 past SIPs", "▮ centre line = what you put in", "⏳ time machine = past SIPs over time"],
     "Each answer has a small picture. The <b>time machine</b> lets you press ▶ and watch where past SIPs like yours "
     "were months later. Dotted words open a plain meaning when you tap them."),
    ("What it won't do", "No advice. No predictions. No pressure.",
     ["✓ Checked answers", "⚖️ Choices side by side", "🧭 You decide"],
     "Every answer is checked before you see it: the numbers must match your data, with no advice, fund tips or "
     "scary words. If a check fails, you see a standard answer built straight from your numbers."),
]


@st.dialog("Quick tour · 30 seconds", width="small")
def tour():
    i = st.session_state.get("tour_i", 0)
    tag, big, chips, body = TOUR[i]
    chips_html = "".join(f'<span class="chipx">{c}</span>' for c in chips)
    dots_html = "".join(f'<i class="{"on" if j == i else ""}"></i>' for j in range(len(TOUR)))
    st.markdown(f"""<div class="tour-art"><div style="font-size:.72rem;opacity:.75;letter-spacing:.08em;text-transform:uppercase">
      Step {i + 1} of {len(TOUR)} · {tag}</div><div class="big">{big}</div><div class="row">{chips_html}</div></div>
      <div class="tour-p">{body}</div><div class="tour-dots">{dots_html}</div>""", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if i > 0 and c1.button("Back", key="t_back"):
        st.session_state["tour_i"] = i - 1
        st.rerun(scope="fragment")
    if i == 0 and c1.button("Skip", key="t_skip"):
        st.session_state.update(toured=True, tour_i=0)
        st.rerun()
    last = i == len(TOUR) - 1
    if c2.button("Let's start" if last else "Next", type="primary", key="t_next"):
        if last:
            st.session_state.update(toured=True, tour_i=0)
            st.rerun()
        st.session_state["tour_i"] = i + 1
        st.rerun(scope="fragment")


if not st.session_state.get("toured"):
    tour()
_, helpcol = st.columns([3, 1])
if helpcol.button("❔ How it works", key="help"):
    st.session_state["tour_i"] = 0
    tour()


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
st.markdown('<div class="panel-title">Start here</div>', unsafe_allow_html=True)
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
GLOSSARY = {
    "instalment": "One monthly payment into your SIP.",
    "in the red": "Worth less today than the money you put in.",
    "past SIPs": "SIPs started in each past month, run on real past prices. They show what happened, not what will.",
    "index for its type of fund": "An index holding the same kind of companies your fund buys, like small or large "
                                  "companies. It's a yardstick, not a suggestion.",
    "index": "A fixed basket of many companies' shares, used as a yardstick. It is not a fund suggestion.",
    "Nifty 50": "An index of 50 of India's largest companies. Here it stands for 'the market'.",
    "Nifty 100": "An index of India's 100 largest companies.",
    "Nifty 500": "An index of 500 companies, large and small: a broad view of the market.",
    "Nifty Midcap 150": "An index of 150 medium-sized companies.",
    "Nifty Smallcap 250": "An index of 250 smaller companies. Their prices tend to move up and down more.",
    "units": "Your share of the fund. You keep them unless you sell.",
}
OPTIONS = [
    {"t": "Skip one instalment", "short": "Pause next month only", "what": "You keep the units you own. Only the next instalment is skipped.",
     "note": "One skip at a time. Three skips in a row cancel the SIP."},
    {"t": "Change the amount or date", "short": "Keep going, differently", "what": "You keep your units. Future instalments use the new amount or date.",
     "note": "If the next instalment is within 2 working days, the change starts after it."},
    {"t": "Cancel the SIP", "short": "Stop new instalments", "what": "You keep the units you own. No more instalments are taken.",
     "note": "No cancellation charge. You can start a new SIP later."},
]
CHECK_NAMES = {"numbers_match": "Every number comes from your data", "no_advice": "No advice, no fund names, no predictions",
               "no_pressure": "No fear or urgency words", "complete": "All three answers, with what the past can't tell",
               "plain_words": "Short sentences, no jargon"}
UI = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "results.html"), encoding="utf-8").read()


def ui_data(r):
    f, a = r["facts"], r["answer"]
    h, c = f["history"], f["compare"]
    who = (f"{f['fund_name']} · as of {f['as_of']}" if f.get("fund_name") else f"Your SIP · typed numbers · {f['as_of']}")
    if h.get("available") and f["direction"] == "down" and h.get("deep_in_10") is not None:
        k = 0 if h.get("deep_rare") else h["deep_in_10"]
        normal = {"k": k, "cls": "hit", "rare": k == 0, "cap": f"Out of 10 past SIPs, the orange ones had a drop this big or bigger at month "
                  f"{f['months']}." + (" The pale one means fewer than 1 in 10." if k == 0 else "")}
    elif h.get("available"):
        normal = {"k": h["red_in_10"], "cls": "hit", "cap": f"Out of 10 past SIPs, the orange ones were below what was put "
                  f"in at month {f['months']}."}
    else:
        normal = {"k": None}
    rows = []
    if c.get("available"):
        rows.append({"label": "Your SIP", "gain": f["_val"] - f["_inv"], "you": True})
        if c.get("_cat") is not None:
            rows.append({"label": c["category_label"][0].upper() + c["category_label"][1:], "gain": c["_cat"] - f["_inv"], "you": False})
        if c.get("_mkt") is not None:
            rows.append({"label": "The market (Nifty 50)", "gain": c["_mkt"] - f["_inv"], "you": False})
    paths = f.get("_paths")
    if paths:
        paths = dict(paths, since=h.get("since_year"), series=h.get("series"))
    return {
        "summary": {"who": who, "inv": f["_inv"], "val": f["_val"], "dir": f["direction"],
                    "foot": f"{f['months']} monthly instalments of {f['monthly_amount']}"},
        "n": f["months"], "answer": a, "normal": normal, "compare": {"rows": rows}, "paths": paths,
        "options": OPTIONS, "options_note": "Rules as described on Groww's help pages; check the app for the latest. "
                                             "Banks may charge for a failed auto-debit.",
        "glossary": GLOSSARY, "source": r["source"],
        "checks": [{"name": CHECK_NAMES.get(n, n), "ok": ok} for n, ok, _ in (r.get("checks") or [])],
    }


r = st.session_state.get("result")
if r:
    blob = json.dumps(ui_data(r), ensure_ascii=False, default=str).replace("</", "<\\/")
    page = UI.replace("__DATA__", blob)
    if hasattr(st, "iframe"):  # newer Streamlit: sizes the frame to its content
        st.iframe(page, height="content")
    else:
        components.html(page, height=900, scrolling=True)
    m = r.get("meta") or {}
    st.caption(f"Writer: {m.get('model', 'standard answer')} · {m.get('prompt_version', '')} · prices: {r['facts'].get('price_source')}")

st.markdown(f'<div class="notice">{NOTICE} Prices: public AMFI data via mfapi.in. Comparisons use index-tracking '
            f'prices. A prototype for a product-management project; not affiliated with any fund house or app.</div>',
            unsafe_allow_html=True)
