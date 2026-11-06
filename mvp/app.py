"""'Is this normal for me?': a prototype for first-time SIP investors whose SIP is in the red.
Explains the user's own numbers; never recommends a fund or an action. Not investment advice."""
import html, json, os, sys
from datetime import date

import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mvp.core import data as D, engine as E  # noqa: E402
from mvp.core.explain import explain  # noqa: E402
from mvp.core import ask as ASK  # noqa: E402

st.set_page_config(page_title="Is this normal for me?", page_icon="🧭", layout="centered")
for k in ("GEMINI_API_KEY", "GROQ_API_KEY", "GEMINI_MODEL", "GROQ_MODEL"):
    try:
        if k in st.secrets and not os.getenv(k):
            os.environ[k] = st.secrets[k]
    except Exception:  # noqa: BLE001  (no secrets file locally)
        pass

INK, PINE, VER, GRN, GRND, MUTED = "#0E2A2B", "#1F4A4B", "#D55E00", "#009E73", "#00704F", "#5C6F6E"
DISP = "'Bricolage Grotesque','Bricolage Grotesque 96pt ExtraBold','Inter',sans-serif"
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700;12..96,800&family=Inter:wght@400;500;600;700&family=Kalam:wght@400;700&display=swap');
html, body, [class*="css"], .stApp {{ font-family:'Inter',sans-serif; color:{INK}; }}
.stApp {{ background-color:#F2F5F3; background-image: radial-gradient(circle, #D3DDD9 1px, transparent 1.3px); background-size:22px 22px; }}
.block-container, [data-testid="stMainBlockContainer"] {{ max-width:600px; padding-top:1.2rem; padding-bottom:4rem; }}
header[data-testid="stHeader"] {{ background:transparent; }}
h1, h2, h3 {{ font-family:{DISP} !important; letter-spacing:-.02em; }}
/* hero: the SIP path */
.hero {{ position:relative; margin:4px 0 6px; }}
.hero svg {{ width:100%; height:auto; display:block; overflow:visible; }}
.hero .line {{ stroke-dasharray:700; stroke-dashoffset:700; animation: draw 1.8s .2s cubic-bezier(.6,.1,.2,1) forwards; }}
.hero .zone {{ opacity:0; animation: fade .8s 1.2s forwards; }}
.hero .here {{ opacity:0; animation: fade .6s 1.7s forwards; }}
@keyframes draw {{ to {{ stroke-dashoffset:0; }} }}
@keyframes fade {{ to {{ opacity:1; }} }}
.hero h1 {{ font-size:2.35rem !important; line-height:1 !important; font-weight:800 !important; margin:4px 0 6px !important; padding:0 !important; color:{INK}; }}
.hero .sub {{ font-size:1.05rem; color:{PINE}; line-height:1.45; max-width:30em; }}
.promise {{ display:flex; gap:16px; flex-wrap:wrap; margin:12px 0 4px; padding:0; list-style:none; font-size:.86rem; font-weight:600; color:{PINE}; }}
.promise li {{ display:flex; align-items:center; gap:6px; }}
.promise li:before {{ content:""; width:8px; height:8px; border-radius:50%; background:{GRN}; box-shadow:0 0 0 3px rgba(0,158,115,.18); }}
.panel-title {{ font-family:{DISP}; font-size:1.15rem; font-weight:700; margin:18px 0 6px; }}
/* segmented control (radio), old + new Streamlit markup */
[data-testid="stRadio"] div[role="radiogroup"] {{ gap:4px !important; background:#E1E9E6; padding:4px; border-radius:14px; display:flex; flex-wrap:wrap; }}
[data-testid="stRadio"] div[role="radiogroup"] > label, [data-testid="stRadio"] div[role="radiogroup"] label[data-testid="stRadioOption"] {{ flex:1 1 auto; justify-content:center; margin:0 !important; padding:9px 10px !important; border-radius:10px; transition: background .2s, box-shadow .2s; cursor:pointer; }}
[data-testid="stRadio"] div[role="radiogroup"] > div {{ flex:1 1 auto; display:flex; }}
[data-testid="stRadio"] div[role="radiogroup"] > div > label {{ width:100%; justify-content:center; }}
[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked), [data-testid="stRadio"] div[role="radiogroup"] label[data-selected="true"] {{ background:#fff; box-shadow:0 2px 10px rgba(14,42,43,.12); }}
[data-testid="stRadio"] div[role="radiogroup"] > label > div:first-child, [data-testid="stRadio"] div[role="radiogroup"] label[data-testid="stRadioOption"] > div > div:first-child {{ display:none !important; }}
[data-testid="stRadio"] div[role="radiogroup"] p {{ font-weight:600; font-size:.92rem; color:{INK}; }}
/* the example list is a second radio: make it a list of choices */
.st-key-ex div[role="radiogroup"] {{ flex-direction:column; background:transparent; padding:0; gap:6px !important; }}
.st-key-ex div[role="radiogroup"] label {{ justify-content:flex-start !important; background:#fff; border:1.5px solid #D3DDDA; }}
.st-key-ex div[role="radiogroup"] label[data-selected="true"], .st-key-ex div[role="radiogroup"] > label:has(input:checked) {{ border-color:{GRN}; box-shadow:0 0 0 3px rgba(0,158,115,.15); }}
div[data-testid="stTextInput"] input, div[data-testid="stNumberInput"] input {{ border-radius:12px; }}
[data-testid="stButton"], .stElementContainer:has([data-testid="stButton"]) {{ width:100% !important; }}
[data-testid="stButton"] button, div.stButton > button {{ width:100% !important; border-radius:16px; min-height:52px; font-weight:700; transition: transform .15s, box-shadow .2s; }}
[data-testid="stButton"] button[kind="primary"], [data-testid="stBaseButton-primary"] {{ background:{INK}; color:#fff; border:0; box-shadow:0 10px 24px -10px rgba(14,42,43,.6); font-family:{DISP}; font-size:1.05rem; letter-spacing:.01em; }}
[data-testid="stButton"] button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover {{ background:{GRND}; color:#fff; }}
[data-testid="stFormSubmitButton"] button {{ background:{INK} !important; color:#fff !important; border:0 !important; border-radius:12px !important; min-height:42px; font-weight:700; }}
div.stButton > button:active {{ transform: scale(.98); }}
button:disabled, button[disabled] {{ opacity:.45 !important; box-shadow:none !important; }}
.st-key-help, .st-key-help [data-testid="stButton"] {{ width:auto !important; }}
.st-key-help button {{ width:auto !important; min-height:34px !important; border-radius:99px !important; padding:2px 14px !important; background:#fff !important; border:1.5px solid #D3DDDA !important; font-size:.85rem !important; color:{INK} !important; float:right; }}
.ask-head {{ margin:26px 0 8px; }} .ask-head b {{ font-family:{DISP}; font-size:1.35rem; display:block; letter-spacing:-.01em; }} .ask-head span {{ font-size:.9rem; color:{MUTED}; }}
.ask-card {{ margin:14px 0; animation: askin .35s ease; }}
@keyframes askin {{ from {{ opacity:0; transform:translateY(8px); }} to {{ opacity:1; transform:none; }} }}
.ask-card .q {{ margin-left:auto; max-width:85%; width:fit-content; background:{INK}; color:#fff; border-radius:18px 18px 4px 18px; padding:9px 14px; font-weight:600; }}
.ask-card .a {{ margin-top:8px; max-width:94%; background:#fff; border:1.5px solid #D3DDDA; border-radius:18px 18px 18px 4px; padding:12px 14px; }}
.ask-card .a p {{ margin:6px 0 8px; line-height:1.55; }}
.ask-card .foot {{ font-size:.76rem; color:{MUTED}; }}
.ask-card .foot.ok {{ color:{GRND}; font-weight:600; }}
.ichip {{ display:inline-block; font-size:.72rem; font-weight:700; background:#DDF1E9; color:{GRND}; border-radius:99px; padding:2px 9px; margin:0 4px 2px 0; }}
.ichip.blk {{ background:#F8E4D6; color:#A84700; }}
.notice {{ font-size:.8rem; color:{MUTED}; border-top:1.5px solid {INK}; padding-top:10px; margin-top:22px; line-height:1.5; }}
.tour-art {{ background:{INK}; border-radius:20px; padding:16px 18px 18px; color:#fff; margin-bottom:12px; min-height:160px; position:relative; overflow:hidden; }}
.tour-art .k {{ font-size:.82rem; color:#8FD9C0; font-weight:600; }}
.tour-art .big {{ font-family:{DISP}; font-size:1.4rem; font-weight:800; line-height:1.2; margin-top:2px; }}
.tour-art .row {{ display:flex; gap:8px; margin-top:12px; flex-wrap:wrap; }}
.tour-art .chipx {{ background:rgba(255,255,255,.1); border:1px solid rgba(255,255,255,.18); border-radius:12px; padding:7px 10px; font-size:.84rem; }}
.tour-dots {{ display:flex; gap:6px; justify-content:center; margin:6px 0 2px; }}
.tour-dots i {{ width:8px; height:8px; border-radius:99px; background:#C9D3D0; display:block; transition: all .25s; }}
.tour-dots i.on {{ width:22px; background:{GRN}; }}
.tour-p {{ font-size:.98rem; line-height:1.55; }}
[data-testid="stCaptionContainer"] {{ color:{MUTED}; }}
.promise li {{ margin:0 !important; padding:0 !important; }}
.promise {{ row-gap:6px; }}
.st-key-help [data-testid="stButton"] button, .st-key-help div.stButton > button {{ width:auto !important; min-height:34px !important; border-radius:99px !important; padding:2px 14px !important; background:#fff !important; border:1.5px solid #D3DDDA !important; color:{INK} !important; }}
.st-key-help p {{ font-size:.85rem !important; font-weight:600; }}
.st-key-help {{ margin-left:auto; }}
[data-testid="stBaseButton-primary"] p, [data-testid="stButton"] button[kind="primary"] p {{ font-family:{DISP}; font-size:1.08rem; font-weight:700; }}
.st-key-ex div[role="radiogroup"] > div, .st-key-ex div[role="radiogroup"] label {{ width:100%; }}
.st-key-sugg button {{ background:#fff !important; border:1.5px solid #D3DDDA !important; border-radius:99px !important; color:{INK} !important; }}
.st-key-sugg button:hover {{ border-color:{GRN} !important; color:{GRND} !important; }}
.st-key-sugg button p {{ font-size:.86rem; font-weight:600; }}

@media (prefers-reduced-motion: reduce) {{ .hero .line, .hero .zone, .hero .here {{ animation:none !important; stroke-dashoffset:0; opacity:1; }} }}
@media (max-width: 480px) {{ .block-container {{ padding-left:14px; padding-right:14px; }} .hero h1 {{ font-size:2rem !important; }} }}
</style>""", unsafe_allow_html=True)

NOTICE = "This explains your own numbers using public fund prices. It is not investment advice."
EXAMPLES = {  # real public prices, replayed as they stood on that date
    "Small-cap SIP, month 5 (as on 3 Mar 2025)": dict(code=118778, y=2024, m=10, day=5, amt=3000, as_of=date(2025, 3, 3)),
    "Flexi-cap SIP, month 6 (as on 20 Jun 2022)": dict(code=122639, y=2022, m=1, day=10, amt=5000, as_of=date(2022, 6, 20)),
    "Mid-cap SIP behind its index, month 12 (as on 3 Mar 2026)": dict(code=120841, y=2025, m=3, day=5, amt=2000, as_of=date(2026, 3, 3)),
}

HERO = f"""<div class="hero"><svg viewBox="0 0 560 120" role="img" aria-label="A SIP's value dips below what was put in, then climbs back">
<defs><clipPath id="hz-up"><rect x="0" y="0" width="560" height="52"/></clipPath><clipPath id="hz-dn"><rect x="0" y="52" width="560" height="80"/></clipPath></defs>
<path class="zone" d="M8,50 C70,44 110,58 160,74 S250,104 300,92 S400,40 452,30 S530,14 552,10 L552,52 L8,52Z" fill="{GRN}" fill-opacity=".16" clip-path="url(#hz-up)"/>
<path class="zone" d="M8,50 C70,44 110,58 160,74 S250,104 300,92 S400,40 452,30 S530,14 552,10 L552,52 L8,52Z" fill="{VER}" fill-opacity=".16" clip-path="url(#hz-dn)"/>
<line x1="0" x2="560" y1="52" y2="52" stroke="{INK}" stroke-opacity=".4" stroke-dasharray="3 5"/>
<text x="556" y="70" text-anchor="end" font-size="13" fill="{MUTED}" font-family="Inter">what you put in</text>
<path class="line" d="M8,50 C70,44 110,58 160,74 S250,104 300,92 S400,40 452,30 S530,14 552,10" fill="none" stroke="{INK}" stroke-width="3.5" stroke-linecap="round"/>
<g class="here"><circle cx="246" cy="98" r="7" fill="{VER}" stroke="#fff" stroke-width="2.5"/>
<text x="196" y="18" font-family="Kalam, cursive" font-size="20" fill="{VER}">you are here</text>
<path d="M232,26 C236,48 240,70 244,86" fill="none" stroke="{VER}" stroke-width="2"/></g></svg>
<h1>Is this normal for me?</h1>
<div class="sub">Your first SIP is in the red. Get three plain answers about it, in your own rupees.</div>
<ul class="promise"><li>No login or PAN</li><li>Your own numbers</li><li>Never advice</li></ul></div>"""
st.markdown(HERO, unsafe_allow_html=True)

# ---------------------------------------------------------------- first-time tour
TOUR = [
    ("What this is", "Your SIP is in the red. Is that normal?",
     ["① Is this normal for my stage?", "② Is it the market or my fund?", "③ What does patience look like?"],
     "Three plain answers about <b>your own numbers</b>, using real past prices."),
    ("How to start", "Three ways in, no login",
     ["Find my fund", "Type my numbers", "Try an example"],
     "Pick your fund, or type what you put in and what it's worth. No PAN or account numbers."),
    ("How to read it", "Pictures, not jargon",
     ["10 people = 10 past SIPs", "Centre line = what you put in", "Time machine = the past, not a forecast"],
     "Tap ▶ to see where past SIPs were later, tap dotted words for a meaning, and open “How was this calculated?” for the method."),
    ("What it won't do", "No advice. No predictions. No pressure.",
     ["✓ Checked answers", "Choices side by side", "You decide"],
     "Automatic checks block advice, fund tips and scary words before you see an answer."),
]


@st.dialog("A 30-second tour", width="small")
def tour():
    i = st.session_state.get("tour_i", 0)
    tag, big, chips, body = TOUR[i]
    chips_html = "".join(f'<span class="chipx">{c}</span>' for c in chips)
    dots_html = "".join(f'<i class="{"on" if j == i else ""}"></i>' for j in range(len(TOUR)))
    st.markdown(f"""<div class="tour-art"><div class="k">{i + 1} of {len(TOUR)}: {tag}</div>
      <div class="big">{big}</div><div class="row">{chips_html}</div></div>
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
if helpcol.button("How it works", key="help"):
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
st.markdown('<div class="panel-title">Start with your SIP</div>', unsafe_allow_html=True)
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
    ex = st.radio("Pick an example", list(EXAMPLES), label_visibility="collapsed", key="ex")
    e = EXAMPLES[ex]
    st.caption("Examples replay a real fund's public prices as they stood on that date.")
    req = ("example", e)

go = st.button("Explain my SIP", type="primary", disabled=req is None)
# round-2 user test (P3): an old result stayed on screen after switching to another way in. A result is now
# shown only while the inputs that produced it are still the ones on screen.
req_key = repr(req)
if st.session_state.get("result_req") != req_key and not go:
    st.session_state.pop("result", None)
    st.session_state.pop("asks", None)
if go:
    st.session_state.pop("result", None)
    st.session_state.pop("asks", None)
    st.session_state["result_req"] = req_key
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
GLOSSARY = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval", "glossary.json"), encoding="utf-8"))
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
    n, asof, src = f["months"], f["as_of"], "Prices are public AMFI NAVs (via mfapi.in)"
    if h.get("available"):
        s1 = (f"We replayed {h['past_starts']} past SIPs in {h['series']}, one starting each month from {h['since_year']}, "
              f"each investing the same amount on the 5th. Then we counted how many were "
              + ("as far down as yours, or further," if f["direction"] == "down" else "below what was put in")
              + f" after {n} months. {src}, up to {asof}."
              + (" This counts only drops as deep as yours, so it is a smaller group than the SIPs in step 3, which "
                 "counts every SIP below what was put in by any amount." if f["direction"] == "down" else ""))
    else:
        s1 = f"There isn't enough price history to compare with past SIPs at month {n}. {src}, up to {asof}."
    if c.get("available"):
        s2 = ("We put the same instalments, on the same dates, into "
              + (f"the {c['category_label']}, the index for {f.get('category_name') or 'funds'} funds like yours, and into "
                 if c.get("category_label") else "")
              + "the market (Nifty 50). Index values come from public prices of funds that track each index, so they can "
                f"differ slightly from the official index. {src}, up to {asof}.")
    elif f["path"] == "manual":
        s2 = "You typed your totals, so we don't know your fund and have nothing fair to compare it with. Pick your fund to see this part."
    else:
        s2 = "Your fund doesn't invest only in shares, so a share-market index wouldn't be a fair yardstick. We left the comparison out."
    hz = h.get("horizons") or []
    if h.get("available") and hz:
        s3 = (f"From the {h['past_starts']} past SIPs, we took every one in the red at month {n}, by any amount (not only "
              f"drops as deep as yours, as in step 1), and checked where they were at "
              + " and ".join(f"month {x['month']} ({x['red_starts_seen']} with known results)" for x in hz)
              + ". Only past SIPs are used; the past can't promise what happens next.")
    else:
        s3 = ""
    banner = ("You typed your numbers, so we don't know your fund. We use past SIPs in the market (Nifty 50) as a guide, "
              "and can't compare your fund with others." if f["path"] == "manual" else "")
    return {
        "method": {"s1": s1, "s2": s2, "s3": s3}, "banner": banner,
        "afford": "This app explains your SIP's numbers. Only you know whether the next instalment fits your budget this month.",
        # round-2 user test (P2): "keep going" was mentioned but had no column, so the table read as "pick an action"
        "compare_choices": {"cols": ["Keep going as is", "Skip one", "Change amount or date", "Cancel"], "rows": [
            ["Next instalment", "Taken as usual", "Not taken", "Taken at the new amount or date*", "Not taken"],
            ["Units you own", "Kept", "Kept", "Kept", "Kept"],
            ["Later instalments", "Continue as before", "Continue as before", "Use the new amount or date", "Stop"],
            ["Watch out", "Nothing changes", "!3 skips in a row cancel the SIP", "*If it's due within 2 working days, the change starts after it", "To restart, you set up a new SIP"]]},
        "summary": {"who": who, "inv": f["_inv"], "val": f["_val"], "dir": f["direction"],
                    "foot": f"{f['months']} monthly instalments of {f['monthly_amount']}"},
        "n": f["months"], "answer": a, "normal": normal, "compare": {"rows": rows}, "paths": paths,
        "options": OPTIONS, "options_note": "Source: rules as described on Groww's help pages (read Oct 2026); check the app for the latest. "
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
    if st.query_params.get("debug") == "1":  # round-2 user test (P3): hide the model line from users
        st.caption(f"Writer: {m.get('model', 'standard answer')} · {m.get('prompt_version', '')} · ask: {ASK.PROMPT_VERSION} · "
                   f"prices: {r['facts'].get('price_source')}")

    # ------------------------------------------------------------ ask about your SIP
    st.markdown('<div class="ask-head"><b>Still unsure? Ask it.</b><span>In your own words, English or Hinglish. '
                'It explains your numbers and choices. It won\'t tell you what to do.</span></div>', unsafe_allow_html=True)
    SUGGEST = ["Is it my fund or the market?", "Should I stop my SIP?", "Kab tak green hoga?",
               "What happens if I skip next month?", "Index matlab kya?"]
    def _pick():
        st.session_state["pending_q"] = st.session_state.get("sugg")
        st.session_state["sugg"] = None
    if hasattr(st, "pills"):
        st.pills("Try one", SUGGEST, key="sugg", on_change=_pick, label_visibility="collapsed")
    else:
        for i, sq in enumerate(SUGGEST):
            if st.button(sq, key=f"sg{i}"):
                st.session_state["pending_q"] = sq
    picked = st.session_state.pop("pending_q", None)
    with st.form("askf", clear_on_submit=True, border=False):
        c1, c2 = st.columns([4, 1])
        typed = c1.text_input("Your question", placeholder="e.g. itna loss normal hai kya?", label_visibility="collapsed")
        sent = c2.form_submit_button("Ask", type="primary")
    question = picked or (typed if sent and typed.strip() else None)
    if st.query_params.get("debug") == "1":
        st.session_state["_runs"] = st.session_state.get("_runs", 0) + 1
        st.caption(f"debug · run {st.session_state['_runs']} · sent={sent} typed={typed!r} picked={picked!r} · "
                   f"asks={len(st.session_state.get('asks', []))} · req={hash(req_key) % 10000}")
    if question:
        with st.spinner("Reading your question…"):
            st.session_state.setdefault("asks", []).insert(0, ASK.ask(question, r["facts"], GLOSSARY, timeout=20))
    NAMES = {"explain_normal": "Is this normal?", "explain_market": "Market or fund", "explain_patience": "Past SIPs",
             "meaning": "Meaning of a word", "choices": "Your choices", "affordability": "Your budget",
             "advice": "Asks what to do (declined)", "prediction": "Asks what will happen (declined)",
             "off_topic": "Outside this app"}
    for a_ in st.session_state.get("asks", [])[:5]:
        chips = "".join(f'<span class="ichip{" blk" if i in ASK.BLOCKED else ""}">{NAMES.get(i, i)}</span>' for i in a_["intents"])
        down = (a_.get("fallback_reason") or "").startswith("AI unavailable")
        badge = ("✓ Checked AI answer" if a_["source"] == "ai" else
                 "Standard answer (AI unavailable)" if down else
                 "Standard answer (the AI text didn't pass a check)" if a_["source"] == "template" else "Fixed safe answer")
        how = "AI understood the question" if a_["router"] == "ai" else "Keyword match (AI unavailable)"
        st.markdown(f'<div class="ask-card"><div class="q">{html.escape(a_["question"])}</div><div class="a"><div>{chips}</div>'
                    f'<p>{html.escape(a_["answer"])}</p><div class="foot{" ok" if a_["source"] == "ai" else ""}">{badge}. {how}. Not investment advice.</div></div></div>',
                    unsafe_allow_html=True)

st.markdown(f'<div class="notice">{NOTICE} Prices: public AMFI data via mfapi.in. Comparisons use index-tracking '
            f'prices. A prototype for a product-management project; not affiliated with any fund house or app.</div>',
            unsafe_allow_html=True)
