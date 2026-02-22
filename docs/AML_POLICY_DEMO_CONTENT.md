## Anti-Money Laundering Monitoring Policy (Demo)

### 1) High-value transaction control
Any transaction with amount paid above USD 10,000 must be flagged for compliance review.

### 2) High-value cash control
Any transaction with payment format equal to Cash and amount paid above USD 5,000 must be flagged.

### 3) Cross-currency high-value control
Any transaction where payment currency differs from receiving currency and amount paid is above USD 8,000 must be flagged.

### 4) Repeated transfer pattern control
If the same source account sends transfers to the same destination account more than 5 times in a single day, that account pair must be flagged.

### 5) Explicit laundering-tag escalation
Any transaction marked as laundering by upstream monitoring signals must be flagged for immediate investigation.

### 6) Subjective analyst review clause (V3 courtroom path)
Transactions that appear inconsistent with normal customer behavior, even when no deterministic threshold is crossed, should be escalated for semantic review.

Examples include combinations of factors such as:
- transfer purpose text that appears evasive or intentionally vague,
- timing patterns that look staged to avoid reporting,
- account-to-account movement that appears layered without clear business rationale.

This clause is intentionally subjective and should be evaluated by the V3 adversarial courtroom (Prosecutor, Defender, Chief Justice), not by deterministic SQL alone.
