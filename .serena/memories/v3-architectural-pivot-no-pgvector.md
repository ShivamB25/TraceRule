# V3 Architectural Pivot: pgvector Removal

**Date:** 2026-02-22
**Decision:** Remove pgvector, numpy, embedding-based retrieval, and RRF from the V3 pipeline.

## Why pgvector Was Removed

1. **Embedding structured data is an anti-pattern.** Business records (expenses, employees, transactions) are tabular — they don't embed well. Semantic similarity between a rubric like "Is this gift lavish?" and a JSON row `{amount: 50000, category: "entertainment"}` produces near-zero useful signal.

2. **No embedding model in our stack.** Anthropic has no embedding API. We'd need a second provider (OpenAI/Voyage/Cohere) — another API key, another bill, another dependency. The project is Anthropic-first.

3. **The 1536 dimension was hardcoded to OpenAI's ada-002.** Switching providers would require schema migration.

4. **The embedding function was a dead stub** returning `[0.0] * 1536`. It would crash any live demo.

5. **RRF (Reciprocal Rank Fusion) is for document retrieval, not structured data scanning.** Overkill for short tabular records.

## New Architecture: SQL Pre-Filtering + Multi-Agent Semantic Evaluation

### Rule types and their scan paths:

| Rule Type | Example | Scan Path |
|-----------|---------|-----------|
| Pure deterministic | `age < 18` | Run compiled SQL → save violations (confidence=1.0) |
| Mixed (deterministic + vague) | `amount > 500 AND IS_VAGUE("lavish")` | Compiled SQL has `1=1` for vague → returns superset → courtroom evaluates each candidate |
| Pure vague | `IS_VAGUE("lavish gift")` | BM25 text search on `company_records` → courtroom evaluates each candidate |

### Key insight:
The Adversarial Courtroom (Prosecutor + Defender + Chief Justice, all Claude) IS the reranker. Three agents debating > any embedding similarity score. No separate reranker needed.

### BM25 fallback for pure-vague rules:
`_find_bm25_candidates()` uses Postgres-native `ts_rank` + `websearch_to_tsquery` on the `company_records.ts_vector` column. No extensions, no external APIs.

### SQL pre-filter failure fallback:
If compiled SQL fails for a mixed rule, scanner falls back to BM25 search automatically.

## What Was Removed

- `pgvector>=0.4.2` from pyproject.toml dependencies
- `numpy>=2.4.2` from pyproject.toml dependencies (was never actually used)
- `from pgvector.sqlalchemy import Vector` import in models.py
- `VectorVariant` TypeDecorator class in models.py
- `embedding` column from `CompanyRecord` model
- `CREATE EXTENSION IF NOT EXISTS vector` from main.py lifespan
- `_generate_query_embedding()` stub function from scanner.py
- `find_suspicious_rows()` RRF query from scanner.py

## What Was Kept

- `TSVectorVariant` TypeDecorator (still needed for BM25)
- `CompanyRecord.ts_vector` column (GIN-indexed for BM25)
- `CompanyRecord.search_text` column (source text for tsvector)
- `CompanyRecord` model (still needed for pure-vague BM25 search)

## Pitch framing for judges

"Strict SQL Pre-Filtering + Multi-Agent Semantic Evaluation" — deterministic SQL narrows candidates, then an adversarial courtroom of three Claude agents debates each case. No naive vector search, no embedding anti-patterns on structured data.
