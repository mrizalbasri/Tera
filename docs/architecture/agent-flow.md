# Agent Flow

The implemented processing flow is:

```mermaid
flowchart TD
    Upload[Upload receipt] --> Extract[Extract fields]
    Extract --> Validate[Validate fields and policy]
    Validate --> Duplicate[Check duplicate]
    Duplicate --> Risk[Score risk]
    Risk --> Decision{Decision}
    Decision -->|Approve| Approved[Record approval]
    Decision -->|Clarify| Clarify[Ask employee]
    Decision -->|Escalate| Review[Human review]
    Decision -->|Reject| Rejected[Record rejection]
```

Intake saves receipts before processing begins. Clarification resumes processing
with the stored answer; human review applies a new decision without repeating
extraction. The workflow also records policy evaluation separately from field
validation. Completed requests replay stored outcomes.

See [[agent-modules|Agent module boundaries]] for graph modules and responsibilities.

Related documents:

- [[overview|Architecture overview]]
- [[../BRD_Expense_Reimbursement_Agent|Business requirements]]
