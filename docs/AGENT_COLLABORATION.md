# How TraceRule's agents process policy documents

Seven Claude agents, two pipelines, one goal: turn legal text into enforceable database queries. No agent talks to another directly. The service layer passes typed Pydantic schemas between them.

---

## 1. Full system overview

```mermaid
flowchart TD
    PDF["Policy PDF upload"]

    subgraph TEXT_EXTRACT["Text extraction - CPU, ~200ms"]
        PYMUPDF["pymupdf4llm.to_markdown()"]
    end

    subgraph SCHEMA["Database introspection"]
        INTRO["information_schema.columns<br/>schema context string"]
    end

    PDF --> PYMUPDF
    PYMUPDF --> MARKDOWN["Markdown text"]
    MARKDOWN --> COMPILER
    MARKDOWN --> LEXICON
    MARKDOWN --> CHUNKER

    subgraph V1_PATH["V1 Pipeline"]
        direction TB
        COMPILER["Compiler Agent<br/>Claude Sonnet 4.6<br/>adaptive thinking, high effort<br/>3 retries"]
        RULES_V1["Rule rows<br/>status=pending_review<br/>compiled_sql + source_quote"]
        COMPILER --> RULES_V1
    end

    subgraph V3_PATH["V3 Pipeline"]
        direction TB
        LEXICON["Lexicon Agent<br/>Claude Sonnet 4.6<br/>thinking budget: 4K tokens<br/>reads first 12K chars"]
        ONTOLOGY["GlobalOntology<br/>term to definition map"]
        CHUNKER["Chunker<br/>4000 chars, 500 overlap"]
        EXTRACTOR["Extractor Agent<br/>Claude Sonnet 4.6<br/>thinking budget: 10K tokens<br/>4 retries + output_validator"]
        AST_COMP["AST Compiler<br/>pure Python, no LLM<br/>LogicNode to SQL WHERE"]
        EXPLAIN["EXPLAIN sandbox<br/>begin_nested then rollback"]
        RETRY{"Postgres<br/>error?"}
        MODEL_RETRY["ModelRetry<br/>full stack trace<br/>back to Claude"]
        RULES_V3["V3Rule rows<br/>status=pending_review<br/>logic_tree_json + compiled_sql"]

        LEXICON --> ONTOLOGY
        ONTOLOGY --> EXTRACTOR
        CHUNKER --> EXTRACTOR
        EXTRACTOR --> AST_COMP
        AST_COMP --> EXPLAIN
        EXPLAIN --> RETRY
        RETRY -- "Yes" --> MODEL_RETRY
        MODEL_RETRY --> EXTRACTOR
        RETRY -- "No, SQL valid" --> RULES_V3
    end

    INTRO --> COMPILER
    INTRO --> EXTRACTOR

    RULES_V1 --> HITL["Human review<br/>Approve or Reject"]
    RULES_V3 --> HITL

    HITL --> SCAN_V1["V1 Scanner<br/>db.execute compiled_sql<br/>~2ms per rule, zero LLM"]
    HITL --> SCAN_V3["V3 Scanner<br/>3-path routing"]

    SCAN_V1 --> VIOLATIONS["Violations"]
    SCAN_V3 --> VIOLATIONS

    SCAN_V1 --> EXPLAINER["Explainer Agent<br/>adaptive, medium effort<br/>capped at 25 per scan"]
    EXPLAINER --> VIOLATIONS

    style V1_PATH fill:#1e293b,stroke:#3b82f6,color:#e2e8f0
    style V3_PATH fill:#1e293b,stroke:#10b981,color:#e2e8f0
    style HITL fill:#92400e,stroke:#f59e0b,color:#fef3c7
```

---

## 2. V3 ingestion: from PDF to validated logic trees

This is the sequence of agent invocations during a single `POST /api/v3/policies/upload`. The Lexicon Agent runs first and its output feeds every subsequent Extractor call.

```mermaid
sequenceDiagram
    participant U as Upload endpoint
    participant I as ingestion.py
    participant L as Lexicon Agent
    participant C as Chunker
    participant E as Extractor Agent
    participant A as AST Compiler
    participant P as Postgres

    U->>I: ingest_policy_v3(db, bytes, filename, policy_id)
    I->>I: _extract_policy_text() returns markdown

    Note over I,L: Phase 1: Build shared vocabulary
    I->>L: run_stream(first 12K chars)
    L-->>I: GlobalOntology{definitions}

    Note over I,P: Phase 2: Get DB column names
    I->>P: SELECT FROM information_schema.columns
    P-->>I: schema context string

    Note over I,C: Phase 3: Split for context windows
    I->>C: _chunk_policy_text(markdown, 4000, 500)
    C-->>I: list of string chunks

    loop For each chunk
        Note over I,E: Phase 4: Extract deontic logic AST
        I->>E: run(chunk, deps={db, schema, ontology})
        E->>E: Claude produces list of SymbolicRuleDraft

        Note over E,P: Phase 5: Reflexion loop (@output_validator)
        E->>A: compile_ast_to_sql(logic_tree)
        A-->>E: SQL WHERE clause
        E->>P: EXPLAIN sql (inside begin_nested)

        alt Postgres rejects SQL
            P-->>E: DBAPIError
            E->>E: ModelRetry("column 'emplyee_age' does not exist...")
            Note over E: Claude self-corrects, retries (up to 4x)
        else SQL passes EXPLAIN
            P-->>E: OK
            E-->>I: list of SymbolicRuleDraft with compiled_sql filled
        end

        I->>P: INSERT V3Rule rows (status=pending_review)
    end
```

---

## 3. V3 scanner: three-path routing

After human approval, each V3 rule takes one of three scan paths based on whether its logic tree contains `IS_VAGUE` conditions.

```mermaid
flowchart TD
    TRIGGER["POST /api/v3/scan"]
    FETCH["SELECT approved V3 rules"]

    TRIGGER --> FETCH
    FETCH --> LOOP["For each approved rule"]

    LOOP --> CHECK{"requires_semantic_scan?"}

    CHECK -- "False" --> EXEC_A
    CHECK -- "True" --> HAS_SQL{"compiled_sql<br/>exists?"}

    HAS_SQL -- "Yes, mixed rule" --> EXEC_B
    HAS_SQL -- "No, pure vague" --> BM25_C

    subgraph PATH_A["Path A: Pure deterministic"]
        direction TB
        EXEC_A["db.execute compiled_sql"]
        SAVE_A["Save V3Violation<br/>confidence = 1.0<br/>Deterministic SQL match"]
        EXEC_A --> SAVE_A
    end

    subgraph PATH_B["Path B: SQL pre-filter + courtroom"]
        direction TB
        EXEC_B["db.execute compiled_sql<br/>IS_VAGUE compiles to 1=1, gives superset"]
        FAIL_B{"SQL<br/>failed?"}
        BM25_B["Fallback: BM25 text search<br/>ts_rank + websearch_to_tsquery"]
        CANDIDATES_B["Candidate rows"]
        COURT_B["Adversarial Courtroom<br/>per candidate"]

        EXEC_B --> FAIL_B
        FAIL_B -- "Yes" --> BM25_B
        BM25_B --> CANDIDATES_B
        FAIL_B -- "No" --> CANDIDATES_B
        CANDIDATES_B --> COURT_B
    end

    subgraph PATH_C["Path C: BM25 + courtroom"]
        direction TB
        BM25_C["BM25 text search<br/>on company_records table<br/>ts_rank + websearch_to_tsquery"]
        CANDIDATES_C["Candidate rows"]
        COURT_C["Adversarial Courtroom<br/>per candidate"]

        BM25_C --> CANDIDATES_C
        CANDIDATES_C --> COURT_C
    end

    COURT_B --> VERDICT_B{"Verdict:<br/>is_violation?"}
    COURT_C --> VERDICT_C{"Verdict:<br/>is_violation?"}

    VERDICT_B -- "True" --> SAVE_B["Save V3Violation<br/>with confidence_score<br/>+ verdict_reasoning"]
    VERDICT_B -- "False" --> SKIP_B["Skip record"]
    VERDICT_C -- "True" --> SAVE_C["Save V3Violation<br/>with confidence_score<br/>+ verdict_reasoning"]
    VERDICT_C -- "False" --> SKIP_C["Skip record"]

    style PATH_A fill:#064e3b,stroke:#10b981,color:#d1fae5
    style PATH_B fill:#1e1b4b,stroke:#818cf8,color:#e0e7ff
    style PATH_C fill:#4c1d95,stroke:#a78bfa,color:#ede9fe
```

---

## 4. Adversarial courtroom: the only parallel agent execution

Prosecutor and Defender run concurrently via `asyncio.gather`. The Chief Justice waits for both arguments before rendering a verdict.

```mermaid
sequenceDiagram
    participant S as Scanner
    participant P as Prosecutor
    participant D as Defender
    participant J as Chief Justice

    S->>S: Build context string:<br/>RULE RUBRIC + RECORD EVIDENCE

    Note over P,D: asyncio.gather — parallel execution
    par Prosecution builds case
        S->>P: "Argue why this record VIOLATES the rule"
        Note over P: Thinking budget: 8K tokens
        P->>P: Identifies incriminating data fields
        P-->>S: LegalArgument{points, evidence_citations}
    and Defense builds counterargument
        S->>D: "Argue why this record COMPLIES (find loopholes)"
        Note over D: Thinking budget: 8K tokens
        D->>D: Finds exceptions, mitigating context
        D-->>S: LegalArgument{points, evidence_citations}
    end

    Note over S,J: Sequential — Chief Justice weighs both sides
    S->>J: Prosecution argument (JSON)<br/>+ Defense argument (JSON)<br/>+ Original context
    Note over J: Thinking budget: 16K tokens<br/>Weighs evidence quality, not quantity
    J-->>S: Verdict{is_violation, confidence_score, reasoning}

    alt is_violation == true
        S->>S: Save V3Violation with confidence + reasoning
    else is_violation == false
        S->>S: Skip record
    end
```

---

## 5. Data contracts between agents

No agent calls another. The service layer moves typed Pydantic models between them. Every boundary is validated.

```mermaid
flowchart LR
    subgraph INGESTION["Ingestion phase"]
        direction TB
        LEX["Lexicon Agent"] -->|"GlobalOntology<br/>definitions: dict"| EXT["Extractor Agent"]
        EXT -->|"list of SymbolicRuleDraft<br/>logic_tree, target_table"| AST["AST Compiler"]
        AST -->|"SQL WHERE clause string"| VAL["output_validator"]
        VAL -->|"ModelRetry with postgres_error"| EXT
        VAL -->|"SymbolicRuleDraft<br/>with compiled_sql filled"| DB1[("V3Rule<br/>in database")]
    end

    subgraph SCAN["Scan phase"]
        direction TB
        SCANNER["Scanner"] -->|"dict record_data<br/>+ str rubric"| PROS["Prosecutor"]
        SCANNER -->|"dict record_data<br/>+ str rubric"| DEF["Defender"]
        PROS -->|"LegalArgument<br/>points, citations"| CJ["Chief Justice"]
        DEF -->|"LegalArgument<br/>points, citations"| CJ
        CJ -->|"Verdict<br/>is_violation, confidence, reasoning"| DB2[("V3Violation<br/>in database")]
    end

    DB1 -.->|"approved rules"| SCANNER

    style INGESTION fill:#0f172a,stroke:#3b82f6,color:#e2e8f0
    style SCAN fill:#0f172a,stroke:#ef4444,color:#e2e8f0
```

---

## 6. The reflexion loop in detail

The Extractor Agent's `@output_validator` is the only self-healing mechanism in the system. It turns Postgres error messages into correction prompts.

```mermaid
flowchart TD
    CLAUDE["Claude produces<br/>list of SymbolicRuleDraft"] --> PARSE["Parse logic_tree<br/>JSON string to LogicNode"]

    PARSE --> PARSE_OK{"Valid<br/>JSON?"}
    PARSE_OK -- "No" --> RETRY_JSON["ModelRetry with message:<br/>Invalid logic_tree JSON for rule X.<br/>Return logic_tree as valid JSON."]
    RETRY_JSON --> CLAUDE

    PARSE_OK -- "Yes" --> COMPILE["compile_ast_to_sql(logic_tree)<br/>pure Python, deterministic"]
    COMPILE --> BUILD["Build test SQL:<br/>SELECT id FROM target_table<br/>WHERE where_clause LIMIT 1"]
    BUILD --> EXPLAIN["EXPLAIN test_sql<br/>inside begin_nested()"]

    EXPLAIN --> PG_OK{"Postgres<br/>accepts?"}
    PG_OK -- "No" --> RETRY_SQL["ModelRetry with message:<br/>SQL validation failed for rule X.<br/>Postgres error: column emplyee_age<br/>does not exist.<br/>Fix subject_column values."]
    RETRY_SQL --> CLAUDE

    PG_OK -- "Yes" --> FILL["Fill compiled_sql field:<br/>SELECT * FROM {table}<br/>WHERE {where_clause}"]
    FILL --> DONE["Return validated rules"]

    style RETRY_JSON fill:#7f1d1d,stroke:#ef4444,color:#fecaca
    style RETRY_SQL fill:#7f1d1d,stroke:#ef4444,color:#fecaca
    style DONE fill:#064e3b,stroke:#10b981,color:#d1fae5
```

---

## 7. Agent registry

All seven agents, their configurations, and when they fire.

```mermaid
graph TD
    subgraph AGENTS["Agent registry — all Claude Sonnet 4.6"]
        direction TB

        A1["Lexicon Agent<br/>─────────────<br/>Thinking: enabled, 4K budget<br/>Max tokens: 8K<br/>Retries: default<br/>Runs: once per V3 ingestion<br/>File: ingestion.py inline<br/>Output: GlobalOntology"]

        A2["Compiler Agent<br/>─────────────<br/>Thinking: adaptive, high effort<br/>Retries: 3<br/>Runs: once per V1 ingestion<br/>File: agents/compiler.py<br/>Output: list of CompiledRule<br/>Factory: lru_cache"]

        A3["Extractor Agent<br/>─────────────<br/>Thinking: enabled, 10K budget<br/>Max tokens: 20K<br/>Retries: 4<br/>Runs: per chunk during V3 ingestion<br/>File: agents/extractor.py<br/>Output: list of SymbolicRuleDraft<br/>Factory: lru_cache<br/>Special: output_validator reflexion"]

        A4["Explainer Agent<br/>─────────────<br/>Thinking: adaptive, medium effort<br/>Retries: default<br/>Runs: post-V1-scan, capped at 25<br/>File: agents/explainer.py<br/>Output: str, 2-sentence explanation<br/>Factory: lru_cache"]

        A5["Prosecutor Agent<br/>─────────────<br/>Thinking: enabled, 8K budget<br/>Max tokens: 16K<br/>Runs: per candidate in V3 semantic scan<br/>File: agents/courtroom.py<br/>Output: LegalArgument<br/>Factory: lru_cache"]

        A6["Defender Agent<br/>─────────────<br/>Thinking: enabled, 8K budget<br/>Max tokens: 16K<br/>Runs: per candidate, parallel w/ Prosecutor<br/>File: agents/courtroom.py<br/>Output: LegalArgument<br/>Factory: lru_cache"]

        A7["Chief Justice Agent<br/>─────────────<br/>Thinking: enabled, 16K budget<br/>Max tokens: 32K<br/>Runs: per candidate, after both arguments<br/>File: agents/courtroom.py<br/>Output: Verdict<br/>Factory: lru_cache"]
    end

    style AGENTS fill:#0f172a,stroke:#475569,color:#e2e8f0
```

---

## 8. Token cost by phase

```mermaid
pie title Token spend distribution (per policy lifecycle)
    "Lexicon Agent (1 call)" : 1
    "Extractor Agent (N chunks × up to 4 retries)" : 8
    "Compiler Agent (V1 only, 1 call)" : 3
    "Explainer Agent (up to 25 calls)" : 4
    "Prosecutor (M candidates)" : 5
    "Defender (M candidates, parallel)" : 5
    "Chief Justice (M candidates)" : 7
```

Deterministic scanning costs zero tokens. The courtroom is the expensive part, and it only fires for rules containing `IS_VAGUE` conditions. The `semantic_candidate_limit_per_rule` setting caps how many records enter the courtroom per rule.

---

## 9. Audit trail chain

Every violation traces back to the original PDF, through every intermediate representation.

```mermaid
flowchart BT
    PDF["Policy PDF<br/> policies.markdown_text"]
    QUOTE["Source quote<br/>(v3_rules.source_quote)"]
    AST["Logic tree<br/>(v3_rules.logic_tree_json)"]
    SQL["Compiled SQL<br/>(v3_rules.compiled_sql)"]
    VERDICT["Courtroom verdict<br/>(v3_violations.verdict_reasoning)"]
    CONFIDENCE["Confidence score<br/>(v3_violations.confidence_score)"]
    VIOLATION["Violation record<br/> v3_violations.violation_data"]

    VIOLATION --> CONFIDENCE
    CONFIDENCE --> VERDICT
    VERDICT --> SQL
    SQL --> AST
    AST --> QUOTE
    QUOTE --> PDF
```

For V1 violations, the chain is shorter: `violation → rule.compiled_sql → rule.source_quote → policies.markdown_text → ai_explanation`.

---

## Design rationale (short form)

**Why not one agent that does everything?**
Different phases have different cost profiles. The compiler needs `high` effort and schema context. The explainer needs `medium` effort and violation data. The courtroom needs adversarial structure. Cramming them into one agent wastes tokens and produces worse results.

**Why the adversarial courtroom instead of a single "is this a violation?" call?**
Single-agent evaluation anchors on its first interpretation and produces overconfident scores. The Defender forces the system to consider reasonable doubt. The Chief Justice, having seen both sides, produces calibrated confidence rather than binary yes/no.

**Why IS_VAGUE compiles to 1=1?**
V1 skipped subjective clauses entirely. V3 compiles them to `1=1` (match all rows), producing a superset that the courtroom narrows. No policy clause goes unenforced.

**Why BM25 instead of embeddings?**
Embedding tabular business data (expenses, transactions) produces garbage similarity scores. "Is this gift lavish?" and `{amount: 50000, category: "entertainment"}` don't embed into useful proximity. Postgres-native `ts_rank` retrieves candidates. The courtroom handles semantic evaluation.

**Why the @output_validator reflexion loop?**
Claude sometimes generates ASTs referencing nonexistent columns. The loop runs `EXPLAIN` on the generated SQL, catches Postgres errors, and feeds the exact error message back. Claude sees "column 'emplyee_age' does not exist" and fixes it. SQL that survives EXPLAIN is guaranteed executable at scan time.
