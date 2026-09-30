# Agent Flow

The target claim flow is:

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

The flow is a target architecture, not a claim that all steps are already implemented.

Related documents:

- [[overview|Architecture overview]]
- [[../../BRD_Expense_Reimbursement_Agent|Business requirements]]
