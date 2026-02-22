## Anti-Money Laundering Monitoring Policy (Demo, LLM-Robust Version)

This version is written for reliable machine extraction into deterministic and semantic rules.
Use this text to create the demo PDF.

### A. Scope
This policy applies to all records in the `transactions` table.

### B. Definitions
1. "High-value transaction" means `amount_paid > 10000`.
2. "High-value cash transaction" means `payment_format = 'Cash' AND amount_paid > 5000`.
3. "Cross-currency transaction" means `payment_currency != receiving_currency`.
4. "Flagged transaction" means the transaction must be reported for compliance review.

### C. Deterministic Controls

#### Rule AML-1: High-value transaction
If a transaction has `amount_paid > 10000`, then that transaction must be flagged.

#### Rule AML-2: High-value cash transaction
If a transaction has `payment_format = 'Cash'` and `amount_paid > 5000`, then that transaction must be flagged.

#### Rule AML-3: Cross-currency high-value transaction
If a transaction has `payment_currency != receiving_currency` and `amount_paid > 8000`, then that transaction must be flagged.

#### Rule AML-4: Repeated account-pair transfers (same day)
If the same `from_account` sends to the same `to_account` more than 5 times on the same calendar day, then those transactions must be flagged.

#### Rule AML-5: Upstream laundering signal
If `is_laundering = TRUE`, then that transaction must be flagged for immediate investigation.

### D. Subjective Control (Semantic Courtroom Path)

#### Rule AML-6: Behavior inconsistent with normal customer activity
If a transaction appears inconsistent with normal customer behavior, the transaction should be escalated for semantic review even when deterministic thresholds are not crossed.

For semantic review, evaluate these rubrics:
1. The transaction narrative appears evasive, vague, or intentionally obscured.
2. The timing pattern appears staged to avoid reporting controls.
3. The account-to-account movement appears layered without a clear business rationale.

### E. Exception Handling
If a transaction qualifies under Rules AML-1 through AML-5, it must still be flagged even if an operator manually labels it as low risk.
