# TraceRule — Judges Document

## One Line

TraceRule compiles compliance policies into deontic logic ASTs, auto-heals its own SQL via database stack traces, and runs an adversarial multi-agent courtroom for subjective clauses. The AI runs during upload. Every deterministic scan after that costs zero tokens.

---

## The Problem With Current Approaches

Every compliance AI tool on the market does some version of the same thing: take a policy, take some data, throw both at an LLM, and ask "does this violate anything?" This is RAG-based compliance scanning, and it has three problems that nobody talks about honestly:

1. **It doesn't scale.** Scanning 10 million database rows means 10 million LLM calls. At $3/million input tokens with Claude, scanning a mid-size company's transaction database costs hundreds of dollars per run. Per policy. Per day.

2. **It hallucinates.** Run the same scan twice, get different results. An LLM might flag a $9,500 transaction as violating a $10,000 threshold because it "felt" close. Try explaining that to a compliance officer who needs to file a regulatory report.

3. **You can't audit it.** When a regulator asks "why was this flagged?", the answer is "the model's latent space determined it during inference." That's not an answer. That's a liability.

4. **It can't handle subjectivity.** Real compliance policies contain clauses like "employees must not accept lavish gifts." RAG either skips these (incomplete coverage) or hallucinates thresholds (fabricated rules). There's no principled way to handle the gap between "amount > 500" and "lavish."

TraceRule takes a different position: compliance rules are not conversations. They're code. And the subjective ones that can't be code get tried in court.

---

## How It Actually Works

TraceRule has two coexisting pipelines. V1 handles straightforward deterministic compilation. V3 adds neuro-symbolic reasoning for the hard cases.

### V1 Pipeline — Deterministic Compilation

#### Phase 1 — Compilation (AI runs here, once)

A compliance officer uploads a PDF — could be an AML policy, GDPR requirements, internal HR rules, whatever. TraceRule does three things:

1. **Parse**: `pymupdf4llm` converts the PDF to markdown in under 200ms. No GPU. No PyTorch. No vision model. Just fast CPU-based text extraction that preserves tables and headings.

2. **Introspect**: The system queries `information_schema.columns` to discover every table and column in the company's PostgreSQL database. This schema context gets injected into the AI prompt so Claude knows exactly what columns exist to write SQL against.

3. **Compile**: Claude Sonnet 4.6 (with adaptive thinking cranked to `high` effort) reads the policy text and the database schema, then applies MECE decomposition — Mutually Exclusive, Collectively Exhaustive — to break the policy into atomic rules. Each rule becomes a structured object with a title, the exact source quote from the PDF, severity level, compiled SQL, and a determinism flag.

The SQL is written to **return violations**. If the policy says "all employees must be 18 or older," the compiled SQL is `SELECT id, age FROM employees WHERE age < 18`. The query finds what's wrong, not what's right.

Rules that are purely subjective — things like "employees must demonstrate good moral character" — get `is_deterministic=False` and `compiled_sql=None`. The system is honest about what it can and can't automate.

Every rule lands in the database with `status="pending_review"`. Nothing executes without a human saying so.

#### Phase 2 — Human Review (No AI)

The compliance officer sees each compiled rule in the dashboard: the title, the exact source quote from the PDF they can verify, the SQL query right there readable and auditable, and Approve/Reject buttons. They click one. That's it. A PATCH endpoint flips the status. Stateless. Survives restarts.

#### Phase 3 — Scanning (Zero AI)

APScheduler runs every 5 minutes (configurable). The scan engine executes `db.execute(text(rule.compiled_sql))` for each approved deterministic rule. About 2ms per rule. No LLM. No tokens. No hallucination. The results are reproducible.

After the scan finds new violations, an explainer agent (Claude at `medium` effort) generates a 2-sentence plain-English explanation for each one. This is the only post-compilation AI usage, and it's for human convenience — the detection itself was pure SQL.

---

### V3 Pipeline — Neuro-Symbolic with Adversarial Courtroom

V1 has a gap: subjective clauses get `compiled_sql=None` and are skipped entirely. V3 closes that gap.

#### Phase 1 — Deontic Logic Compilation

V3 doesn't ask Claude to write raw SQL. Instead, it compiles policy text into **deontic logic Abstract Syntax Trees** — formal logical structures that represent obligations, prohibitions, and permissions.

The compilation pipeline:

1. **Global Ontology Extraction**: Before chunking, a lexicon agent reads the full PDF and extracts a `GlobalOntology` — a dictionary of domain-specific terms, their definitions, and mappings to database columns. "High-value transaction" → `transactions.amount_paid > 10000`. This prevents inconsistent interpretations across chunks.

2. **Chunking**: The policy text is split into overlapping chunks (4000 chars, 500 char overlap) so the extractor agent can process long documents without context truncation.

3. **AST Extraction**: For each chunk, a PydanticAI extractor agent produces `SymbolicRule` objects. Each contains a `LogicNode` tree — recursive AND/OR/UNLESS nodes with leaf `Condition` objects. Conditions can be concrete (`operator: "GREATER_THAN"`, `value: 10000`) or vague (`operator: "IS_VAGUE"`, `value: "lavish gift"`).

4. **AST → SQL Compilation**: A pure-Python recursive compiler (`ast_compiler.py`) walks the logic tree and generates SQL deterministically. No LLM involved. AND/OR map to SQL AND/OR. UNLESS maps to defeasible logic (`AND NOT`). IS_VAGUE conditions compile to `1=1` — a deliberate superset that the courtroom will narrow down later. CONTAINS maps to ILIKE.

5. **SQL Auto-Healing**: The extractor agent has an `@output_validator` that runs `EXPLAIN` on every generated SQL query inside a sandboxed nested transaction. If Postgres rejects the SQL (bad column name, syntax error, type mismatch), the validator catches the error and raises `ModelRetry` with the full Postgres stack trace injected back into the prompt. Claude sees exactly what went wrong and self-corrects. This loop runs up to 4 retries. The SQL that makes it through is guaranteed to be executable.

```python
# Simplified: the auto-heal loop
@extractor_agent.output_validator
async def validate_sql(ctx, rules):
    for rule in rules:
        sql = compile_ast_to_sql(rule.logic_tree)
        try:
            await db.execute(text(f"EXPLAIN {sql}"))  # sandboxed
        except Exception as e:
            raise ModelRetry(f"SQL failed: {e}\nFix the logic tree.")
```

#### Phase 2 — Human Review

Same as V1. The compliance officer sees each rule with its logic tree visualization, the compiled SQL, the source quote, and Approve/Reject buttons. They audit the SQL and the logic structure.

#### Phase 3 — Three-Path Scanning

V3 classifies each approved rule and routes it to the appropriate scan path:

V3 classifies each approved rule via `requires_semantic_scan` and routes it:

**Path A — Pure Deterministic** (`requires_semantic_scan=False`)
Same as V1. Execute compiled SQL. Save violations with `confidence=1.0`. Done.

**Path B — Mixed Rules** (`requires_semantic_scan=True`, compiled SQL exists)
The compiled SQL has `1=1` where IS_VAGUE conditions appear, producing a *superset* of potential violators. Each candidate from this superset goes to the adversarial courtroom for evaluation. If the SQL pre-filter fails, the scanner falls back to BM25.

**Path C — Pure Vague Rules** (`requires_semantic_scan=True`, no compiled SQL)
No useful SQL exists. The scanner runs BM25 text search using Postgres-native `ts_rank` + `websearch_to_tsquery` on the `company_records` table. No pgvector. No embeddings. No external search engine. Top candidates go to the courtroom.

#### The Adversarial Courtroom

This is the semantic evaluation layer for subjective clauses. Three Claude agents debate each candidate violation:

1. **Prosecutor**: Argues why this record violates the policy. Sees the record data, the rule's semantic rubric, and the source quote. Builds the strongest possible case for violation.

2. **Defender**: Argues why this record does NOT violate the policy. Same evidence. Finds every reasonable doubt, alternative interpretation, mitigating context.

3. **Chief Justice**: Reads both arguments. Renders a `Verdict` with three fields: `is_violation` (boolean), `confidence_score` (0.0–1.0), and `reasoning` (the rationale).

Prosecutor and Defender run in parallel via `asyncio.gather`. The Chief Justice runs sequentially after both arguments are in.

This is adversarial deliberation, not a single LLM call deciding "is this a violation?" The Prosecutor can't just assert. The Defender forces it to justify. The Chief Justice weighs competing arguments. The result is a calibrated confidence score, not a binary yes/no.

---

## Why Not pgvector / Embeddings?

We built the V3 pipeline with pgvector initially and removed it for four reasons:

1. **Embedding structured data is an anti-pattern.** Business records (expenses, employees, transactions) are tabular. Semantic similarity between a rubric like "Is this gift lavish?" and a JSON row `{amount: 50000, category: "entertainment"}` produces near-zero useful signal.

2. **No embedding model in our stack.** Anthropic has no embedding API. We'd need a second provider (OpenAI, Voyage, Cohere) — another API key, another dependency, another bill. The project is Anthropic-first.

3. **The courtroom IS the reranker.** Three Claude agents debating a case produces better signal than any cosine similarity score. Why add a mediocre retrieval step before a superior evaluation step?

4. **BM25 is sufficient for candidate retrieval.** Postgres-native `ts_rank` with `websearch_to_tsquery` finds relevant text records without any extensions, external APIs, or additional models. The courtroom handles the semantic heavy lifting.

The architecture is: **SQL Pre-Filtering + Multi-Agent Semantic Evaluation**. Deterministic SQL narrows candidates. An adversarial courtroom of three Claude agents debates each case. No naive vector search. No embedding anti-patterns on structured data.

---

## What Makes This Different

### vs. RAG-Based Compliance Tools

| | RAG Approach | TraceRule V1 | TraceRule V3 |
|---|---|---|---|
| Cost per scan | $$$$ (LLM per row) | ~$0 (SQL execution) | ~$0 deterministic, LLM only for vague candidates |
| Consistency | Different results each run | Identical results, always | Deterministic + calibrated confidence for subjective |
| Audit trail | "The model decided" | Here's the exact SQL query | SQL + logic tree + courtroom reasoning |
| Subjective clauses | Hallucinated thresholds | Skipped entirely | Adversarial courtroom with confidence scores |
| Speed | Minutes to hours | Milliseconds per rule | Milliseconds (deterministic) + seconds (courtroom) |
| LLM dependency | Every scan | Upload only | Upload + courtroom for vague clauses only |

### vs. Rule Engines (Drools, etc.)

Traditional rule engines require developers to manually encode every rule in a domain-specific language. TraceRule automates that encoding step — Claude reads the English policy and writes the logic tree. The human verifies. Net result: a compliance officer who can't write SQL still gets deterministic rule execution plus principled handling of subjective clauses.

### vs. Embedding-Based Retrieval (pgvector, Pinecone, etc.)

Embedding retrieval assumes semantic similarity in latent space correlates with compliance relevance. For structured tabular data, it doesn't. A $50,000 entertainment expense and a $50 office supply both embed as "business expense" — but only one is "lavish." The courtroom can reason about this. Cosine similarity cannot.

### The Research

The DERECHA paper (IEEE Transactions on Software Engineering, 2023) found that deterministic code execution achieved 89%+ precision on GDPR compliance tasks. Probabilistic NLP approaches topped out around 60%. TraceRule implements that finding for deterministic rules and extends it with adversarial multi-agent evaluation for the subjective remainder.

---

## Technical Architecture

```
                          ┌─────────────────────┐
                          │   Policy PDF Upload  │
                          └──────────┬──────────┘
                                     │
                          ┌──────────▼──────────┐
                          │  pymupdf4llm (CPU)   │
                          │  PDF → Markdown      │
                          │  < 200ms             │
                          └──────────┬──────────┘
                                     │
                    ┌────────────────┤
                    │                │
         ┌──────────▼──────────┐    │    ┌──────────────────────────┐
         │  DB Schema           │    │    │  Global Ontology (V3)    │
         │  Introspection       │    │    │  Lexicon of domain terms │
         │  information_schema  │    │    │  before chunking         │
         └──────────┬──────────┘    │    └──────────┬───────────────┘
                    │                │               │
                    └────────────────┤───────────────┘
                                     │
                 ┌───────────────────┼───────────────────┐
                 │ V1                │                    │ V3
      ┌──────────▼──────────┐       │         ┌──────────▼──────────┐
      │  Compiler Agent      │       │         │  Extractor Agent     │
      │  Claude Sonnet 4.6   │       │         │  Claude Sonnet 4.6   │
      │  → raw SQL           │       │         │  → Deontic Logic AST │
      │  3 retries           │       │         │  @output_validator   │
      └──────────┬──────────┘       │         │  EXPLAIN auto-heal   │
                 │                   │         │  4 retries           │
                 │                   │         └──────────┬──────────┘
                 │                   │                    │
      ┌──────────▼──────────┐       │         ┌──────────▼──────────┐
      │  list[CompiledRule]  │       │         │  AST Compiler (V3)   │
      │  title, source_quote │       │         │  Pure Python, no LLM │
      │  severity, SQL       │       │         │  LogicNode → SQL     │
      │  status=pending      │       │         │  IS_VAGUE → 1=1     │
      └──────────┬──────────┘       │         └──────────┬──────────┘
                 │                   │                    │
                 └───────────────────┤────────────────────┘
                                     │
                          ┌──────────▼──────────┐
                          │  HUMAN REVIEW        │
                          │  Approve / Reject    │
                          │  (frontend dashboard)│
                          └──────────┬──────────┘
                                     │
                 ┌───────────────────┼───────────────────┐
                 │                   │                    │
      ┌──────────▼──────────┐       │         ┌──────────▼──────────┐
      │  V1 Scanner          │       │         │  V3 Scanner          │
      │  db.execute(sql)     │       │         │  3 paths:            │
      │  ~2ms per rule       │       │         │  A: Pure SQL         │
      │  ZERO LLM            │       │         │  B: SQL + courtroom  │
      └──────────┬──────────┘       │         │  C: BM25 + courtroom │
                 │                   │         └──────────┬──────────┘
                 │                   │                    │
                 │                   │         ┌──────────▼──────────┐
                 │                   │         │  Adversarial         │
                 │                   │         │  Courtroom           │
                 │                   │         │  Prosecutor ─┐      │
                 │                   │         │  Defender ───┤gather │
                 │                   │         │  Chief Justice ─▶    │
                 │                   │         │  Verdict{confidence} │
                 │                   │         └──────────┬──────────┘
                 │                   │                    │
                 └───────────────────┼────────────────────┘
                                     │
                          ┌──────────▼──────────┐
                          │  Violations          │
                          │  record_pk           │
                          │  violating_data (JSON)│
                          │  confidence_score(V3) │
                          │  verdict_reasoning(V3)│
                          │  ai_explanation       │
                          └─────────────────────┘
```

### Stack

| Component | Choice | Why Not The Alternative |
|---|---|---|
| LLM Framework | PydanticAI | LangChain adds 30+ transitive deps and hides runtime behavior. PydanticAI uses `output_type=` for structured output, handles retries, stays readable. |
| LLM | Claude Sonnet 4.6 | Adaptive thinking with configurable effort. `high` for compilation (accuracy matters), `medium` for explanations (speed matters). |
| PDF Parsing | pymupdf4llm | Docling needs PyTorch and a GPU. pymupdf4llm runs on CPU in 200ms. |
| Database | PostgreSQL + SQLAlchemy async | The compiled SQL targets Postgres. asyncpg for non-blocking I/O. JSONB for violation data. Postgres-native `ts_rank` for BM25. |
| Scheduling | APScheduler 3.x | Celery + Redis is two extra services for a cron job. APScheduler runs in-process. |
| Background Tasks | FastAPI BackgroundTasks | Same reasoning. No external task queue needed. |
| Schema Management | `Base.metadata.create_all()` | Alembic is overkill for a system where the schema is fixed. |
| AST Compiler | Pure Python (recursive) | Deterministic SQL generation from logic trees. No LLM in the compilation path. |
| Semantic Evaluation | Adversarial Courtroom (3 agents) | Embeddings don't work on structured data. Three agents debating > cosine similarity. |
| Text Search | Postgres BM25 (ts_rank) | No pgvector extension, no embedding model, no external API. Built into Postgres. |

### Database Schema

**V1 Tables:**

| Table | Purpose |
|-------|---------|
| `policies` | Uploaded documents: `id, filename, markdown_text, status, created_at` |
| `rules` | V1 compiled SQL rules: `id, policy_id, title, source_quote, severity, compiled_sql, is_deterministic, status, created_at` |
| `violations` | V1 detected violations: `id, rule_id, record_pk, violating_data (JSONB), ai_explanation, status, detected_at` |

**V3 Tables:**

| Table | Purpose |
|-------|---------|
| `company_records` | Business data for BM25 search: `id, table_name, data_payload (JSONB), search_text, ts_vector (GIN-indexed)` |
| `v3_rules` | V3 rules with logic trees: `id, policy_id, rule_id, title, source_quote, severity, target_table, logic_tree_json (JSONB), requires_semantic_scan, compiled_sql, status, created_at` |
| `v3_violations` | V3 violations with confidence: `id, v3_rule_id, record_id, violation_data (JSONB), verdict_reasoning, confidence_score, status, detected_at` + unique dedup index on `(v3_rule_id, record_id)` |

Plus whatever business tables the company has (employees, transactions, etc.) — TraceRule discovers them via `information_schema` and writes SQL against them.

---

## The Code

### File Map

| File | What It Does |
|---|---|
| `app/main.py` | FastAPI app, lifespan (DB init + scheduler), CORS, health, V1+V3 router registration |
| `app/config.py` | Settings from .env (DATABASE_URL, API key, scan interval) |
| `app/database.py` | Async engine + session factory |
| `app/models.py` | ORM: Policy, Rule, Violation (V1) + CompanyRecord, V3Rule, V3Violation + TypeDecorators |
| `app/schemas.py` | Pydantic: V1 CompiledRule + V3 GlobalOntology, Condition, LogicNode, SymbolicRule, responses |
| `app/ast_compiler.py` | Pure-Python recursive AST→SQL compiler (AND/OR/UNLESS/IS_VAGUE/CONTAINS/IS_NULL) |
| `app/agents/compiler.py` | V1: policy text → list[CompiledRule] via Claude |
| `app/agents/explainer.py` | V1: violation → 2-sentence explanation via Claude |
| `app/agents/extractor.py` | V3: policy text → list[SymbolicRule] with @output_validator auto-heal |
| `app/agents/courtroom.py` | V3: Prosecutor + Defender + Chief Justice adversarial debate |
| `app/services/ingestion.py` | V1 ingest_policy() + V3 ingest_policy_v3() with ontology + chunking |
| `app/services/scanner.py` | V1 run_deterministic_scan() + V3 run_v3_scan() with 3-path routing |
| `app/routes/*.py` | V1 REST API (/api/v1/) |
| `app/api/router.py` | V3 REST API (/api/v3/) |

### Test Suite

78 tests across 10 files. In-memory SQLite via aiosqlite (Postgres compatibility handled by `JSONVariant` and `TSVectorVariant` TypeDecorators). Tests run without a database server, without an API key, without any external service.

| File | Tests | Covers |
|---|---|---|
| `tests/test_ast_compiler.py` | 23 | All AST operators, logic types, edge cases, boolean handling |
| `tests/test_v3_rules.py` | 11 | V3 rule CRUD, filters, approve/reject |
| `tests/test_rules.py` | 10 | V1 rule CRUD, filters, approve/reject |
| `tests/test_v3_scanner.py` | 8 | V3 scanner, bad SQL, dedup, endpoint |
| `tests/test_violations.py` | 7 | V1 violation CRUD, filters |
| `tests/test_v3_violations.py` | 6 | V3 violation CRUD, filters |
| `tests/test_policies.py` | 5 | V1 upload, missing file, health |
| `tests/test_v3_policies.py` | 4 | V3 upload PDF/MD, 422, 400 |
| `tests/test_scanner.py` | 4 | V1 scanner, bad SQL, explanation limit |

---

## API Endpoints

### V1 Endpoints (prefix: /api/v1/)

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/policies/upload` | Upload PDF, kicks off background AI compilation |
| GET | `/api/v1/rules` | List rules (filter by `?status=` and `?policy_id=`) |
| GET | `/api/v1/rules/{id}` | Get single rule with SQL |
| PATCH | `/api/v1/rules/{id}/approve` | Approve rule for scanning |
| PATCH | `/api/v1/rules/{id}/reject` | Reject rule |
| PATCH | `/api/v1/rules/{id}/status` | Generic status update |
| GET | `/api/v1/violations` | List violations (filter by `?rule_id=` and `?status=`) |
| GET | `/api/v1/violations/{id}` | Get single violation with explanation |
| POST | `/api/v1/scan` | Trigger scan manually |

### V3 Endpoints (prefix: /api/v3/)

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v3/policies/upload` | Upload PDF, neuro-symbolic compilation with ontology + AST + auto-heal |
| GET | `/api/v3/rules` | List V3 rules (filter by `?status=` and `?policy_id=`) |
| GET | `/api/v3/rules/{id}` | Get single V3 rule with logic tree and SQL |
| PATCH | `/api/v3/rules/{id}/approve` | Approve V3 rule |
| PATCH | `/api/v3/rules/{id}/reject` | Reject V3 rule |
| GET | `/api/v3/violations` | List V3 violations with confidence scores |
| GET | `/api/v3/violations/{id}` | Get single V3 violation with verdict reasoning |
| POST | `/api/v3/scan` | Trigger V3 scan (deterministic + courtroom) |

| GET | `/health` | Health check |

---

## Frontend

React 19 + Vite + Tailwind v4. Dark theme. Three panels:

1. **Upload Panel** — Drag-and-drop PDF. Shows processing state, then "Compiled N rules from filename.pdf." Polls the backend every 3 seconds until rules appear.

2. **Review Panel** — Tabbed view (Pending / Approved / Rejected) with cards showing title, severity badge, source quote, logic tree, target table, semantic/deterministic mode, and Approve/Reject buttons.

3. **Violations Panel** — Paginated scan results (25 per page). Deterministic violations show record data with `confidence = 1.0`. Semantic violations include courtroom verdict reasoning with confidence scores.

The frontend targets V3 endpoints (`/api/v3/`). All state lives in `App.tsx` via `useState`. Data fetching uses vanilla `fetch()` in `api.ts`. Violations are paginated: `{items, total_count, limit, offset}`.

---

## Deployment

Docker Compose with two services:
- `db`: Postgres 16 Alpine with health check
- `api`: Multi-stage build (uv for deps, python:3.13-slim runtime, non-root user)

```bash
cp .env.example .env
export ANTHROPIC_API_KEY=your_key
docker compose up --build
# API: http://localhost:8000/docs
# Frontend: http://localhost:3000 (dev)
```

No pgvector extension needed. No additional database extensions. Standard Postgres.

---

## What We'd Build Next

In order of impact:

1. **V3 Frontend** — React components for AST tree visualization, courtroom verdict display with confidence gauges, and side-by-side Prosecutor/Defender argument view.

2. **Company Records Loader** — Data ingestion pipeline that populates the `company_records` table with BM25-indexed business data for pure-vague rule scanning.

3. **Rule Versioning** — When a policy PDF is re-uploaded, diff the new rules against the old ones. Show what changed. Don't lose approved rules.

4. **SQL Sandboxing** — Right now the compiled SQL executes with full database permissions. Production would need a read-only connection, query timeouts, and row-count limits.

5. **Conflict Detection** — Two policies might produce contradictory rules. Detect overlapping WHERE clauses and flag conflicts before approval.

6. **Confidence Thresholds** — Allow compliance officers to set minimum confidence scores for courtroom verdicts. Below threshold → manual review queue instead of auto-flagging.

---

## Why This Matters

Compliance teams at banks, healthcare companies, and regulated industries spend millions of dollars annually on manual policy enforcement. They read a policy document, manually check database records, and write reports. When they use AI tools, they get probabilistic answers they can't trust or audit.

TraceRule doesn't replace the compliance officer. It gives them a compiler and a courtroom. They feed it a policy, it produces logic trees and SQL, they verify it makes sense, and then it runs — deterministically for concrete rules, adversarially for subjective ones. The AI did its job during upload. After that, deterministic scanning is just PostgreSQL doing what PostgreSQL does best: running queries fast. And subjective scanning is three Claude agents doing what adversarial debate does best: calibrating uncertainty.

The compliance officer's job shifts from "manually check 10,000 records" to "verify that this logic tree correctly captures the intent of section 4.2, and review the courtroom's reasoning on the edge cases." That's a better use of a $150K/year professional.
