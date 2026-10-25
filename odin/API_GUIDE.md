# Odin local event feed

Base URL: `http://127.0.0.1:8765`. Loopback only; JSON mutation bodies. Foreign browser origins cannot mutate state.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/state` | Shared state, roles, source rules, projections, graph, alerts, heatmap |
| GET | `/api/events` | Recorded events |
| POST | `/api/event` | Append an idempotent event; duplicate IDs do not duplicate events |
| POST | `/api/clock` | Move simulated date/exact UTC instant |
| POST | `/api/analyze` | Start a bounded live run; empty body uses saved settings |
| POST | `/api/settings` | Save model, budgets, feedback/evidence controls |
| POST | `/api/monitor` | Enable/disable automatic reassessment |
| POST | `/api/mode` | Select `live` or `demo`; snapshots remain separate |
| POST | `/api/company` | Save company name/context |
| POST | `/api/upload` | Add base64 `content` with PDF/TXT/Markdown `name` |
| POST | `/api/action` | Record draft `id` and approval `status` |
| GET | `/api/report` | Complete company Markdown report |
| GET | `/api/report?contract_id=atlas` | Independent complete report |
| GET | `/api/history` | Saved run index |
| GET | `/api/history?id=RUN_ID` | Structured archived run/output |
| POST | `/api/connection` | Key authentication/model discovery; does not prove generation quota |

## Synthetic outage example

```json
{
  "id": "incident-2026-10-25-001",
  "type": "outage",
  "title": "Production infrastructure outage",
  "date": "2026-10-25",
  "timestamp": "2026-10-25T10:00:00Z",
  "detected_at": "2026-10-25T10:05:00Z",
  "classification": "unplanned",
  "duration_minutes": 95,
  "description": "Synthetic test incident."
}
```

No affected contract means a portfolio incident. Scoped events may provide `contract_id` and `affected_contract_ids`. For the sample terms, maintenance exclusion needs recorded `advance_notice_hours` of at least 48. Unproven qualification remains conditional.

## Claim receipt example

```json
{
  "id": "claim-receipt-001",
  "type": "notice",
  "title": "Atlas claim received",
  "date": "2026-11-01",
  "timestamp": "2026-11-01T16:00:00Z",
  "contract_id": "atlas",
  "clause_id": "atlas-8.2",
  "related_event_id": "incident-2026-10-25-001",
  "status": "received",
  "evidence_verified": true,
  "description": "Receipt acknowledgement and incident report verified by operator."
}
```

This records an operator assertion of actual receipt, not draft approval. Receipt must precede the deadline. A payment event with `status: received` and an exact contract/clause records full settlement; partial payments are not modeled. Incident-credit settlements also require `related_event_id`.

## Monitoring and clock

Enable continuous agent reassessment with `POST /api/monitor`, body `{"enabled":true}`. This sends contracts/events to Gemini after input changes. Deterministic rules update immediately even when monitoring is paused or quota is exhausted. The worker prevents overlap and backs off after quota errors.

Clock example: `{"date":"2026-11-02","timestamp":"2026-11-02T09:30:00Z"}`. Date and timestamp must agree in UTC; timestamps require an offset. Date-only simulation uses the end of that UTC day. Missing hour-level event anchors remain unresolved.

Settings: `model`, `max_calls` (6–30), `max_tokens` (1,000–200,000), `max_seconds` (30–1,200), `max_iterations` (0–5), `evidence_threshold` (0–1). Exact quote validation always applies.
