# Contract report: Atlas Cloud Services

Company: Meridian Labs
Counterparty: Atlas Cloud
As of: 2026-10-25T23:59:59+00:00
Analysis status: needs_review
Confidence values are uncalibrated model assessments; explicit source-rule arithmetic is separately identified.

## Key terms and confidence
- party: Meridian Labs | confidence 0.98 [atlas-1.1]
  Source: Meridian Labs
- party: Atlas Cloud | confidence 0.98 [atlas-1.1]
  Source: Atlas Cloud
- duration: 1 January 2026 through 31 December 2026 | confidence 0.95 [atlas-1.1]
  Source: 1 January 2026 through 31 December 2026
- definition: A qualifying incident is an unplanned production outage lasting more than 60 consecutive minutes. | confidence 0.95 [atlas-4.2]
  Source: A qualifying incident is an unplanned production outage lasting more than 60 consecutive minutes.
- penalty: Service credits are capped at INR 30,000 per incident and are the sole monetary remedy, applied to future invoices. | confidence 0.92 [atlas-8.3]
  Source: Service credits are the sole monetary remedy and are capped at INR 30,000 per incident.
- renewal: Renews on 1 January 2027 for twelve months unless written non-renewal notice is received no later than 1 December 2026. | confidence 0.95 [atlas-11.1]
  Source: The agreement renews on 1 January 2027 for twelve months unless written non-renewal notice is received no later than 1 December 2026.
- obligation: A written claim with an incident report must be received by 23:59 UTC on the seventh calendar day after the incident date. | confidence 0.95 [atlas-8.2]
  Source: A written claim with an incident report must be received by 23:59 UTC on the seventh calendar day after the incident date.

## Ambiguities and missing information
- compliance: not explicitly established by extraction; no value inferred.
- termination: not explicitly established by extraction; no value inferred.

## Obligations and timeline
- 2026-11-01T23:59:59+00:00: Submit credit claim | upcoming [atlas-8.2] | Explicit source rule
- 2026-12-01T23:59:59+00:00: Contract notice deadline | upcoming [atlas-11.1] | Explicit source rule

## Recorded payments, notices, and events
- 2026-10-25: Production infrastructure outage | reported | Portfolio event | 

## Risks, challenges, verification, and rulings
### Liability Mismatch Between Upstream Infrastructure and Downstream Customer SLA
Severity: high | Likelihood: high | Ruling: supported | Confidence: 0.95
Meridian Labs owes Northstar Retail INR 100,000 for qualifying outages, but can only recover a maximum of INR 30,000 in non-cash service credits from Atlas Cloud, creating an unrecoverable net loss of INR 70,000 per incident.
Attack path: An unplanned outage occurs on Atlas Cloud. Northstar demands an INR 100,000 credit under northstar-6.1. Meridian Labs seeks recovery from Atlas Cloud under atlas-8.3, but receives only INR 30,000 as a future invoice credit. Northstar's SLA explicitly prevents offsetting this with provider recovery under northstar-9.1, forcing Meridian Labs to absorb the INR 70,000 gap.
Verification: The contracts clearly set Northstar's service credit at INR 100,000 per qualifying incident, while Atlas Cloud caps recovery at INR 30,000 in non-cash credits. Northstar-9.1 explicitly states credits are independent of provider recovery, resulting in an unrecoverable gap.
Rationale: Clause northstar-6.1 obligates Meridian Labs to issue an INR 100,000 credit for qualifying unplanned outages, while atlas-8.3 caps Atlas Cloud recovery at INR 30,000 in future non-cash credits. Clause northstar-9.1 explicitly confirms that customer credits are independent of provider recovery, creating an unrecoverable net liability gap of INR 70,000 per incident.
- [northstar-6.1] An unplanned production outage lasting more than 60 consecutive minutes requires Meridian Labs to issue an INR 100,000 service credit to Northstar Retail within 30 calendar days of the incident date.
- [northstar-9.1] Customer service credits are independent of any recovery Meridian Labs may obtain from its infrastructure providers.
- [atlas-8.3] Service credits are the sole monetary remedy and are capped at INR 30,000 per incident. Credits are applied to future invoices, not paid in cash.

## Financial exposure and no-action projection
- INR 30,000.00 | recovery | conditional [atlas-8.2] — Invoice credit; conditional on qualification and timely documented receipt.
- 2026-10-25: opportunity-adjusted {'INR': {'gross': 0, 'recovery': 30000.0, 'commitments': 0, 'net': -30000.0, 'secured_recovery': 0, 'worst_case_net': 0}}
- 2026-11-01: opportunity-adjusted {'INR': {'gross': 0, 'recovery': 30000.0, 'commitments': 0, 'net': -30000.0, 'secured_recovery': 0, 'worst_case_net': 0}}
- 2026-11-24: opportunity-adjusted {'INR': {'gross': 0, 'recovery': 0, 'commitments': 0, 'net': 0, 'secured_recovery': 0, 'worst_case_net': 0}}
- 2026-12-24: opportunity-adjusted {'INR': {'gross': 0, 'recovery': 0, 'commitments': 0, 'net': 0, 'secured_recovery': 0, 'worst_case_net': 0}}

## Recommended actions and approval
### Submit Atlas Cloud Service Credit Claim
Owner: Operations Lead | Due: 2026-11-01 | needs_approval | Confidence: 0.95
Subject: Service Credit Claim - Unplanned Production Infrastructure Outage (2026-10-25)

To Atlas Cloud Support / Accounts Team,

Meridian Labs hereby submits a formal claim for a service credit under Clause 8.2 of the Atlas Cloud Services Agreement following a qualifying unplanned production outage on 25 October 2026 lasting 95 consecutive minutes. 

Per Clause 4.2 and Clause 8.2, Meridian Labs is eligible for an INR 30,000 service credit. Attached is the incident report provided by our operational support partner in accordance with Clause 8.2. Please confirm receipt of this claim and approve the application of the INR 30,000 credit against our future invoices per Clause 8.3.

Required Attachments: Incident Support Report (Beacon Operations)

Sincerely,
Authorized Signatory
Meridian Labs
References: atlas-4.2, atlas-8.2, atlas-8.3

## References — original clause text
- [atlas-1.1] Clause 1.1, page 1: This agreement is between Meridian Labs and Atlas Cloud, effective 1 January 2026 through 31 December 2026.
- [atlas-4.2] Clause 4.2, page 1: A qualifying incident is an unplanned production outage lasting more than 60 consecutive minutes. Scheduled maintenance announced at least 48 hours in advance is excluded.
- [atlas-8.2] Clause 8.2, page 1: For each qualifying incident, Meridian Labs is eligible for an INR 30,000 service credit. A written claim with an incident report must be received by 23:59 UTC on the seventh calendar day after the incident date. An approved timely claim preserves credit eligibility after this deadline.
- [atlas-8.3] Clause 8.3, page 1: Service credits are the sole monetary remedy and are capped at INR 30,000 per incident. Credits are applied to future invoices, not paid in cash.
- [atlas-11.1] Clause 11.1, page 1: The agreement renews on 1 January 2027 for twelve months unless written non-renewal notice is received no later than 1 December 2026.