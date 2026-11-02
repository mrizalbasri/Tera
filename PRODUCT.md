# Tera

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- Primary: finance teams across industries that process employee reimbursement claims and review exceptions.
- Employees submit receipts, follow claim status, and answer clarification requests.
- Finance reviewers inspect evidence and reasons before approving or rejecting cases that require human judgment.

This audience was confirmed by the product owner on 2026-10-22. The FMCG distributor and field-sales audience in the draft BRD/PRD is an example use case, not the product's audience boundary.

## Product Purpose

Tera helps teams process receipt-based reimbursement claims with less manual entry and checking. Employees should understand the status of a claim and what to do next. Finance should have the evidence and reasons needed to handle exceptions.

Success means clear next actions for employees, consistent policy checks, and traceable decisions for finance. Quantitative targets in draft requirements remain hypotheses, not demonstrated results.

## Positioning

Tera's product mechanism is an agent workflow that connects receipt extraction, validation, policy evaluation, duplicate and anomaly checks, decisions, clarification, and human review. It carries a claim through follow-up steps and records the evidence and reasons behind its outcome.

No unique-market or comparative performance claim has been established.

## Operating Context

- The interface is in Indonesian and runs in desktop and mobile web browsers.
- Employees upload receipts, track claim history and status, and supply missing information or replacement evidence when requested.
- Finance uses a review workspace to inspect receipt evidence, extracted fields, policy findings, and risk signals, then records a decision with a reason.
- Claim history, processing steps, reports, and CSV exports support follow-up and review.
- The existing implementation uses SvelteKit/TypeScript and a Python/FastAPI backend. Normal login uses Clerk; a local demo mode supports evaluation without an account.

## Capabilities and Constraints

- Process receipt claims, explain decisions, request clarification, and escalate uncertain or risky cases to finance.
- Official claim decisions come from the backend. The interface presents their reasons and evidence rather than calculating a separate outcome.
- Extraction can use mock or live providers. Optional policy retrieval and ML anomaly scoring depend on configuration; do not imply that every demo uses them.
- A risk signal supports investigation and review; it is not proof of fraud.
- Payments, accounting integrations, and multilevel approval are outside the current scope, as confirmed by the product owner.
- Preserve employee data boundaries, receipt privacy, and protections around external model calls. Keep credentials and real personal or receipt data out of Git.
- Pricing, public deployment, measured business impact, and production customer adoption have not been confirmed.

## Brand Commitments

- The product name is **Tera**, with an uppercase T.
- Preserve the existing receipt logo and the user-approved brand references recorded in DESIGN.md.
- Use clear Indonesian for status, explanations, errors, and next actions. Do not imply a claim has been paid when it has only been approved.
- DESIGN.md remains the authority for the existing visual system; this file records product truth.

## Evidence on Hand

- README.md describes current workflows, implementation, local setup, and configuration-dependent capabilities.
- docs/BRD_Expense_Reimbursement_Agent.md and docs/sdlc/06-prd.md contain draft business and product requirements. Their fictional personas, volumes, savings, and success targets are planning material, not customer evidence. Some implementation assumptions predate the current application.
- docs/development/screenshots/tera-claim-workspace.png is an existing workspace capture; verify freshness before using it as visual authority.
- frontend/static/logo.webp is the existing identity asset.
- Synthetic or anonymized examples may demonstrate workflows when clearly identified as examples. No validated customer testimonials, adoption statistics, fraud accuracy, or savings claims have been supplied.

## Product Principles

1. Make the current claim status and next action understandable to the employee.
2. Keep decisions traceable to policy, evidence, and recorded reasons.
3. Route uncertainty and risk to a human with enough context to decide.
4. Reduce repeated entry and checking without hiding failures or missing information.
5. Present demonstrated capabilities honestly and protect sensitive claim data.

## Accessibility & Inclusion

Preserve keyboard operation, visible focus, reduced-motion behavior, and usable mobile layouts established in DESIGN.md. Status and next actions must remain understandable without relying on color or animation alone.
