"""SIP Discovery Engine — Live Lab.
Hands-on companion to the public story page (GitHub Pages): run the same AI coder on any text, browse the
verified evidence behind every number, and inspect how the engine is validated. Research only — not advice."""
import html, json, os, re, sys
import pandas as pd
import streamlit as st

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
STORY = "https://omkarpraval.github.io/groww-sip-discovery/"
REPO = "https://github.com/omkarpraval/groww-sip-discovery"

st.set_page_config(page_title="SIP Discovery Engine · Live Lab", page_icon="🔎", layout="wide",
                   initial_sidebar_state="collapsed")


def secret(k):
    try:
        return st.secrets[k]
    except Exception:
        return os.getenv(k)


for _k in ("GEMINI_API_KEY", "GROQ_API_KEY"):
    if secret(_k):
        os.environ[_k] = secret(_k)
try:  # live analysis uses the model that coded the corpus, unless overridden
    _status = json.load(open(os.path.join(ROOT, "outputs", "coder_status.json")))
    os.environ.setdefault("GEMINI_MODEL", secret("GEMINI_MODEL") or _status.get("model") or "auto")
except Exception:
    pass

# ------------------------------------------------------------------ vocabulary (plain English, no codes)
ACT = {"considering_stop": "Considering stopping", "stopped_or_cancelled": "Stopped / cancelled",
       "failed_involuntary": "Debit failed (not by choice)", "paused_or_skipped": "Paused / skipped",
       "redeemed": "Withdrew money", "reduced": "Reduced amount", "continuing": "Continuing", "started": "Started",
       "increased": "Increased", "restarted": "Restarted", "none": "No SIP action"}
RISK = {"considering_stop", "stopped_or_cancelled", "failed_involuntary", "paused_or_skipped", "redeemed", "reduced"}
STAGE = {"considering": "Not started yet", "first_months": "First 3 months", "within_year": "3–12 months in",
         "beyond_year": "Over a year", "unknown": "Not stated"}
FT = {"yes": "Yes", "no": "No", "unknown": "Not stated"}
WHY = {"market_fall_negative_returns": "Portfolio in the red", "underwhelming_returns": "Returns feel too slow",
       "expectation_mismatch": "Expected something else", "cash_flow_squeeze": "Money got tight",
       "payment_mandate_failure": "Debit / mandate failed", "app_ux_or_control_gap": "App friction",
       "platform_trust_doubt": "Doubts the platform", "information_overload_conflict": "Conflicting advice",
       "wrong_fund_doubt": "Doubts own fund choice", "goal_disconnect": "No goal / disengaged",
       "life_event": "Life event", "lock_in_or_tax": "Lock-in or tax", "social_influence": "Others stopped",
       "none": "None stated"}
CHECK = {"daily_or_more": "Daily or more", "weekly": "Weekly", "monthly_statement": "Monthly", "rarely": "Rarely",
         "unknown": "Not stated"}
OUT = {"reddit_forum": "Reddit / forums", "youtube_finfluencer": "YouTube", "friend_family": "Friends & family",
       "advisor_professional": "Advisor", "google_news": "Google / news", "customer_support": "Customer support",
       "amc_or_other_app": "Fund house / other app", "none_stated": "None stated"}
SRC = {"play_store": "Play Store", "app_store": "App Store", "reddit_post": "Reddit", "reddit_comment": "Reddit",
       "tradingqna": "TradingQnA", "youtube": "YouTube"}
FIELD = {"primary_trigger": ("Main reason for stopping", 70), "relevant": ("Is it about a SIP at all?", 90),
         "sip_action": ("What did they do?", 80), "emotion": ("How do they feel?", None),
         "first_time": ("First-time investor?", None)}
E = html.escape

# ------------------------------------------------------------------ design system (matches the story page)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root{--bg:#f5f6f8;--surface:#fff;--surface-2:#f0f2f5;--line:#e3e6ea;--ink:#101418;--ink-2:#47505a;--ink-3:#66707c;
 --accent:#0072B2;--accent-soft:#e6f1f8;--accent-ink:#005a8c;--bar-dim:#a9cde4;
 --good:#00704f;--good-bg:#e2f4ee;--warn:#8a5700;--warn-bg:#fdf1d8;--bad:#a94400;--bad-bg:#fbe7dc;
 --shadow:0 1px 2px rgba(16,20,24,.04),0 4px 16px rgba(16,20,24,.06)}
.stApp,.stApp *:not([data-testid="stIconMaterial"]):not(.material-symbols-rounded):not(code):not(pre){font-family:Inter,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif!important}
.stApp{background:var(--bg)}
header[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"],#MainMenu,footer,
[data-testid="stSidebarCollapsedControl"]{display:none!important}
.block-container{max-width:1120px!important;padding-top:0!important;padding-bottom:64px!important}
h1,h2,h3{letter-spacing:-.02em;color:var(--ink)}
p,li{color:var(--ink-2)}
/* top bar */
.topbar{display:flex;align-items:center;gap:14px;padding:14px 0;border-bottom:1px solid var(--line);margin-bottom:28px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:10px;font-weight:700;color:var(--ink);font-size:16px;text-decoration:none!important}
.brand .dot{width:30px;height:30px;border-radius:9px;background:var(--accent);display:grid;place-items:center}
.topbar .sp{flex:1}
.toplink{font-size:15px;font-weight:600;color:var(--accent-ink)!important;text-decoration:none!important;padding:8px 12px;border-radius:10px}
.toplink:hover{background:var(--surface-2)}
.labtag{font-size:13px;font-weight:700;color:var(--accent-ink);background:var(--accent-soft);padding:4px 10px;border-radius:999px}
/* hero */
.hero h1{font-size:clamp(30px,4.2vw,46px);line-height:1.08;font-weight:800;margin:0 0 12px;padding:0}
.hero h1 em{font-style:normal;color:var(--accent)}
.hero p{font-size:18px;max-width:760px;margin:0 0 18px}
.stats{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:8px}
.stat{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:10px 14px;box-shadow:var(--shadow)}
.stat b{display:block;font-size:20px;font-weight:800;color:var(--ink);font-variant-numeric:tabular-nums;line-height:1.2}
.stat span{font-size:13px;color:var(--ink-3)}
/* segmented nav */
div[data-testid="stSegmentedControl"] button,div[data-testid="stButtonGroup"] button{font-weight:600!important;font-size:15px!important;padding:8px 16px!important}
/* cards */
.card{background:var(--surface);border:1px solid var(--line);border-radius:16px;box-shadow:var(--shadow);padding:22px;margin-bottom:16px}
.card h3{font-size:18px;margin:0 0 4px}
.hint{font-size:14px;color:var(--ink-3);margin:0 0 14px}
.eyebrow{font-size:13px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--accent-ink)}
.badge{display:inline-flex;align-items:center;gap:6px;font-size:14px;font-weight:700;padding:5px 12px;border-radius:999px}
.badge.good{color:var(--good);background:var(--good-bg)} .badge.warn{color:var(--warn);background:var(--warn-bg)}
.badge.bad{color:var(--bad);background:var(--bad-bg)} .badge.info{color:var(--ink-2);background:var(--surface-2)}
.input{font-size:16px;line-height:1.6;background:var(--surface-2);border-radius:12px;padding:14px 16px;margin:12px 0 16px;color:var(--ink)}
.input mark{background:#ffe7a8;border-radius:3px;padding:0 2px;color:inherit}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:12px}
@media(max-width:760px){.grid{grid-template-columns:1fr 1fr}}
.kv{background:var(--surface-2);border-radius:12px;padding:10px 12px}
.kv span{display:block;font-size:12px;font-weight:600;color:var(--ink-3);text-transform:uppercase;letter-spacing:.04em}
.kv b{font-size:15px;color:var(--ink)}
.kv.risk{background:var(--bad-bg)} .kv.risk b{color:var(--bad)}
.pill{display:inline-block;font-size:13px;font-weight:700;padding:3px 10px;border-radius:999px;background:var(--accent-soft);color:var(--accent-ink);margin:0 6px 6px 0}
.row{display:flex;gap:8px 16px;flex-wrap:wrap;align-items:baseline;font-size:15px;color:var(--ink-2);margin-top:4px}
.row b{color:var(--ink)}
.meta{font-size:13px;color:var(--ink-3);margin-top:12px}
.quote{border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:12px;background:var(--surface)}
.quote p{margin:0 0 8px;font-size:16px;color:var(--ink);line-height:1.5}
.quote .tags{display:flex;gap:6px;flex-wrap:wrap;align-items:center;font-size:13px;color:var(--ink-3)}
.tag{font-size:12px;font-weight:600;border-radius:6px;padding:2px 8px;background:var(--surface-2);color:var(--ink-2)}
.ok{color:var(--good);font-weight:600}
.quote a{margin-left:auto;font-weight:600;text-decoration:none;color:var(--accent-ink)}
.need{font-size:14px;color:var(--ink-2);margin:0 0 8px}
.bars .b{display:grid;grid-template-columns:190px 1fr 46px;gap:10px;align-items:center;font-size:14px;margin:6px 0}
.bars .t{height:12px;background:var(--surface-2);border-radius:3px;position:relative}
.bars .t i{position:absolute;inset:0 auto 0 0;background:var(--accent);border-radius:0 3px 3px 0}
.bars .v{text-align:right;font-weight:700;font-variant-numeric:tabular-nums;color:var(--ink)}
.score{width:100%;border-collapse:collapse;font-size:15px}
.score th{font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--ink-3);text-align:left;font-weight:600;padding:0 8px 8px}
.score td{padding:12px 8px;border-top:1px solid var(--line);color:var(--ink)}
.score .n{font-weight:800;font-size:18px;font-variant-numeric:tabular-nums}
.step{display:flex;gap:14px;align-items:flex-start;margin-bottom:14px}
.step .no{flex:none;width:32px;height:32px;border-radius:10px;background:var(--accent);color:#fff;display:grid;place-items:center;font-weight:700}
.step b{color:var(--ink)}
.notice{display:flex;gap:10px;background:var(--warn-bg);color:#5c3b00;border-radius:12px;padding:12px 14px;font-size:14px;margin-top:28px}
.empty{text-align:center;padding:36px 16px;color:var(--ink-3)}
/* streamlit widgets */
.stTextArea textarea{font-size:16px!important;border-radius:12px!important;background:#fff!important}
.stButton>button[kind="primary"]{border-radius:12px;font-weight:700;padding:10px 22px;background:var(--accent);border-color:var(--accent)}
.stButton>button[kind="primary"] p,.stButton>button[kind="primary"] span{color:#fff!important;font-weight:700}
.stButton>button[kind="primary"]:hover{background:var(--accent-ink);border-color:var(--accent-ink)}
div[data-testid="stExpander"]{border-radius:12px;background:#fff}
div[data-testid="stButtonGroup"]>div{flex-wrap:wrap!important}
.score,.score th,.score td{border:none!important}
.score td{border-top:1px solid var(--line)!important}
.score tr{background:transparent!important}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_json(p):
    p = os.path.join(ROOT, p)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


DATA = load_json("docs/data.json") or {}
gold = (DATA.get("golden") or {}).get("primary")

# ------------------------------------------------------------------ top bar + hero
st.markdown(f"""
<div class="topbar">
  <a class="brand" href="{STORY}" target="_blank"><span class="dot"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg></span>SIP Discovery Engine</a>
  <span class="labtag">Live lab</span><span class="sp"></span>
  <a class="toplink" href="{STORY}" target="_blank">← Read the findings</a>
  <a class="toplink" href="{REPO}" target="_blank">Code</a>
</div>""", unsafe_allow_html=True)

F = DATA.get("funnel", {})
stats = ""
if F:
    stats += f'<div class="stat"><b>{F.get("sip", 0):,}</b><span>SIP conversations</span></div>'
    stats += f'<div class="stat"><b>{F.get("early_drops", 0):,}</b><span>first-year drop-off moments</span></div>'
if gold:
    stats += f'<div class="stat"><b>{round(gold["fields"]["primary_trigger"]["agreement"])}%</b><span>agreement with humans on “why”</span></div>'
_m = os.getenv("GEMINI_MODEL", "auto")
_m = "Gemini" if _m == "auto" else "Gemini " + _m.replace("gemini-", "").replace("-latest", "").replace("-", " ").title()
stats += f'<div class="stat"><b>{E(_m)}</b><span>model · Groq as backup</span></div>'
st.markdown(f"""<div class="hero">
<h1>Run the engine on <em>any SIP post</em> — and see the evidence behind every number.</h1>
<p>Paste a review, Reddit post or comment. The same AI and prompt that labelled 8,900 public conversations will read it, explain why the person might stop, and check its own evidence word-for-word.</p>
<div class="stats">{stats}</div></div>""", unsafe_allow_html=True)

nav = st.segmented_control("Section", ["Analyse text", "Explore the evidence", "Validation", "Method"],
                           default="Analyse text", key="nav", label_visibility="collapsed")
nav = nav or "Analyse text"
st.write("")

# ------------------------------------------------------------------ helpers
SAMPLES = {
    "In the red": "Started my first SIP of 2000 in January after my cousin suggested it. Six months later it shows -3% "
                            "and I check it every morning. Thinking of stopping and putting the money in an FD instead.",
    "Autopay failed": "My autopay failed this month and I got a bounce charge with no reminder at all. "
                      "Honestly thinking of cancelling the SIP, this is the second time.",
    "Money tight": "Freelance income has been really low for two months. Should I pause my SIP for a while or keep it going? "
                   "I don't want to lose what I've built.",
    "Hinglish": "Bhai 8 mahine se SIP chal rahi hai par return dikh hi nahi raha, sab kehte hain long term, "
                "par mujhe samajh nahi aa raha ki ye normal hai ya maine galat kiya.",
    "Not a SIP": "The app UI is clean and IPO applications are smooth. Good experience overall.",
}
SAMPLE_NOTE = "Sample inputs were written for this demo; they are not real user posts."


def highlight(text, quote):
    t = E(text)
    q = (quote or "").strip(" .\"'")
    if not q:
        return t
    i = text.lower().find(q.lower())
    if i < 0:
        return t
    return E(text[:i]) + "<mark>" + E(text[i:i + len(q)]) + "</mark>" + E(text[i + len(q):])


def gate(c, text):
    q = (c.get("evidence_quote") or "").lower().strip(" .\"'")
    quote_ok = (not q) or q in text.lower()
    if not c.get("relevant"):
        return "info", "Not about a personal SIP — excluded from counts", quote_ok
    if not quote_ok:
        return "warn", "Needs human review — evidence quote not found in the text", quote_ok
    if c.get("confidence", 0) < 0.6:
        return "warn", "Needs human review — low confidence", quote_ok
    return "good", "Passed quality check — evidence verified word-for-word", quote_ok


def result_card(text, c, model):
    kind, msg, quote_ok = gate(c, text)
    icon = {"good": "✓", "warn": "!", "info": "–"}[kind]
    act = c.get("sip_action", "none")
    why = [WHY.get(t, t) for t in (c.get("triggers") or []) if t != "none"] or ["None stated"]
    outside = [OUT.get(o, o) for o in (c.get("outside_app_action") or []) if o != "none_stated"]
    repaired = c.get("_repaired")
    body = f"""<div class="card">
<span class="badge {kind}">{icon} {E(msg)}</span>
<div class="input">{highlight(text, c.get("evidence_quote")) if quote_ok else E(text)}</div>"""
    if c.get("relevant"):
        body += f"""<div class="grid">
  <div class="kv {'risk' if act in RISK else ''}"><span>What they did</span><b>{E(ACT.get(act, act))}</b></div>
  <div class="kv"><span>Stage</span><b>{E(STAGE.get(c.get('investor_stage'), '—'))}</b></div>
  <div class="kv"><span>First-time?</span><b>{E(FT.get(c.get('first_time'), '—'))}</b></div>
  <div class="kv"><span>Emotion</span><b>{E(str(c.get('emotion', '—')).capitalize())}</b></div>
</div>
<div class="row"><b>Why</b>{''.join(f'<span class="pill">{E(w)}</span>' for w in why)}</div>
<div class="row"><b>Unmet need</b><span>{E(c.get('unmet_need') or '—')}</span></div>"""
        if outside:
            body += f'<div class="row"><b>Went to</b><span>{E(", ".join(outside))}</span></div>'
    body += f"""<div class="meta">{E(model)} · prompt {E(c.get('_prompt', ''))} · confidence {c.get('confidence', 0):.2f}
{' · auto-repaired fields: ' + E(', '.join(repaired)) if repaired else ''}</div></div>"""
    st.markdown(body, unsafe_allow_html=True)


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def analyse(texts):
    """Cached per exact input so repeated demos don't spend quota. Raises on failure (failures aren't cached)."""
    import llm
    batch = [{"id": f"u{i}", "text": t} for i, t in enumerate(texts)]
    out, model = llm.code_items_auto(batch)
    for o in out:
        if o:
            o["_prompt"] = llm.PROMPT_VERSION.replace("coder-", "")
    switches = [s.get("dropped", s.get("skipped", "")) for s in llm.SWITCHES]
    return out, model, switches


# ------------------------------------------------------------------ 1. Analyse
if nav == "Analyse text":
    left, right = st.columns([1.15, 1], gap="large")
    with left:
        st.markdown('<div class="eyebrow">Step 1 · choose or paste text</div>', unsafe_allow_html=True)
        pick = st.pills("Try a sample", list(SAMPLES), selection_mode="single", key="sample",
                        label_visibility="collapsed")
        if pick and st.session_state.get("_last_pick") != pick:
            st.session_state["txt"] = SAMPLES[pick]
            st.session_state["_last_pick"] = pick
        st.session_state.setdefault("txt", SAMPLES["In the red"])
        txt = st.text_area("Text to analyse", key="txt", height=170, max_chars=3000,
                           placeholder="Paste a review, post or comment about a SIP. Separate several items with a blank line.",
                           help="Up to 5 items, separated by a blank line. Don't paste names, phone numbers, PAN or account details.")
        go = st.button("Analyse", type="primary", icon=":material/auto_awesome:")
        st.caption(SAMPLE_NOTE + " Don’t paste personal details.")
    with right:
        st.markdown("""<div class="card"><h3>What you’ll get</h3><p class="hint">For each item, in about 5–15 seconds</p>
<div class="step"><span class="no">1</span><div><b>What they did</b><br><span style="color:var(--ink-2)">continuing, considering stopping, paused, debit failed…</span></div></div>
<div class="step"><span class="no">2</span><div><b>Why — in plain English</b><br><span style="color:var(--ink-2)">up to three reasons, plus the unmet need behind them</span></div></div>
<div class="step"><span class="no">3</span><div><b>A quality check you can see</b><br><span style="color:var(--ink-2)">the quoted evidence must exist word-for-word, or it’s flagged for human review</span></div></div>
</div>""", unsafe_allow_html=True)

    if go:
        items = [t.strip() for t in re.split(r"\n\s*\n", txt or "") if t.strip()][:5]
        if not items:
            st.warning("Paste some text first, or pick a sample above.")
        else:
            st.markdown('<div class="eyebrow" style="margin-top:12px">Step 2 · results</div>', unsafe_allow_html=True)
            try:
                with st.spinner("Reading like a researcher…"):
                    out, model, switches = analyse(tuple(items))
                if switches:
                    st.info("Primary model unavailable right now — the backup model answered. "
                            "Its accuracy is scored separately on the Validation tab.")
                for t, c in zip(items, out):
                    if c:
                        result_card(t, c, model)
                    else:
                        st.markdown(f'<div class="card"><span class="badge warn">! No answer for this item — routed to human review</span>'
                                    f'<div class="input">{E(t)}</div></div>', unsafe_allow_html=True)
            except Exception:
                ex = DATA.get("example")
                st.markdown("""<div class="card"><span class="badge warn">! The live AI is busy or out of free quota right now</span>
<p style="margin:12px 0 0">Safe fallback: nothing is guessed. Below is a real result the engine produced earlier, and every number in
<b>Explore the evidence</b> was computed in advance, so the lab still works. Please try again in a few minutes.</p></div>""",
                            unsafe_allow_html=True)
                if ex:
                    c = {"relevant": True, "sip_action": ex["labels"]["What they did"],
                         "investor_stage": ex["labels"]["Investor stage"], "first_time": ex["labels"]["First-time?"],
                         "emotion": ex["labels"]["Emotion"], "unmet_need": ex["labels"]["Unmet need"],
                         "triggers": [k for k, v in WHY.items() if v in ex["labels"]["Why"]],
                         "evidence_quote": ex["quote"], "confidence": 0.9, "_prompt": ex["prompt"].replace("coder-", "")}
                    result_card(ex["text"], c, ex["model"] + " · cached example")

# ------------------------------------------------------------------ 2. Explore
elif nav == "Explore the evidence":
    @st.cache_data(show_spinner="Loading the labelled corpus…")
    def corpus():
        from aggregate import load, CLUSTERS
        from site_data import FUND  # never surface fund or stock names, even inside quotes
        df = load()
        df = df[df.relevant & df.quote_ok & (df.evidence_quote.str.len() > 0)].copy()
        df = df[~df.evidence_quote.str.contains(FUND) & ~df.unmet_need.fillna("").str.contains(FUND)]
        df["cluster"] = df.triggers.apply(lambda ts: [k for k, v in CLUSTERS.items() if set(ts) & v] or ["No reason stated"])
        df["src"] = df.source.map(SRC).fillna(df.source)
        return df[["id", "src", "url", "evidence_quote", "unmet_need", "emotion", "sip_action", "investor_stage",
                   "first_time", "early", "drop_event", "cluster", "triggers", "engagement"]]

    df = corpus()
    st.markdown("""<div class="eyebrow">Every quote here passed the word-for-word check</div>
<h3 style="margin:4px 0 14px">Browse what people actually said</h3>""", unsafe_allow_html=True)
    f1, f2, f3, f4 = st.columns([1.3, 1, 1, 1])
    clusters = sorted({c for cs in df.cluster for c in cs})
    cl = f1.multiselect("Root cause", clusters, placeholder="All causes")
    srcs = f2.multiselect("Source", sorted(df.src.unique()), placeholder="All sources")
    emos = f3.multiselect("Emotion", sorted(df.emotion.unique()), format_func=str.capitalize, placeholder="Any emotion")
    acts = f4.multiselect("What they did", [a for a in ACT if a in set(df.sip_action)], format_func=ACT.get,
                          placeholder="Any action")
    g1, g2 = st.columns([2.2, 1])
    q = g1.text_input("Search", placeholder="Search words, e.g. “red”, “autopay”, “salary”, “band kar”",
                      label_visibility="collapsed")
    only_early = g2.toggle("First-year investors only", value=True)

    v = df
    if only_early: v = v[v.early]
    if cl: v = v[v.cluster.apply(lambda cs: bool(set(cs) & set(cl)))]
    if srcs: v = v[v.src.isin(srcs)]
    if emos: v = v[v.emotion.isin(emos)]
    if acts: v = v[v.sip_action.isin(acts)]
    if q: v = v[v.evidence_quote.str.contains(re.escape(q), case=False) | v.unmet_need.str.contains(re.escape(q), case=False)]
    v = v.sort_values(["drop_event", "engagement"], ascending=False)  # drop-off moments first

    a, b = st.columns([1, 1.6], gap="large")
    with a:
        n = len(v)
        drop = int(v.drop_event.sum())
        st.markdown(f"""<div class="card"><h3>{n:,} matching posts</h3><p class="hint">{round(100 * drop / n) if n else 0}% describe stopping, pausing or a failed debit — or thinking about it</p>
<div class="bars">{''.join(f'<div class="b"><span>{E(k)}</span><span class="t"><i style="width:{100 * c / max(1, n):.1f}%"></i></span><span class="v">{round(100 * c / max(1, n))}%</span></div>'
                   for k, c in pd.Series([c for cs in v.cluster for c in cs if c != "No reason stated"] or ["-"]).value_counts().head(5).items() if k != "-")}</div>
<p class="hint" style="margin-top:12px">Share of matching posts per root cause (a post can have several)</p></div>""",
                    unsafe_allow_html=True)
        if n:
            st.download_button("Download these rows (CSV)", v.drop(columns=["triggers"]).to_csv(index=False).encode(),
                               "sip_evidence.csv", "text/csv", icon=":material/download:", use_container_width=True)
    with b:
        if not n:
            st.markdown('<div class="card empty">No posts match these filters. Try removing one.</div>', unsafe_allow_html=True)
        else:
            k = "more"
            st.session_state.setdefault(k, 12)
            for r in v.head(st.session_state[k]).itertuples():
                tags = [r.src, str(r.emotion).capitalize(), ACT.get(r.sip_action, r.sip_action)] + list(r.cluster)[:1]
                st.markdown(f"""<div class="quote"><p>“{E(r.evidence_quote)}”</p>
{f'<div class="need">Need: {E(r.unmet_need)}</div>' if r.unmet_need else ''}
<div class="tags">{''.join(f'<span class="tag">{E(t)}</span>' for t in tags)}<span class="ok">✓ verified</span>
<a href="{E(r.url)}" target="_blank">Source ↗</a></div></div>""", unsafe_allow_html=True)
            if n > st.session_state[k]:
                if st.button(f"Show more ({n - st.session_state[k]:,} left)", use_container_width=True):
                    st.session_state[k] += 24
                    st.rerun()

# ------------------------------------------------------------------ 3. Validation
elif nav == "Validation":
    reports = (DATA.get("golden") or {}).get("all", [])
    st.markdown(f"""<div class="eyebrow">Can you trust it?</div>
<h3 style="margin:4px 0 6px">The AI is marked against {DATA.get('golden', {}).get('items', 24)} hand-labelled posts</h3>
<p class="hint">Pass marks were fixed before any scoring. Every model and prompt version is tested on the same set.</p>""",
                unsafe_allow_html=True)

    def badge(a, t):
        if t is None: return '<span class="badge info">Tracked</span>'
        if a >= t: return '<span class="badge good">✓ Pass</span>'
        if a >= t - 5: return '<span class="badge warn">! Just below</span>'
        return '<span class="badge bad">✕ Fail → fixing</span>'

    def name(r):
        m = next(iter(r["models"]), "")
        base = ("Groq " + m.replace("groq:", "").replace("openai/", "")) if m.startswith("groq:") else ("Gemini " + m.replace("gemini-", ""))
        return f'{base} · {r["prompt_version"].replace("coder-", "")}{" (live)" if r["mode"] == "corpus" else ""}'

    if not reports:
        st.markdown('<div class="card empty">Golden-set results not generated yet.</div>', unsafe_allow_html=True)
    else:
        main = gold or reports[0]
        rows = "".join(f'<tr><td>{FIELD[k][0]}</td><td class="n">{round(main["fields"][k]["agreement"])}%</td>'
                       f'<td>{main["fields"][k]["kappa"]}</td><td>{FIELD[k][1] and str(FIELD[k][1]) + "%" or "—"}</td>'
                       f'<td>{badge(main["fields"][k]["agreement"], FIELD[k][1])}</td></tr>'
                       for k in FIELD if k in main["fields"])
        st.markdown(f"""<div class="card"><h3>Scorecard — {E(name(main))}</h3><p class="hint">{main['n']} items scored · κ above 0.6 = substantial agreement</p>
<table class="score"><tr><th>What the AI labels</th><th>Agreement</th><th>Cohen’s κ</th><th>Pass mark</th><th>Result</th></tr>{rows}</table></div>""",
                    unsafe_allow_html=True)
        if len(reports) > 1:
            def cell(r, k):
                f = r["fields"].get(k)
                if not f: return "<td>—</td>"
                t = FIELD[k][1]; ok = None if t is None else f["agreement"] >= t
                col = "var(--good)" if ok else "var(--bad)" if ok is False else "var(--ink)"
                return f'<td class="n" style="color:{col}">{round(f["agreement"])}%{" ✓" if ok else ""}</td>'
            head = "".join(f"<th>{FIELD[k][0]}</th>" for k in FIELD)
            body = "".join(f'<tr><td>{E(name(r))}</td>{"".join(cell(r, k) for k in FIELD)}</tr>' for r in reports)
            st.markdown(f"""<div class="card"><h3>Every model and prompt, same test</h3><p class="hint">Agreement with human labels · ✓ meets the pass mark</p>
<div style="overflow-x:auto"><table class="score"><tr><th>Model · prompt</th>{head}</tr>{body}</table></div></div>""", unsafe_allow_html=True)
        corr = (DATA.get("golden") or {}).get("corrections", [])
        if corr:
            st.markdown('<h3 style="margin:18px 0 10px">Where the AI was wrong — and what changed</h3>', unsafe_allow_html=True)
            cols = st.columns(len(corr))
            for col, c in zip(cols, corr):
                col.markdown(f"""<div class="card"><p style="margin:0 0 12px;color:var(--ink-2)">“{E(c['text'])}”</p>
<div class="row"><b>AI said</b><span style="text-decoration:line-through;color:var(--bad);font-weight:600">{E(ACT.get(c['ai'], c['ai']))}</span></div>
<div class="row"><b>Human said</b><span style="color:var(--good);font-weight:700">{E(ACT.get(c['human'], c['human']))}</span></div>
<p class="hint" style="margin:10px 0 0">Became an explicit rule in prompt v1.2</p></div>""", unsafe_allow_html=True)

# ------------------------------------------------------------------ 4. Method
else:
    Q = DATA.get("quality", {})
    steps = [("Collect", f"{F.get('collected', 0):,} public posts", "Play Store & App Store reviews, Reddit, TradingQnA and YouTube comments since 2024."),
             ("Filter", f"{F.get('sip', 0):,} kept", "Duplicates and personal data removed; SIP-related text kept in English, Hindi and Hinglish."),
             ("AI labels", f"{F.get('coded', 0):,} labelled", "An LLM labels each post against a fixed codebook with structured JSON output."),
             ("Verify", f"{F.get('relevant_ok', 0):,} passed", f"Evidence must exist word-for-word ({Q.get('failed_quote', 0):,} failed and were excluded); scored against a human golden set."),
             ("Aggregate", f"{F.get('early_drops', 0):,} key moments", "Root causes, segments and opportunity scores; the story page refreshes on every run.")]
    a, b = st.columns([1.1, 1], gap="large")
    with a:
        st.markdown('<div class="card"><h3>How the engine works</h3><p class="hint">Five steps, all in a public GitHub repository</p>' +
                    "".join(f'<div class="step"><span class="no">{i}</span><div><b>{s}</b> · <span style="color:var(--accent-ink);font-weight:700">{n}</span><br>'
                            f'<span style="color:var(--ink-2)">{d}</span></div></div>' for i, (s, n, d) in enumerate(steps, 1)) +
                    "</div>", unsafe_allow_html=True)
    with b:
        src = F.get("by_source", [])
        mx = max([s["sip"] for s in src] or [1])
        st.markdown('<div class="card"><h3>Sources</h3><p class="hint">SIP-related posts kept per source</p><div class="bars">' +
                    "".join(f'<div class="b"><span>{E(s["source"])}</span><span class="t"><i style="width:{100 * s["sip"] / mx:.1f}%"></i></span>'
                            f'<span class="v">{s["sip"]:,}</span></div>' for s in src) + "</div></div>", unsafe_allow_html=True)
        st.markdown(f"""<div class="card"><h3>Guardrails</h3>
<div class="row">✓ No fund or stock is ever recommended — the engine only labels text.</div>
<div class="row">✓ Phone, email, PAN and account numbers are stripped before AI sees anything.</div>
<div class="row">✓ Gemini first, Groq as automatic backup; each scored separately.</div>
<div class="row">✓ Every label records its model and prompt version.</div></div>""", unsafe_allow_html=True)
    with st.expander("Read the full codebook"):
        st.markdown(open(os.path.join(ROOT, "prompts", "codebook.md"), encoding="utf-8").read())

st.markdown(f"""<div class="notice"><span>ⓘ</span><span><b>Research tool — not investment advice.</b> It does not recommend any fund or stock.
Quotes are from public posts with personal data removed. Independent student project, not affiliated with any company named.
<a href="{STORY}" target="_blank">Read the full findings →</a></span></div>""", unsafe_allow_html=True)
