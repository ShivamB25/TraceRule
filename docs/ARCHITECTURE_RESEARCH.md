# TraceRule — Architecture

## Why not RAG?

RAG is probabilistic. Scanning 10 million rows with a RAG system means 10 million chances for hallucination, inconsistent reasoning, and wasted tokens. You can't audit it because the decision logic lives in a latent space at scan time.

TraceRule treats legal text as source code. Claude Sonnet 4.6 compiles PDF policies into PostgreSQL SELECT queries during ingestion. Once a rule becomes SQL, the scan phase never touches the LLM. Compliance officers audit the SQL once. Execution is deterministic and fast.

## Design decisions

### PydanticAI, not LangChain

LangChain and Instructor add brittle dependency chains and hide what's happening at runtime. PydanticAI handles structured outputs via `output_type`, manages validation and retries, and stays out of the way. The agent logic remains readable.

### SQL compiled upfront

"Agentic scanning" where an LLM evaluates every database row is slow and expensive. Instead, SQL is generated during ingestion. The scan engine runs `await db.execute(text(rule.compiled_sql))`, taking about 2ms per rule regardless of complexity.

### Database-backed human review

Workflow engines that try to "pause" for human input add complexity for no gain. Rules are saved with `status="pending_review"`. The frontend polls. A `PATCH` endpoint moves status to `approved`. Stateless, horizontally scalable, survives restarts.

### pymupdf4llm for PDF parsing

Vision-based PDF parsers like Docling need PyTorch, GPU memory, and often take minutes per document. `pymupdf4llm` converts PDF to markdown in under 200ms on a CPU. It preserves tables and headings without the overhead.

### Minimal infrastructure

No Celery, no Redis, no Alembic. FastAPI `BackgroundTasks` handles ingestion. `APScheduler` with `AsyncIOScheduler` runs in-process for the scan interval. `Base.metadata.create_all` initializes the schema on startup. Fewer moving parts, easier to deploy.

## Research backing

### MECE decomposition

The compiler agent applies Mutually Exclusive, Collectively Exhaustive (MECE) decomposition to policy text. Each legal paragraph breaks into atomic rules, where each rule maps to a single IF-THEN statement. This prevents overlapping queries and coverage gaps.

### DERECHA (IEEE TSE 2023)

Research published in the 2023 IEEE Transactions on Software Engineering found that deterministic code execution achieved over 89% precision on GDPR compliance tasks. Probabilistic NLP approaches hovered around 60%. TraceRule implements this finding by converting natural language requirements into executable SQL.
