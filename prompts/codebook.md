# Codebook — SIP continuation discovery (v1.3)

Unit of analysis: one review / post / comment. The coder answers **only from what the text says**;
anything not stated is `unknown`. Built from a 110-item open-coding read of real Play Store and
Reddit data, then frozen before the full run. (Changes are versioned in `CHANGELOG`.)

## 1. relevant (bool)
TRUE only if the author talks about **their own (or a close person's) mutual fund / SIP experience,
intent, or behaviour**. FALSE for: IPO/F&O/stock-only complaints, generic "good app", spam/ads,
pure fund-picking questions with no behaviour or feeling ("which small cap is best?").
**v1.2:** advice or allocation tips written *for someone else* ("you should split 15k into…") are FALSE
unless the author also describes their own SIP behaviour or feeling.

## 2. investor_stage
`considering` (not started) · `first_months` (≤3 months / "just started" / "first SIP") ·
`within_year` (3–12 months) · `beyond_year` (>12 months) · `unknown`

## 3. first_time (yes / no / unknown)
"yes" ONLY if the author explicitly says they are new / beginner / first investment / first SIP /
"just started investing". **v1.2:** do not infer it from a basic question, young age, a small amount or a
short holding period alone — those stay `unknown`.

## 4. sip_action — what happened or is being considered (single)
`started` · `continuing` · `considering_stop` · `paused_or_skipped` · `reduced` · `stopped_or_cancelled` ·
`redeemed` · `increased` · `restarted` · `failed_involuntary` (debit/mandate failed without intent) · `none`

v1.2 decision rules (from golden-set failures, see AI Evidence Log):
- `considering_stop` ONLY when the author says they are thinking of stopping, pausing, cancelling or
  redeeming **their own** SIP. Asking "is this normal?", "should I switch fund?" or "what should I do?"
  without stating an intent to stop is `continuing` (if they still run the SIP) or `none`.
- **v1.3:** an explicit question about stopping or pausing **their own** SIP ("should I stop my SIP?",
  "should I pause it for a while?", "continue or stop?") IS `considering_stop` — the person is weighing it.
  (Decided by the human labeller during adjudication, before v1.3 was scored.)
- A step-up, top-up, lump-sum add or "increased my SIP" → `increased`; a cut in amount → `reduced`.
  Do not collapse these into `continuing`.
- Actions described for another person (advice, a friend's story with no first-person behaviour) → `none`.

## 5. triggers — why (multi-label, max 3, ordered by importance)
| code | meaning |
|---|---|
| `market_fall_negative_returns` | portfolio in red / XIRR fell / crash |
| `underwhelming_returns` | returns flat or "too slow" vs expectation, even without a crash |
| `expectation_mismatch` | they expected something different (quick gains, FD-like stability, guaranteed growth) |
| `cash_flow_squeeze` | income dip, job loss, EMI, expense, emergency, "no money this month" |
| `payment_mandate_failure` | autopay/mandate/NACH failed, bounce charges, debit not processed |
| `app_ux_or_control_gap` | cannot edit amount/date, pause hard to find, confusing dashboard/P&L/XIRR |
| `platform_trust_doubt` | suspects NAV timing, charges, "cheating", support failures |
| `information_overload_conflict` | conflicting advice, finfluencers, news panic, too many opinions |
| `wrong_fund_doubt` | thinks fund choice was wrong, overlap, wants to switch/rebalance |
| `goal_disconnect` | no clear purpose, forgot why, "out of sight", disengaged |
| `life_event` | marriage, house, education, relocation, health |
| `lock_in_or_tax` | ELSS lock-in, exit load, tax on redemption |
| `social_influence` | started/stopped because friend/family/colleague did |
| `none` | no trigger stated |

## 6. checking_behaviour
`daily_or_more` · `weekly` · `monthly_statement` · `rarely` · `unknown`; plus `checks_what`
(free, ≤6 words, e.g. "absolute P&L", "XIRR", "red/green", "nothing").

## 7. emotion (single dominant)
`anxious` · `regretful` · `confused` · `frustrated` · `disappointed` · `confident` · `indifferent` · `neutral`

## 8. outside_app_action (multi)
`reddit_forum` · `youtube_finfluencer` · `friend_family` · `advisor_professional` · `google_news` ·
`customer_support` · `amc_or_other_app` · `none_stated`

## 9. segment signals (unknown unless stated)
- `income_type`: salaried · variable_or_business · student_or_no_income · unknown
- `age_band`: <25 · 25-34 · 35-44 · 45+ · unknown
- `money_source`: salary · family_or_pocket_money · business · windfall_bonus · unknown
- `influencer`: friend_family · finfluencer_youtube · app_or_ad · colleague_employer · self_research · unknown

## 10. unmet_need (≤15 words, user's need in their terms, not a solution)

## 11. evidence_quote (≤25 words, verbatim from the text, supports the main trigger)

## 12. confidence (0–1)
Coder's confidence in `relevant` + `sip_action` + first trigger. Items < 0.6 are routed to
human review and excluded from headline numbers (shown separately).
