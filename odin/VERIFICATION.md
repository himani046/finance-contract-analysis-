# Odin implementation verification — 25 October 2026

## Result

The previously missing application capabilities are implemented: full evidence graph, source-rule financial projections in live mode, hour-level/receipt ledger, configurable feedback/evidence controls, background event reassessment, per-action confidence, complete contract/company reports, and the contract/type/month heatmap. REQUIREMENTS.md maps every functional and non-functional requirement to its implementation.

73 automated checks pass. Both JavaScript files pass syntax checks. Browser checks verified clause and conflict navigation, source text, independent verification/ruling drawers, heatmap grouping and evidence drilldowns, and feedback controls. The local server serves the new assets successfully.

## Replacement key — latest workspace run

The replacement key is configured in the ignored backend .env and loaded by the restarted server. The current workspace run reached all six roles through Tyr using Gemini 3.6 Flash, the approved fallback. It reused nine exact-input cache entries and made three successful new model calls, consuming 14,307 new tokens. Loki reassessed after targeted Thor clarification, Heimdall verified the new findings, and Tyr produced the final rulings and drafts.

The final status is needs_review, not incomplete: one unsupported Thor fact was excluded, and repeated clarification targets could not supply new source evidence. These issues remain visible. The latest results are current (not marked stale). This is a successfully executed resumed workflow, not a wholly uncached repeat or a clean legal assessment.

An earlier uncached verification with the new key produced Odin and four contract extractions, then hit a rate limit; its resumed fifth extraction received HTTP 503. Conservative request pacing was added. An older HTTP 402 workspace run started at 10:18 UTC, before the key file changed at 10:20 UTC; that billing response is not attributed to the replacement key.

## Real retained agent evidence

The prior actual Gemini run remains archived for comparison: Odin plan, Thor extraction for five contracts (29 accepted facts), Norns six obligations, Loki three findings, targeted Thor clarification, Heimdall three verifications, Tyr three rulings and three drafts. Accepted quotes were rechecked against source clauses. That prior run remains needs_review because one unsupported extraction was excluded. The latest resumed workspace run is recorded separately in verification-results.json and live-run-example.json. It is not silently relabeled complete.

Saved runs are inspectable in Agent workspace. Failed refreshes retain earlier results with an explicit stale label and preserve separate partial output/error details. Source-rule arithmetic is recomputed independently of old model interpretations.

## Added and verified behavior

- Financial amounts come from original clauses, including qualifying duration and cross-clause caps. Rule sources can be inspected together.
- Conditional qualification, non-cash credits, renewal commitments, separate currencies, and unsupported formulas are explicit.
- The no-action horizon evaluates 61 dates and honors already recorded receipt evidence.
- Timely verified claim receipt preserves eligibility after a deadline; late, wrong-clause, wrong-incident, reported-only, or unverified receipt does not.
- Exact UTC event/detection/confirmation anchors support hour-level deadlines. Missing anchors stay unresolved. An outage alone does not trigger a data-breach notice.
- Configurable confidence/feedback limits trigger targeted retrieval followed by Loki reassessment. Repeated targets, exhausted budgets, missing reviews, and inadequate drafts prevent clean completion.
- Continuous local source-rule monitoring is immediate. Optional automatic agent reassessment batches event/input changes, prevents overlap, and backs off for 15 minutes on quota failure. It is off by default to avoid unexpected transmission/API use.
- The graph contains company, party, contract and clause nodes, dependency/reference/challenge edges, layer/focus controls, and clickable evidence.
- Reports include terms/confidence, missing information, payment/notice history, obligations, attacks, verification, arbitration, action drafts, no-action projections, and original references.
- Heatmap controls group by contract or clause type, choose a month, and open the underlying obligations.

## Credential and package checks

The key remains in the ignored backend .env. It is sent as an authentication header, not in prompts or URLs. It was scanned for across source/deliverables and not found there. Secret/source/database URLs are not served. The portable source ZIP excludes .env, databases, and bytecode. The server binds to loopback.

## Boundaries

This is a local, single-user hackathon implementation with meaningful model agents. The financial compiler supports explicit fixed credits/caps, annual renewal commitments, dated fixed payments, and capped daily penalties. Complex percentages/tiers/negotiated terms, ambiguous thresholds, unsupported currencies and missing anchors are disclosed rather than given fabricated totals. Receipt events model full settlement; partial payments are not modeled. Text PDF/TXT/Markdown uploads are bounded; scans need OCR.

These are documented input/modeling boundaries, not hidden placeholder views. Legal and semantic interpretations still need human review; confidence is uncalibrated. There is no public deployment or production load/security certification.

## Reproduce

```powershell
python -m unittest discover -s tests -v
```

See API_GUIDE.md for the event feed, clock, settings, monitor and report endpoints. See REQUIREMENTS.md for traceability. A fresh online repeat still requires available Gemini quota.
