# Contract report: Northstar Enterprise SLA

Company: Meridian Labs
Counterparty: Northstar Retail
As of: 2026-10-25T23:59:59+00:00
Analysis status: needs_review
Confidence values are uncalibrated model assessments; explicit source-rule arithmetic is separately identified.

## Key terms and confidence
- party: Meridian Labs | confidence 1 [northstar-1.1]
  Source: Meridian Labs
- party: Northstar Retail | confidence 1 [northstar-1.1]
  Source: Northstar Retail
- duration: 1 January 2026 through 31 December 2026 | confidence 1 [northstar-1.1]
  Source: 1 January 2026 through 31 December 2026
- penalty: INR 100,000 service credit per incident for unplanned production outage lasting more than 60 consecutive minutes, issued within 30 calendar days | confidence 1 [northstar-6.1]
  Source: An unplanned production outage lasting more than 60 consecutive minutes requires Meridian Labs to issue an INR 100,000 service credit to Northstar Retail within 30 calendar days of the incident date.
- obligation: An incident notification must be provided to the customer within 24 hours of detection. | confidence 0.95 [northstar-6.2]
  Source: An incident notification must be provided to the customer within 24 hours of detection.

## Ambiguities and missing information
- compliance: not explicitly established by extraction; no value inferred.
- payment: not explicitly established by extraction; no value inferred.
- renewal: not explicitly established by extraction; no value inferred.
- termination: not explicitly established by extraction; no value inferred.

## Obligations and timeline
- 2026-11-24T23:59:59+00:00: Issue customer credit | upcoming [northstar-6.1] | Explicit source rule
- Unresolved: Incident notification required | unresolved [northstar-6.2] | Event timestamp/detection/confirmation time is missing; exact deadline unresolved.

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
- INR 100,000.00 | liability | supported [northstar-6.1] — Fixed event-triggered customer credit; not necessarily a cash payment.
- 2026-10-25: opportunity-adjusted {'INR': {'gross': 100000.0, 'recovery': 0, 'commitments': 0, 'net': 100000.0, 'secured_recovery': 0, 'worst_case_net': 100000.0}}
- 2026-11-01: opportunity-adjusted {'INR': {'gross': 100000.0, 'recovery': 0, 'commitments': 0, 'net': 100000.0, 'secured_recovery': 0, 'worst_case_net': 100000.0}}
- 2026-11-24: opportunity-adjusted {'INR': {'gross': 100000.0, 'recovery': 0, 'commitments': 0, 'net': 100000.0, 'secured_recovery': 0, 'worst_case_net': 100000.0}}
- 2026-12-24: opportunity-adjusted {'INR': {'gross': 100000.0, 'recovery': 0, 'commitments': 0, 'net': 100000.0, 'secured_recovery': 0, 'worst_case_net': 100000.0}}

## Recommended actions and approval

## References — original clause text
- [northstar-1.1] Clause 1.1, page 1: Meridian Labs provides a production analytics service to Northstar Retail from 1 January 2026 through 31 December 2026.
- [northstar-3.1] Clause 3.1, page 1: The production analytics service depends on the Atlas Cloud production infrastructure.
- [northstar-6.1] Clause 6.1, page 1: An unplanned production outage lasting more than 60 consecutive minutes requires Meridian Labs to issue an INR 100,000 service credit to Northstar Retail within 30 calendar days of the incident date. Scheduled maintenance announced at least 48 hours in advance is excluded. The credit is capped at INR 100,000 per incident.
- [northstar-6.2] Clause 6.2, page 1: An incident notification must be provided to the customer within 24 hours of detection.
- [northstar-9.1] Clause 9.1, page 1: Customer service credits are independent of any recovery Meridian Labs may obtain from its infrastructure providers.