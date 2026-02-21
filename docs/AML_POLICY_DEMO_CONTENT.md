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

### 6) Subjective analyst review clause
Transactions with unusual narrative context that cannot be captured through deterministic fields should be escalated for analyst judgment.
