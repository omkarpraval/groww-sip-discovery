# Groww SIP Continuation — AI Discovery Engine

**Question:** why do first-time mutual fund investors on Groww stop, pause or let their SIP lapse within 12 months,
despite starting with good intent?

This repo is the reproducible discovery engine for a Product Management Fellowship graduation project.
It is a research tool and **does not provide investment advice**.

## Pipeline
| Stage | Script | What it does |
|---|---|---|
| 0 Collect | `collectors/*.py` | Play Store + App Store reviews, Reddit (Arctic Shift archive), TradingQnA threads, YouTube comments |
| 1 Filter | `pipeline/filter.py` | De-duplicate, scrub phone/email/PAN, keep SIP/MF-related items (EN/Hindi/Hinglish), keyword flags |
| 2 Code | `pipeline/coder.py` + `pipeline/llm.py` | Gemini codes each item against `prompts/codebook.md` into structured JSON |
| 3 Aggregate | `pipeline/aggregate.py` | Theme reach, drop-off proximity, stage x trigger, segment cuts, opportunity score |
| 4 Validate | `pipeline/golden.py` | Golden set hand labels vs engine: agreement %, Cohen's kappa, confusion, failures |
| App | `app/streamlit_app.py` | Explore results + run the same coder live on any text, with visible quality gates |

## Quality gates
- Confidence < 0.6 → human-review bucket, excluded from headline numbers
- Evidence quote must appear verbatim in the source text (hallucination check)
- Golden set agreement targets fixed before the run: relevance ≥ 90%, action ≥ 80%, primary trigger ≥ 70%
- Prompt + model version stamped on every coded row

## Privacy
Public data only. No usernames stored. Phone numbers, emails, PAN-like strings and long account-like numbers
are scrubbed before storage or LLM calls.

## Run
`Actions → Discovery engine → Run workflow` (needs repo secret `GEMINI_API_KEY`).
Locally: `pip install -r requirements.txt && streamlit run app/streamlit_app.py`.
