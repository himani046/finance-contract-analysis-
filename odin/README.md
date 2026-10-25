# Odin — Contract Risk Foresight

A local multi-agent contract workspace built against Odin_PS.pdf: cited extraction, temporal and financial projections, adversarial review, event verification, arbitration, and human-reviewed actions.

## Start

On this computer, run Start-Odin.ps1 from this folder, then open http://127.0.0.1:8765.

On another computer with Python 3.11 or later:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Configure GEMINI_API_KEY in .env, then:
.venv\Scripts\python server.py
```

The original computer's ignored .env is configured. The shareable ZIP excludes credentials and runtime databases. The frontend never receives the key.

## Use the workspace

1. Overview: choose a currency; inspect exposure, recoveries, commitments, priority alerts, and each amount's rule sources. Source-rule arithmetic works in demo and live mode.
2. Contract graph: inspect parties, contracts, and individual clauses. Filter contracts or edge types; click a conflict marker to open Loki's challenge, Heimdall's verification, and Tyr's ruling.
3. Time machine: move the date slider or exact UTC clock. The 60-day no-action horizon, obligations, alerts, and financial entries update from one ledger. Missing event anchors remain unresolved.
4. Event feed: record outages, incidents, payments, or notices. Confirmed receipts need the correct contract/clause and, for incident credits, the related incident. Claims requiring attachments also need verified evidence. Draft approval never counts as sending or receipt.
5. Agents: switch to Live analysis and run the six Gemini roles. Inspect the delegated plan, workstream status, extracted facts, feedback, verification, and arbitration. Saved runs can be inspected independently.
6. Reports: drill into the heatmap by contract, clause type, and month. Download complete company/contract reports containing terms, confidence, obligations, risks, rulings, actions, projections, and references.
7. Settings: configure model, call/token/runtime budgets, clarification rounds, and evidence confidence. Enable automatic event reassessment to run agents on new inputs. It is off by default because it sends contract text to Gemini and consumes quota. Deterministic source rules update without an LLM call.

Demo and live workspaces are saved separately. Synthetic contracts and authored demo traces are clearly labeled. Live traces are actual Gemini results or explicitly labeled cache hits.

## Agent workflow

Odin plan → Thor per contract → Norns timeline → Loki challenge → bounded targeted Thor/Loki feedback → Heimdall verification → Tyr arbitration and drafts.

Exact quote checks reject fabricated/wrong-contract evidence. Missing extraction categories remain unestablished. Low-confidence facts and clarification requests trigger scoped re-extraction, followed by Loki reassessment. Repeated targets cannot create an infinite loop. Missing review/arbitration, unresolved requests, weak evidence, and malformed drafts prevent clean completion.

Actions carry arbitration confidence, references, and approval status. No email or legal notice is automatically sent. Gemini 3.8 Flash is primary; only Gemini 3.6 Flash is the authorized service/model-failure fallback. Quota/authentication failures are surfaced. Cache keys include context, model, and prompt version. Failed refreshes preserve earlier results with an explicit stale label.

## Financial and temporal model

intelligence.py compiles explicit fixed outage credits and source caps, annual renewal commitments, dated fixed payments, and capped daily late-payment penalties. Supporting clauses, qualification, and receipt conditions stay visible. Totals never combine currencies or mix renewal commitments into incident exposure.

The no-action projection honors recorded receipts and assumes no additional payments/notices. Timely documented claims can preserve eligibility after the deadline; late claims cannot. UTC hour rules use event, detection, or access-confirmation timestamps. An outage alone does not establish a data breach.

Variable percentages, tiers, negotiated formulas, unsupported currencies, conflicting definitions, and missing anchors are disclosed as unquantified/unresolved. A zero compiled subtotal does not mean a contract has no other liability. This is a bounded rule interpreter, not a universal legal-language compiler.

## Architecture

- server.py: loopback API, SQLite state/cache/history, orchestration, event monitor.
- agents.py: Gemini adapter, six role prompts/schemas, retries, quote validation.
- intelligence.py: source rules, obligation/receipt ledger, projections, graph, alerts, heatmap, reports.
- demo.py: synthetic portfolio and authored demonstration traces.
- static/app.js: shared UI primitives/base views; static/workspace.js adds the full evidence workspace.
- static/editorial.css and workspace.css: responsive reference-inspired dashboard.
- data/odin.db: workspace, separate mode snapshots, agent cache, archived runs.

Generation requests are paced at 15 seconds by default (GEMINI_MIN_INTERVAL_SECONDS in the backend environment). The event monitor batches changes, prevents overlapping runs, and uses a 15-minute quota/billing backoff. The dashboard refreshes events arriving through the local API. See API_GUIDE.md for feed integration.

## Verification

```powershell
python -m unittest discover -s tests -v
```

73 automated checks cover provenance, all agent roles, configurable feedback, budgets, quota handling, retained results, financial/time boundaries, receipts, graph integrity, heatmaps, complete reports, ingestion, persistence, and API behavior. Both JavaScript files pass syntax checks.

See REQUIREMENTS.md for traceability and VERIFICATION.md for runtime evidence. The replacement key now powers a resumed end-to-end workspace run: all six roles reached Tyr, with nine cache hits and three successful new model calls. Its status is needs_review because one extraction was excluded and a clarification remains unresolved. An earlier fully uncached attempt encountered rate/service limits. Cache reuse is explicitly recorded; this is not claimed as a wholly uncached run.

## Runtime boundaries

Local single-user hackathon application. Text PDF/TXT/Markdown only: maximum 8 MB, 60 pages, 100,000 characters per contract, 12 contracts per portfolio. Scans need OCR. Interpretations need human review; model confidence is uncalibrated. A transport response may finish after a runtime boundary: it is cached and the run stays incomplete. Payment receipt events model full settlement of the exact cited obligation; partial payments are not modeled. No public deployment or multi-user authentication.
