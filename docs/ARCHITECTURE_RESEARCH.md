# TraceRule — Architecture Research

## Why not RAG?

RAG is probabilistic. Scanning 10 million rows with a RAG system means 10 million chances for hallucination, inconsistent reasoning, and wasted tokens. You can't audit it because the decision logic lives in a latent space at scan time.

TraceRule treats legal text as source code. Claude Sonnet 4.6 compiles PDF policies into executable representations during ingestion. Once a rule is compiled, the scan phase never touches the LLM for deterministic rules. Compliance officers audit the logic once. Execution is deterministic and fast.

## Design decisions

### PydanticAI, not LangChain

LangChain and Instructor add brittle dependency chains and hide what's happening at runtime. PydanticAI handles structured outputs via `output_type`, manages validation and retries, and stays out of the way. The agent logic remains readable. V3 uses `@output_validator` with `ModelRetry` for SQL auto-healing — a pattern that would require multiple abstraction layers in LangChain.

### V1: SQL compiled upfront

"Agentic scanning" where an LLM evaluates every database row is slow and expensive. Instead, SQL is generated during ingestion. The scan engine runs `await db.execute(text(rule.compiled_sql))`, taking about 2ms per rule regardless of complexity.

### V3: Deontic Logic ASTs, not raw SQL

V1 asks Claude to write SQL directly. This works but has two problems: (1) Claude occasionally generates SQL that references nonexistent columns or uses wrong syntax, and (2) subjective clauses like "employees must not accept lavish gifts" get `compiled_sql=None` and are skipped entirely.

V3 solves both problems:

1. **AST output**: Claude produces `LogicNode` trees — formal deontic logic structures (AND/OR/UNLESS nodes with typed `Condition` leaves). A pure-Python compiler then generates SQL deterministically. The LLM never writes SQL directly.

2. **IS_VAGUE operator**: Subjective conditions get `operator: "IS_VAGUE"` in the AST. The compiler maps these to `1=1` in SQL (a deliberate superset), and the adversarial courtroom evaluates each candidate from the superset. Nothing is skipped.

3. **SQL auto-healing**: The `@output_validator` runs `EXPLAIN` on generated SQL in a sandboxed transaction. If Postgres rejects it, the full error message goes back to Claude via `ModelRetry`. Claude sees "column 'emplyee_age' does not exist" and self-corrects to `employee_age`. Up to 4 retries. SQL that makes it through is guaranteed executable.

### Adversarial Courtroom, not single-agent evaluation

A single LLM call asking "is this a violation?" produces overconfident, poorly calibrated answers. The adversarial courtroom forces structured reasoning:

- **Prosecutor** builds the strongest case for violation
- **Defender** finds every reasonable doubt
- **Chief Justice** weighs both arguments, produces `Verdict{is_violation, confidence_score, reasoning}`

Prosecutor and Defender run in parallel via `asyncio.gather`. This adversarial structure produces calibrated confidence scores — the Chief Justice is less likely to say 0.95 confidence when there's a strong defense argument. Single-agent evaluation tends to anchor on the first interpretation.

### BM25 over embeddings (pgvector removed)

We initially built V3 with pgvector and embedding-based retrieval, then removed it. Five reasons:

1. **Embedding structured data is an anti-pattern.** Business records are tabular. Semantic similarity between "Is this gift lavish?" and `{amount: 50000, category: "entertainment"}` produces near-zero useful signal.

2. **No embedding model in our stack.** Anthropic has no embedding API. Adding a second provider (OpenAI/Voyage/Cohere) means another API key, another dependency, another cost.

3. **The embedding stub was dead code.** The function was returning `[0.0] * 1536`. Any demo would crash or produce garbage results.

4. **RRF (Reciprocal Rank Fusion) was solving a self-created problem.** Fusing a bad embedding signal with BM25 doesn't improve retrieval — it degrades it.

5. **The courtroom IS the reranker.** Three Claude agents debating a case produces better signal than any cosine similarity score. Why add a mediocre retrieval step before a superior evaluation step?

The replacement: Postgres-native `ts_rank` + `websearch_to_tsquery` for candidate retrieval (BM25). No extensions. No external APIs. The courtroom handles semantic evaluation.

### Database-backed human review

Workflow engines that try to "pause" for human input add complexity for no gain. Rules are saved with `status="pending_review"`. The frontend polls. A `PATCH` endpoint moves status to `approved`. Stateless, horizontally scalable, survives restarts.

### pymupdf4llm for PDF parsing

Vision-based PDF parsers like Docling need PyTorch, GPU memory, and often take minutes per document. `pymupdf4llm` converts PDF to markdown in under 200ms on a CPU. It preserves tables and headings without the overhead.

### Global Ontology extraction (V3)

Before chunking a long policy, V3 extracts a `GlobalOntology` — a dictionary mapping domain terms to database columns and threshold values. "High-value transaction" → `transactions.amount_paid > 10000`. This prevents the extractor agent from interpreting the same term differently across chunks. The ontology is injected into every chunk's extraction context.

### Minimal infrastructure

No Celery, no Redis, no Alembic, no pgvector. FastAPI `BackgroundTasks` handles ingestion. `APScheduler` with `AsyncIOScheduler` runs in-process for the scan interval. `Base.metadata.create_all` initializes the schema on startup. Fewer moving parts, easier to deploy.

## Research backing

### MECE decomposition

The compiler agent applies Mutually Exclusive, Collectively Exhaustive (MECE) decomposition to policy text. Each legal paragraph breaks into atomic rules, where each rule maps to a single logical statement. This prevents overlapping queries and coverage gaps.

### DERECHA (IEEE TSE 2023)

Research published in the 2023 IEEE Transactions on Software Engineering found that deterministic code execution achieved over 89% precision on GDPR compliance tasks. Probabilistic NLP approaches hovered around 60%. TraceRule V1 implements this finding by converting natural language requirements into executable SQL. V3 extends it by also handling the subjective remainder through adversarial multi-agent evaluation rather than ignoring it.

### Deontic Logic

Deontic logic is the formal logic of obligations, permissions, and prohibitions — the exact modalities that compliance policies express. V3's LogicNode trees are a practical implementation of deontic logic structures, with the UNLESS operator implementing defeasible reasoning (obligations that can be overridden by exceptions). This is a well-studied formalism in legal AI research.

### Adversarial Debate for Calibration

Multi-agent debate has been shown to improve factual accuracy and calibration in LLM outputs (Irving et al., "AI safety via debate"). The courtroom structure applies this principle to compliance evaluation — the Defender's counterarguments force the system to be less overconfident and more principled in its violation determinations.
