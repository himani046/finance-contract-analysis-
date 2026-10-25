# Odin: three-minute demonstration

## Before presenting

- Start the local application.
- Keep Gemini quota available; test the connection in Settings.
- Run one live analysis in advance and keep its outputs available in Live analysis.
- Use Demo scenario for deterministic time and money comparisons. Say that this is a synthetic fixture.
- Reset the demo, then start at 25 October 2026.

## 0:00–0:20: The business problem

"One cloud outage can create obligations across several contracts. Odin connects the event to the clauses, the deadlines, and the next action."

## 0:20–0:55: Make the risk visible

In Overview, click Inject event. Keep the defaults: unplanned, 95 minutes, 25 October. Add the event.

Point to INR 100,000 of customer credit exposure and INR 30,000 of conditional vendor recovery. Explain that vendor recovery is an invoice credit, not cash.

## 0:55–1:25: Show evidence

Open the outage finding's sources. Show the customer credit clause, the provider claim deadline, and the support evidence requirement. Distinguish contract facts from agent interpretations.

## 1:25–1:55: Show the cost of waiting

Go to Time machine. Move the slider to 2 November. The claim window has closed. Recovery drops to zero; the scenario's net exposure rises to INR 100,000. Moving time does not call Gemini.

## 1:55–2:25: Show the real agent work

Switch to Live analysis and open Agent workspace. Inspect a real Loki finding, Heimdall verification, and Tyr ruling from the saved run. Keep its actual needs-review or completion status visible; explain any excluded evidence. The traces include their structured outputs and evidence references.

## 2:25–2:50: Show the action

Open Action center, inspect the drafted notice and its references. Approval records human review; nothing is automatically sent.

## 2:50–3:00: Close with a precise claim

"Odin makes contractual risk traceable, tests its own findings, and puts the next action in front of a human before the deadline."

## If asked about limits

The same source-rule engine now evaluates explicit fixed credits/caps, renewals, dated payments, and daily penalties in demo and live portfolios. Unsupported formulas stay unquantified. Scanned PDFs need OCR. The replacement-key workspace run reached every role with cached extractions and fresh reassessment/verification/arbitration. Keep cache labels and the needs-review status visible; preserve the archived run in case provider quota changes. The app is a local prototype.

## Additional feature proof

Open Overview and scroll to the graph. Click an individual clause, then a conflict marker to inspect the verification/ruling. Open Reports, change Group by to Clause type, select a month, and click a populated heatmap cell. Download a complete independent contract report. In Settings, show configurable rounds, evidence threshold and the automatic event-monitor toggle. For hour-level deadline demonstrations, supply event and detection timestamps rather than only a calendar date.
