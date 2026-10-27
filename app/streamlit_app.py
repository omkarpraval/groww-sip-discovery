"""Groww SIP Continuation — AI Discovery Engine (public demo).
Explore what ~100k public conversations say about why first-time investors stop SIPs, and run the
same AI coder live on any text."""
import json, os, re, sys
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "pipeline"))

st.set_page_config(page_title="SIP Discovery Engine", page_icon="🔎", layout="wide")
# Okabe-Ito palette: distinguishable for common colour-vision deficiencies
OKABE = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00", "#F0E442", "#000000"]
LABEL = {
    "market_fall_negative_returns": "Market fall / portfolio in red", "underwhelming_returns": "Returns feel too slow",
    "expectation_mismatch": "Expected something different", "cash_flow_squeeze": "Cash-flow squeeze",
    "payment_mandate_failure": "Mandate / debit failure", "app_ux_or_control_gap": "App control gap (edit/pause/understand)",
    "platform_trust_doubt": "Doubts the platform", "information_overload_conflict": "Conflicting advice / noise",
    "wrong_fund_doubt": "Doubts own fund choice", "goal_disconnect": "No goal / disengaged", "life_event": "Life event",
    "lock_in_or_tax": "Lock-in / tax", "social_influence": "Social influence",
}


def secret(k):
    try:
        return st.secrets[k]
    except Exception:
        return os.getenv(k)


for _k in ("GEMINI_API_KEY", "GROQ_API_KEY"):
    if secret(_k):
        os.environ[_k] = secret(_k)
# Live analysis uses the same model that coded the corpus (recorded by the pipeline), unless overridden.
try:
    _status = json.load(open(os.path.join(ROOT, "outputs", "coder_status.json")))
    os.environ.setdefault("GEMINI_MODEL", secret("GEMINI_MODEL") or _status.get("model") or "auto")
except Exception:
    pass


@st.cache_data
def load_json(p):
    p = os.path.join(ROOT, p)
    return json.load(open(p)) if os.path.exists(p) else None


ins, funnel, gold = load_json("outputs/insights.json"), load_json("outputs/funnel.json"), load_json("outputs/golden_report.json")

st.title("🔎 SIP Continuation — AI Discovery Engine")
st.caption("Why do first-time mutual fund investors stop their SIPs? Public Play Store, App Store, Reddit, "
           "TradingQnA and YouTube conversations, coded by an LLM against a fixed codebook and validated "
           "against a hand-labelled golden set. Research tool only — **not investment advice.**")

tabs = st.tabs(["① How it works", "② Opportunity map", "③ Segments", "④ Behaviour", "⑤ Try the engine", "⑥ Validation"])

# ---------------------------------------------------------------- 1
with tabs[0]:
    st.subheader("Pipeline")
    st.markdown("""
| Stage | What happens | Why |
|---|---|---|
| **0 · Collect** | Groww Play Store + App Store reviews; Reddit (r/mutualfunds, r/IndiaInvestments, r/personalfinanceindia…); TradingQnA threads; YouTube comments on SIP videos | Reviews show in-app friction; forums show the *thinking* behind stopping |
| **1 · Filter (rules)** | De-duplicate, strip phone/email/PAN, keep SIP/MF-related text (EN + Hindi + Hinglish keywords) | Cheap, transparent, full-corpus counts |
| **2 · Code (LLM)** | Gemini codes each item: stage, action (start/pause/stop…), up to 3 triggers, emotion, checking habit, outside-app action, segment signals, unmet need, verbatim quote, confidence | Turns free text into comparable data |
| **3 · Quality gates** | Evidence quote must appear verbatim in the source, and confidence ≥ 0.6, else → human-review bucket; golden set of hand-labelled items → agreement & Cohen's κ | Catches hallucination and drift |
| **4 · Prioritise** | Per theme: reach × drop-off proximity × first-timer share × addressability | Ranks opportunities that can move 12-month continuation |
""")
    if funnel:
        df = pd.DataFrame(funnel).fillna(0).astype(int)
        df.loc["TOTAL"] = df.sum()
        st.markdown("**Data funnel (items per source)**")
        st.dataframe(df, use_container_width=True)
    if ins:
        f = ins["funnel"]
        c = st.columns(4)
        c[0].metric("AI-coded items", f"{f['coded']:,}")
        c[1].metric("Relevant & passed quality gates", f"{f['relevant_high_conf']:,}")
        c[2].metric("Failed a gate → human review", f"{f['relevant_low_conf_review']:,}")
        c[3].metric("Pause/stop/fail events", f"{f['dropoff_events']:,}")
        st.caption(f"Model: {ins.get('model')} · Prompt: {ins.get('prompt_version')}")
    with st.expander("Codebook (frozen before the full run)"):
        st.markdown(open(os.path.join(ROOT, "prompts", "codebook.md")).read())

# ---------------------------------------------------------------- 2
with tabs[1]:
    if not ins:
        st.info("Engine results not generated yet.")
    else:
        ed = ins.get("early_dropoffs")
        if ed:
            st.subheader("First-time & first-year investors: why do they consider stopping, pause, stop or lapse?")
            m = st.columns(3)
            m[0].metric("First-time / first-year conversations", f"{ed['n_early_relevant']:,}")
            m[1].metric("…describing a drop-off moment", f"{ed['n_early_dropoffs']:,}")
            m[2].metric("Most common emotion there", max(ed["emotion"], key=ed["emotion"].get).title())
            cl = pd.Series(ed["clusters_pct"]).sort_values().rename("% of drop-off moments").reset_index()
            figc = px.bar(cl, x="% of drop-off moments", y="index", orientation="h", text="% of drop-off moments",
                          color_discrete_sequence=[OKABE[0]], height=320, labels={"index": ""})
            figc.update_traces(texttemplate="%{text:.0f}%", textposition="outside")
            st.plotly_chart(figc, use_container_width=True)
            st.caption(f"An item can sit in more than one cluster. No reason stated in {ed['no_reason_stated_pct']}% of drop-off moments. "
                       "Clusters group the codebook triggers (see pipeline/aggregate.py).")
            pick0 = st.selectbox("Read what they said", list(ed["quotes"].keys()), format_func=lambda k: LABEL.get(k, k))
            for q in ed["quotes"][pick0]:
                if q["evidence_quote"]:
                    st.markdown(f"> {q['evidence_quote']}  \n<sub>Need: {q['unmet_need']} · {q['source']} · "
                                f"[source]({q['url']})</sub>", unsafe_allow_html=True)
            st.divider()
        th = pd.DataFrame(ins["themes"])
        th["label"] = th.theme.map(LABEL).fillna(th.theme)
        st.subheader("Which reasons for stopping are big, close to drop-off, early, and in our control?")
        fig = px.scatter(th, x="reach_pct", y="dropoff_proximity_pct", size="early_or_first_time_pct",
                         color="addressability", text="label", color_continuous_scale="Cividis",
                         labels={"reach_pct": "Reach: % of relevant conversations", "dropoff_proximity_pct":
                                 "Drop-off proximity: % that co-occur with pause/stop", "addressability": "Addressability"},
                         height=560)
        fig.update_traces(textposition="top center", textfont_size=13)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Bubble size = share from first-time / first-year investors. Addressability is a documented "
                   "human judgement (can Groww act on it without recommending funds or using fear/FOMO?).")
        show = th[["label", "mentions", "reach_pct", "dropoff_proximity_pct", "early_or_first_time_pct",
                   "sources_present", "addressability", "opportunity_score", "top_emotion"]]
        st.dataframe(show, use_container_width=True, hide_index=True)
        pick = st.selectbox("Drill into a theme", th.label.tolist())
        row = th[th.label == pick].iloc[0]
        a, b = st.columns(2)
        a.markdown("**Unmet needs (top by engagement)**")
        for n in row.top_needs:
            if n: a.markdown(f"- {n}")
        b.markdown("**Evidence (verbatim)**")
        for q in row.quotes:
            if q["evidence_quote"]:
                b.markdown(f"> {q['evidence_quote']}  \n<sub>{q['source']} · [link]({q['url']})</sub>", unsafe_allow_html=True)

# ---------------------------------------------------------------- 3
with tabs[2]:
    if ins:
        st.subheader("Does drop-off differ by segment?")
        st.caption("Only items where the segment was explicitly stated. 'dropoff_pct' = share of those items "
                   "describing a pause / stop / failure / considering stopping.")
        for col, rows in ins["segments"].items():
            d = pd.DataFrame(rows)
            if d.empty: continue
            st.markdown(f"**{col.replace('_', ' ').title()}**")
            d["top_triggers"] = d["top_triggers"].apply(lambda t: ", ".join(f"{LABEL.get(a, a)} ({b})" for a, b in (t or [])))
            st.dataframe(d, use_container_width=True, hide_index=True)
        st.markdown("**Theme mix by stage (% of mentions within each stage)**")
        sx = pd.DataFrame(ins["stage_x_trigger"]).fillna(0)
        sx.index = [LABEL.get(i, i) for i in sx.index]
        st.dataframe(sx, use_container_width=True)

# ---------------------------------------------------------------- 4
with tabs[3]:
    if ins:
        c1, c2 = st.columns(2)
        e = pd.Series(ins["emotion_in_dropoffs"]).rename("% of drop-off events").reset_index()
        c1.plotly_chart(px.bar(e, x="index", y="% of drop-off events", title="Emotion at the drop-off moment",
                               color_discrete_sequence=[OKABE[0]]), use_container_width=True)
        o = pd.Series(ins["outside_app"]).drop("none_stated", errors="ignore").rename("mentions").reset_index()
        c2.plotly_chart(px.bar(o, x="index", y="mentions", title="Where they go when unsure (outside the app)",
                               color_discrete_sequence=[OKABE[1]]), use_container_width=True)
        c3, c4 = st.columns(2)
        c3.markdown("**How often they check (when stated)**"); c3.write(ins["checking"])
        c4.markdown("**What they look at**"); c4.write(ins["checks_what"])

# ---------------------------------------------------------------- 5
with tabs[4]:
    st.subheader("Run the engine on new text")
    st.markdown("Paste one or more reviews / posts / comments (separate items with a blank line). "
                "The same model + prompt that coded the corpus will label them.")
    sample = ("Started my first SIP of 2000 in Jan after my cousin suggested it. Six months later it shows -3% "
              "and I check it every morning. Thinking of stopping and putting it in FD instead.\n\n"
              "Groww charged me bounce charges because my autopay failed, no reminder. Cancelled the SIP.")
    txt = st.text_area("Text", value=sample, height=180)
    if st.button("Analyse", type="primary"):
        items = [t.strip() for t in re.split(r"\n\s*\n", txt) if t.strip()][:10]
        try:
            import llm
            batch = [{"id": f"u{i}", "text": t} for i, t in enumerate(items)]
            with st.spinner("Coding (Gemini, with Groq as automatic fallback)…"):
                out, used_model = llm.code_items_auto(batch)
            st.caption(f"Model: {used_model} · prompt {llm.PROMPT_VERSION}"
                       + (" · switched provider: " + ", ".join(s.get("dropped", s.get("skipped", ""))
                                                               for s in llm.SWITCHES) if llm.SWITCHES else ""))
        except Exception as ex:
            st.error(f"The AI coder is unavailable right now ({ex}). Fallback: the precomputed corpus "
                     "results in tabs ②–④ are still valid.")
            out = []
        for t, c in zip(items, out):
            with st.container(border=True):
                st.markdown(f"**Input:** {t[:300]}")
                if not c:
                    st.warning("No output for this item — needs human review."); continue
                quote_ok = (not c["evidence_quote"]) or c["evidence_quote"].lower().strip(' ."') in t.lower()
                gate = []
                if c["confidence"] < 0.6: gate.append("low confidence")
                if not quote_ok: gate.append("quote not found verbatim in input (possible hallucination)")
                if gate:
                    st.warning("⚠️ Quality gate: " + "; ".join(gate) + " → routed to human review, not counted.")
                elif not c["relevant"]:
                    st.info("Not about a personal SIP / mutual fund experience → excluded.")
                else:
                    st.success(f"✅ Passed quality gate (confidence {c['confidence']:.2f}, quote verified)")
                k = st.columns(4)
                k[0].metric("Action", c["sip_action"]); k[1].metric("Stage", c["investor_stage"])
                k[2].metric("Emotion", c["emotion"]); k[3].metric("First-time?", c["first_time"])
                st.markdown("**Triggers:** " + ", ".join(LABEL.get(x, x) for x in c["triggers"]))
                st.markdown(f"**Unmet need:** {c['unmet_need']}  \n**Evidence:** “{c['evidence_quote']}”")
                with st.expander("Full JSON"):
                    st.json(c)

# ---------------------------------------------------------------- 6
with tabs[5]:
    st.subheader("Does the engine agree with a human?")
    if not gold:
        st.info("Golden-set comparison not generated yet.")
    else:
        g = pd.DataFrame(gold["fields"]).T[["agreement_pct", "cohens_kappa"]]
        st.markdown(f"Hand-labelled items: **{gold['n']}** (labelled blind, before seeing engine output).")
        st.dataframe(g, use_container_width=True)
        st.caption("κ > 0.6 = substantial agreement; > 0.8 = near-perfect. Target set before the run: "
                   "≥ 90% on relevance, ≥ 80% on action, ≥ 70% on primary trigger.")
        st.markdown("**Where the engine disagreed**")
        for d in gold["disagreements"]:
            st.markdown(f"- `{d['id']}` (engine conf {d['engine_confidence']}): " +
                        "; ".join(f"{k}: human **{v['human']}** vs engine **{v['engine']}**" for k, v in d["diff"].items()))

st.divider()
st.caption("Public data only; no usernames stored; phone/email/PAN scrubbed before analysis. "
           "This is a research prototype and does not provide investment advice.")
