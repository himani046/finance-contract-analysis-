# Contract report: Prism Analytics License

Company: Meridian Labs
Counterparty: Prism Software
As of: 2026-10-25T23:59:59+00:00
Analysis status: needs_review
Confidence values are uncalibrated model assessments; explicit source-rule arithmetic is separately identified.

## Key terms and confidence
- party: Meridian Labs | confidence 0.95 [prism-1.1]
  Source: Meridian Labs
- payment: INR 240,000 per annual term | confidence 0.95 [prism-1.1]
  Source: INR 240,000 per annual term
- duration: 1 December 2025 to 30 November 2026 | confidence 0.95 [prism-1.1]
  Source: 1 December 2025 to 30 November 2026
- renewal: renews automatically on 1 December 2026 for another annual term at INR 240,000 unless written cancellation is received by 1 November 2026 at 23:59 UTC | confidence 0.95 [prism-5.1]
  Source: renews automatically on 1 December 2026 for another annual term at INR 240,000 unless written cancellation is received by 1 November 2026 at 23:59 UTC
- termination: Cancellation prevents future renewal only; it does not refund fees paid for the current term. | confidence 0.95 [prism-5.2]
  Source: Cancellation prevents future renewal only; it does not refund fees paid for the current term.

## Ambiguities and missing information
- compliance: not explicitly established by extraction; no value inferred.
- obligation: not explicitly established by extraction; no value inferred.
- penalty: not explicitly established by extraction; no value inferred.

## Obligations and timeline
- 2026-11-01T23:59:59+00:00: Non-renewal notice deadline | upcoming [prism-5.1] | Explicit source rule

## Recorded payments, notices, and events
- 2026-10-25: Production infrastructure outage | reported | Portfolio event | 

## Risks, challenges, verification, and rulings
### Imminent Automatic Renewal of Prism Analytics License
Severity: medium | Likelihood: high | Ruling: supported | Confidence: 0.95
Meridian Labs will incur an automatic renewal liability of INR 240,000 on 1 December 2026 unless cancellation notice is given by 1 November 2026.
Attack path: Meridian Labs fails to submit a written cancellation notice by 1 November 2026 at 23:59 UTC. The agreement automatically renews on 1 December 2026, creating a binding fee obligation of INR 240,000 for the following annual term with no refund available.
Verification: Prism clause 5.1 specifies auto-renewal on 1 December 2026 for INR 240,000 unless cancellation is received by 1 November 2026. Given the current date of 2026-10-25, the deadline is imminent.
Rationale: Clause prism-5.1 establishes that the Prism Analytics License automatically renews on 1 December 2026 for INR 240,000 unless written cancellation is received by 1 November 2026 at 23:59 UTC. As of 25 October 2026, 7 days remain before the non-renewal deadline.
- [prism-5.1] This license renews automatically on 1 December 2026 for another annual term at INR 240,000 unless written cancellation is received by 1 November 2026 at 23:59 UTC.
- [prism-5.2] Cancellation prevents future renewal only; it does not refund fees paid for the current term.

## Financial exposure and no-action projection
- INR 240,000.00 | commitment | avoidable [prism-5.1] — Annual renewal commitment, separate from incident exposure.
- 2026-10-25: opportunity-adjusted {'INR': {'gross': 0, 'recovery': 0, 'commitments': 240000.0, 'net': 0, 'secured_recovery': 0, 'worst_case_net': 0}}
- 2026-11-01: opportunity-adjusted {'INR': {'gross': 0, 'recovery': 0, 'commitments': 240000.0, 'net': 0, 'secured_recovery': 0, 'worst_case_net': 0}}
- 2026-11-24: opportunity-adjusted {'INR': {'gross': 0, 'recovery': 0, 'commitments': 240000.0, 'net': 0, 'secured_recovery': 0, 'worst_case_net': 0}}
- 2026-12-24: opportunity-adjusted {'INR': {'gross': 0, 'recovery': 0, 'commitments': 240000.0, 'net': 0, 'secured_recovery': 0, 'worst_case_net': 0}}

## Recommended actions and approval
### Issue Prism Analytics Non-Renewal Notice
Owner: Procurement Manager | Due: 2026-11-01 | needs_approval | Confidence: 0.95
Subject: Notice of Non-Renewal - Prism Analytics License

To Prism Software Account Management,

Meridian Labs hereby provides formal written notice of cancellation and non-renewal for the Prism Analytics License (term 1 December 2025 to 30 November 2026), pursuant to Clause 5.1 of the Prism Analytics License agreement.

This notice is delivered prior to the 1 November 2026 23:59 UTC deadline to ensure the agreement does not automatically renew for the subsequent term commencing 1 December 2026. Please confirm receipt of this non-renewal notice and acknowledge that no further fees of INR 240,000 will be billed for the 2026–2027 annual term per Clause 5.1 and Clause 5.2.

Sincerely,
Authorized Signatory
Meridian Labs
References: prism-5.1, prism-5.2

## References — original clause text
- [prism-1.1] Clause 1.1, page 1: Meridian Labs licenses Prism Analytics for INR 240,000 per annual term, from 1 December 2025 to 30 November 2026.
- [prism-5.1] Clause 5.1, page 1: This license renews automatically on 1 December 2026 for another annual term at INR 240,000 unless written cancellation is received by 1 November 2026 at 23:59 UTC.
- [prism-5.2] Clause 5.2, page 1: Cancellation prevents future renewal only; it does not refund fees paid for the current term.