# Traceability to Odin_PS.pdf

The requested local workflow and dashboard capabilities are implemented below. Financial computation is bounded to supported explicit source rules; unsupported terms and missing anchors are disclosed. Model-mocked checks are distinguished from real provider calls.

| Requirement | Implementation / review location |
|---|---|
| FR1.1 Context/contracts | Company settings, document upload, API/state |
| FR1.2 Per-contract/cross-contract plan | Odin prompt/schema, required-workstream validation, delegated work-plan panel |
| FR1.3 Delegation/tracking | State-machine routing, per-contract/shared status, transitions |
| FR1.4 Coordination/synthesis | Bounded feedback, coverage checks, Heimdall/Tyr synthesis, explicit terminal statuses |
| FR2.1 Extraction | Thor types: parties, duration, renewal, payments, obligations, penalties, compliance, termination |
| FR2.2 Confidence/citations | Exact contract/clause/quote validation; confidence in drawers/reports |
| FR2.3 Ambiguity | Thor ambiguities, explicit missing-category coverage, unsupported rules/date anchors disclosed |
| FR2.4 Re-extraction | Scoped clause retrieval, scoped response validation, shared clarification history |
| FR3.1 Past/current/future | Event/receipt ledger, obligations, statuses, UTC hour rules, reports |
| FR3.2 Clock | Date slider and exact UTC clock; generalized slider origin |
| FR3.3 No-action financial projection | 61 positions; source credits/caps, renewals, payments and daily penalties; unsupported math unquantified |
| FR4.1 Adversarial review | Separate Loki prompt and attack-path output |
| FR4.2 Cross-contract conflicts | Multi-source findings, graph edges, company synthesis |
| FR4.3 Evidence/scoring | Source citations, severity, qualitative likelihood, attack paths |
| FR4.4 Clarification | Loki/low-confidence requests route to scoped Thor, followed by Loki reassessment |
| FR5.1 Event monitoring/mapping | Local event API/feed, event scoping, Heimdall mappings, opt-in background reassessment |
| FR5.2 Verification | Independent Heimdall role, validated mappings, verdicts and missing facts |
| FR5.3 Alerts/noise | Severity feed; completed/rejected items filtered; deadline urgency; outage does not prove data breach |
| FR6.1 Arbitration | Tyr verdict/rationale; missing verification/rulings prevent clean completion |
| FR6.2 Concrete drafts | Notice/memo prompt, source references, draft subject/length review, download |
| FR6.3 Approval/confidence | Local approval; per-action confidence from associated Tyr arbitration |
| FR7.1 Feedback/debate | Thor–Loki loop; Heimdall independent challenge; Tyr resolution |
| FR7.2 Termination | Configurable rounds/confidence/calls/tokens/runtime; repeated-target guard; budget breach incomplete |
| FR8.1 Independent report | Terms/confidence, ambiguity, events, timeline, risks, verification, rulings, actions, projection, references |
| FR8.2 Company report | Currency-separated totals, cross-contract conflicts, priorities, no-action horizon, independent reports |
| FR9.1 Graph | Company/party/contract/clause nodes, dependency/reference/conflict edges, filters and source drilldowns |
| FR9.2 Slider | Recalculates obligations, deadlines, penalties, recoveries and commitments |
| FR9.3 Gauge/heatmap | Currency-selectable financial gauge; urgency matrix by contract or clause type and month; drilldown |
| FR9.4 Debate panel | Role traces/outputs, feedback rounds, plan, saved run browser |
| FR9.5 Alerts/actions | Prioritized stream and complete cited drafts with confidence/approval |
| NFR1 Architecture | Separate prompts/schemas, explicit state machine, SQLite shared output/messages |
| NFR2 Quality | Wrong-contract/fabricated citations excluded; facts versus interpretations; unresolved inputs preserved |
| NFR3 Reliability | Malformed input handling, retries, authorized fallback, quota backoff, bounded loops, incomplete flags, retained stale output |
| NFR4 Observability | Plan/status, confidence, projections, attacks, verification, rulings, transitions, archives, synthesis |
| NFR5 Performance | Context/model/prompt cache, targeted retrieval, compile-once projections, configurable budgets |
| NFR6 Reproducibility | Explicit SQLite state/modes/history/cache; structured intermediate output; deterministic arithmetic |
| NFR7 Meaningful LLM | Six actual Gemini roles; retained real output inspectable; replacement-key resumed run reached all roles; nine cache hits and three new calls, needs_review |

## Evaluation evidence

73 tests cover workflow, provenance, time/financial boundaries, receipts, automatic reassessment, loop/usage limits, graph integrity, heatmap dimensions, reports, documents, state and API handling. Browser checks verified graph clauses/conflicts, Heimdall/Tyr drawers, clause-type heatmap drilldowns and controls.

The replacement key was verified in the current workspace: a resumed run reached all six roles using nine cache hits and three successful new calls (14,307 tokens) on Gemini 3.6 Flash. Its needs-review status preserves an excluded extraction and an unresolved clarification. Earlier uncached attempts encountered rate/service limits. The older HTTP 402 run occurred before the replacement key was installed and is not attributed to it. Mocked checks are never substituted for a live result.
