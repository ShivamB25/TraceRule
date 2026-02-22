# How TraceRule's agents process policy documents

Seven Claude agents, two pipelines, one goal: turn legal text into enforceable database queries. No agent talks to another directly. The service layer passes typed Pydantic schemas between them.

---

## 1. Full system overview

```mermaid
flowchart TD
    PDF["📄 Policy PDF upload"]

    subgraph TEXT_EXTRACT["Text extraction (CPU, ~200ms)"]
        PYMUPDF["pymupdf4llm.to_markdown()"]
    end

    subgraph SCHEMA["Database introspection"]
        INTRO["information_schema.columns → schema context string"]
    end

    PDF --> PYMUPDF
    PYMUPDF --> MARKDOWN["Markdown text"]
    MARKDOWN --> V1_PATH
    MARKDOWN --> V3_PATH

    subgraph V1_PATH["V1 Pipeline"]
        direction TB
        COMPILER["🤖 Compiler Agent\nClaude Sonnet 4.6\nadaptive thinking · high effort\n3 retries"]
        RULES_V1["Rule rows\nstatus=pending_review\ncompiled_sql + source_quote"]
        COMPILER --> RULES_V1
    end

    subgraph V3_PATH["V3 Pipeline"]
        direction TB
        LEXICON["🤖 Lexicon Agent\nClaude Sonnet 4.6\nthinking budget: 4K tokens\nreads first 12K chars"]
        ONTOLOGY["GlobalOntology\n{term → definition}"]
        CHUNKER["Chunker\n4000 chars · 500 overlap"]
        EXTRACTOR["🤖 Extractor Agent\nClaude Sonnet 4.6\nthinking budget: 10K tokens\n4 retries + @output_validator"]
        AST_COMP["AST Compiler\npure Python · no LLM\nLogicNode → SQL WHERE"]
        EXPLAIN["EXPLAIN sandbox\nbegin_nested() → rollback"]
        RETRY{"Postgres\nerror?"}
        MODEL_RETRY["ModelRetry\nfull stack trace\nback to Claude"]
        RULES_V3["V3Rule rows\nstatus=pending_review\nlogic_tree_json + compiled_sql"]

        LEXICON --> ONTOLOGY
        ONTOLOGY --> EXTRACTOR
        CHUNKER --> EXTRACTOR
        EXTRACTOR --> AST_COMP
        AST_COMP --> EXPLAIN
        EXPLAIN --> RETRY
        RETRY -- "Yes" --> MODEL_RETRY
        MODEL_RETRY --> EXTRACTOR
        RETRY -- "No (SQL valid)" --> RULES_V3
    end

    INTRO --> V1_PATH
    INTRO --> V3_PATH
    MARKDOWN --> CHUNKER

    RULES_V1 --> HITL["👤 Human review\nApprove / Reject"]
    RULES_V3 --> HITL

    HITL --> SCAN_V1["V1 Scanner\ndb.execute(compiled_sql)\n~2ms/rule · zero LLM"]
    HITL --> SCAN_V3["V3 Scanner\n3-path routing"]

    SCAN_V1 --> VIOLATIONS["Violations"]
    SCAN_V3 --> VIOLATIONS

    SCAN_V1 --> EXPLAINER["🤖 Explainer Agent\nadaptive · medium effort\ncapped at 25/scan"]
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
    I->>I: _extract_policy_text() → markdown

    Note over I,L: Phase 1: Build shared vocabulary
    I->>L: run_stream(first 12K chars)
    L-->>I: GlobalOntology{definitions}

    Note over I,P: Phase 2: Get DB column names
    I->>P: SELECT FROM information_schema.columns
    P-->>I: schema context string

    Note over I,C: Phase 3: Split for context windows
    I->>C: _chunk_policy_text(markdown, 4000, 500)
    C-->>I: list[str] chunks

    loop For each chunk
        Note over I,E: Phase 4: Extract deontic logic AST
        I->>E: run(chunk, deps={db, schema, ontology})
        E->>E: Claude produces list[SymbolicRuleDraft]

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
            E-->>I: list[SymbolicRuleDraft] with compiled_sql filled
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

    CHECK -- "False" --> PATH_A
    CHECK -- "True" --> HAS_SQL{"compiled_sql\nexists?"}

    HAS_SQL -- "Yes (mixed rule)" --> PATH_B
    HAS_SQL -- "No (pure vague)" --> PATH_C

    subgraph PATH_A["Path A: Pure deterministic"]
        direction TB
        EXEC_A["db.execute(compiled_sql)"]
        SAVE_A["Save V3Violation\nconfidence = 1.0\nreasoning = 'Deterministic SQL match'"]
        EXEC_A --> SAVE_A
    end

    subgraph PATH_B["Path B: SQL pre-filter + courtroom"]
        direction TB
        EXEC_B["db.execute(compiled_sql)\nIS_VAGUE → 1=1 gives superset"]
        FAIL_B{"SQL\nfailed?"}
        BM25_B["Fallback: BM25 text search\nts_rank + websearch_to_tsquery"]
        CANDIDATES_B["Candidate rows"]
        COURT_B["Adversarial Courtroom\n(per candidate)"]

        EXEC_B --> FAIL_B
        FAIL_B -- "Yes" --> BM25_B
        BM25_B --> CANDIDATES_B
        FAIL_B -- "No" --> CANDIDATES_B
        CANDIDATES_B --> COURT_B
    end

    subgraph PATH_C["Path C: BM25 + courtroom"]
        direction TB
        BM25_C["BM25 text search\non company_records table\nts_rank + websearch_to_tsquery"]
        CANDIDATES_C["Candidate rows"]
        COURT_C["Adversarial Courtroom\n(per candidate)"]

        BM25_C --> CANDIDATES_C
        CANDIDATES_C --> COURT_C
    end

    COURT_B --> VERDICT_B{"Verdict:\nis_violation?"}
    COURT_C --> VERDICT_C{"Verdict:\nis_violation?"}

    VERDICT_B -- "True" --> SAVE_B["Save V3Violation\nwith confidence_score\n+ verdict_reasoning"]
    VERDICT_B -- "False" --> SKIP_B["Skip record"]
    VERDICT_C -- "True" --> SAVE_C["Save V3Violation\nwith confidence_score\n+ verdict_reasoning"]
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
    participant P as 🔴 Prosecutor
    participant D as 🔵 Defender
    participant J as ⚖️ Chief Justice

    S->>S: Build context string:\nRULE RUBRIC + RECORD EVIDENCE

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
    S->>J: Prosecution argument (JSON)\n+ Defense argument (JSON)\n+ Original context
    Note over J: Thinking budget: 16K tokens\nWeighs evidence quality, not quantity
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
        LEX["Lexicon Agent"] -->|"GlobalOntology\n{definitions: dict}"| EXT["Extractor Agent"]
        EXT -->|"list[SymbolicRuleDraft]\n{logic_tree: str, target_table, ...}"| AST["AST Compiler"]
        AST -->|"str (SQL WHERE clause)"| VAL["@output_validator"]
        VAL -->|"ModelRetry(postgres_error)"| EXT
        VAL -->|"SymbolicRuleDraft\nwith compiled_sql filled"| DB1[("V3Rule\nin database")]
    end

    subgraph SCAN["Scan phase"]
        direction TB
        SCANNER["Scanner"] -->|"dict (record_data)\n+ str (rubric)"| PROS["Prosecutor"]
        SCANNER -->|"dict (record_data)\n+ str (rubric)"| DEF["Defender"]
        PROS -->|"LegalArgument\n{points, citations}"| CJ["Chief Justice"]
        DEF -->|"LegalArgument\n{points, citations}"| CJ
        CJ -->|"Verdict\n{is_violation, confidence, reasoning}"| DB2[("V3Violation\nin database")]
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
    CLAUDE["Claude produces\nlist[SymbolicRuleDraft]"] --> PARSE["Parse logic_tree\nJSON string → LogicNode"]

    PARSE --> PARSE_OK{"Valid\nJSON?"}
    PARSE_OK -- "No" --> RETRY_JSON["ModelRetry:\n'Invalid logic_tree JSON for rule X: error.\nReturn logic_tree as valid JSON.'"]
    RETRY_JSON --> CLAUDE

    PARSE_OK -- "Yes" --> COMPILE["compile_ast_to_sql(logic_tree)\npure Python, deterministic"]
    COMPILE --> BUILD["Build test SQL:\nSELECT id FROM {target_table}\nWHERE {where_clause} LIMIT 1"]
    BUILD --> EXPLAIN["EXPLAIN test_sql\ninside begin_nested()"]

    EXPLAIN --> PG_OK{"Postgres\naccepts?"}
    PG_OK -- "No" --> RETRY_SQL["ModelRetry:\n'SQL validation failed for rule X.\nPostgres error: column emplyee_age\ndoes not exist.\nFix subject_column values.'"]
    RETRY_SQL --> CLAUDE

    PG_OK -- "Yes" --> FILL["Fill compiled_sql field:\nSELECT * FROM {table}\nWHERE {where_clause}"]
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

        A1["🤖 Lexicon Agent\n─────────────\nThinking: enabled, 4K budget\nMax tokens: 8K\nRetries: default\nRuns: once per V3 ingestion\nFile: ingestion.py (inline)\nOutput: GlobalOntology"]

        A2["🤖 Compiler Agent\n─────────────\nThinking: adaptive, high effort\nRetries: 3\nRuns: once per V1 ingestion\nFile: agents/compiler.py\nOutput: list[CompiledRule]\nFactory: @lru_cache"]

        A3["🤖 Extractor Agent\n─────────────\nThinking: enabled, 10K budget\nMax tokens: 20K\nRetries: 4\nRuns: per chunk during V3 ingestion\nFile: agents/extractor.py\nOutput: list[SymbolicRuleDraft]\nFactory: @lru_cache\nSpecial: @output_validator reflexion"]

        A4["🤖 Explainer Agent\n─────────────\nThinking: adaptive, medium effort\nRetries: default\nRuns: post-V1-scan, capped at 25\nFile: agents/explainer.py\nOutput: str (2-sentence explanation)\nFactory: @lru_cache"]

        A5["🔴 Prosecutor Agent\n─────────────\nThinking: enabled, 8K budget\nMax tokens: 16K\nRuns: per candidate in V3 semantic scan\nFile: agents/courtroom.py\nOutput: LegalArgument\nFactory: @lru_cache"]

        A6["🔵 Defender Agent\n─────────────\nThinking: enabled, 8K budget\nMax tokens: 16K\nRuns: per candidate (parallel w/ Prosecutor)\nFile: agents/courtroom.py\nOutput: LegalArgument\nFactory: @lru_cache"]

        A7["⚖️ Chief Justice Agent\n─────────────\nThinking: enabled, 16K budget\nMax tokens: 32K\nRuns: per candidate (after both arguments)\nFile: agents/courtroom.py\nOutput: Verdict\nFactory: @lru_cache"]
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
    PDF["📄 Policy PDF\n(policies.markdown_text)"]
    QUOTE["Source quote\n(v3_rules.source_quote)"]
    AST["Logic tree\n(v3_rules.logic_tree_json)"]
    SQL["Compiled SQL\n(v3_rules.compiled_sql)"]
    VERDICT["Courtroom verdict\n(v3_violations.verdict_reasoning)"]
    CONFIDENCE["Confidence score\n(v3_violations.confidence_score)"]
    VIOLATION["🚨 Violation record\n(v3_violations.violation_data)"]

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
