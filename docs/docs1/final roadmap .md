
# **14-Day Enterprise RAG System: Execution Roadmap**

## Phase 0 — Epistemic Boundaries (Non-Negotiable)

Objective:
Define what the system is allowed to know, answer, and refuse before any modeling.

### 1) Domain Constraint
Chosen domain:
- Example: Clinical guidelines for adult diabetes management (single authority + timeframe).

Explicit exclusions:
- Patient-specific advice
- Cross-country guideline merging
- Informal sources (blogs, forums)

### 2) Authority Hierarchy
Source priority order:
1. Primary guideline documents
2. Official clinical manuals
3. Peer-reviewed review papers
4. Textbooks

If sources conflict:
- Higher authority overrides lower authority.
- Conflicts are logged, not merged.

### 3) Allowed Question Classes
Allowed:
- “What does document X state about Y?”
- “According to guideline X, what is recommended for Y?”

Disallowed:
- “What should I do?”
- “What is the best treatment?”
- Hypothetical clinical judgment questions.

### 4) Ground Truth Definition
An answer is considered correct if:
- It cites at least one authoritative chunk.
- The answer content is semantically aligned with that chunk.
- It does not merge contradictory sources.

### 5) Phase 0 Artifacts
- docs/domain_scope.md
- docs/authority_hierarchy.md
- docs/question_policy.md
- docs/ground_truth_definition.md

Rule:
If a question violates Phase 0 constraints, the system must refuse to answer.


## **Day 1: Foundation + Data Reality**

### **Learn**

- Project structure patterns (src/ vs scripts/ separation)
- Configuration management with type validation
- Data versioning vs code versioning


### **Build**

```
rag-medical/
├── src/{config,models,ingestion,retrieval,generation,evaluation,api}/
├── scripts/{01-06}_*.py
├── data/{raw,processed,evaluation,failures}/
├── docs/
├── docker/
└── tests/
```

- `requirements.txt` with pinned versions
- `.env.example` with all config keys
- `src/config/settings.py` using Pydantic
- `src/models/schemas.py` with dataclasses for ParsedDocument, Chunk, RetrievedChunk, GeneratedAnswer, EvaluationResult, FailureCase


### **Measure**

- Can you install all dependencies without errors?
- Does `python -c "from src.config.settings import settings"` work?


### **Artifacts**

- ✓ Complete directory structure
- ✓ `requirements.txt`
- ✓ `.env.example`
- ✓ `src/config/settings.py`
- ✓ `src/models/schemas.py`
- ✓ `.gitignore` excluding data/raw and .env

***

## **Day 2: Dataset Selection + Inspection**

### **Learn**

- Medical PDF characteristics (tables, complex layouts)
- Dataset constraints (bounded scope prevents scope creep)
- Difference between document count and retrieval units


### **Build**

- `scripts/01_inspect_dataset.py`
    - Counts total files, PDFs vs text
    - Calculates file size distribution
    - Estimates complexity (pages, file sizes)
    - Outputs `data/dataset_stats.json`


### **Measure**

- Total documents: N
- Average file size: X KB
- Estimated tables: Y (grep for "Table" keyword)
- Document type breakdown (PDF %, TXT %)


### **Artifacts**

- ✓ Chosen dataset downloaded to `data/raw/` (20-30 PDFs)
- ✓ `scripts/01_inspect_dataset.py`
- ✓ `data/dataset_stats.json`
- ✓ `docs/dataset_stats.md` with known issues ("3 PDFs are scanned images")

***

## **Day 3: PDF Parsing + Parse Failure Logging**

### **Learn**

- Why naive PDF extractors fail on tables
- LlamaParse markdown output preserves structure
- Parse errors are data, not exceptions to hide


### **Build**

- `src/ingestion/parser.py` with `DocumentParser` class
    - Uses LlamaParse with `result_type="markdown"`
    - Returns `ParsedDocument` with `parse_errors` list
    - Counts tables detected (heuristic: count `|` chars)
- `scripts/02_parse_documents.py`
    - Parses all PDFs in `data/raw/`
    - Saves to `data/processed/parsed_docs.json`
    - Logs failures to `data/failures/parsing_failures.json`


### **Measure**

- Parsed: X/N PDFs successfully
- Failed: Y PDFs (reasons logged)
- Tables preserved: Z% (manual inspection of 5 random docs)


### **Artifacts**

- ✓ `src/ingestion/parser.py`
- ✓ `scripts/02_parse_documents.py`
- ✓ `data/processed/parsed_docs.json`
- ✓ `data/failures/parsing_failures.json`
- ✓ `docs/parsing_analysis.md` documenting table collapse, scanned PDF failures, page header issues

***

## **Day 4: Semantic Chunking + Distribution Analysis**

### **Learn**

- Chunk size is the most critical RAG decision
- Semantic boundaries matter (don't split "500mg every 6 hours")
- Outlier detection (too small/large chunks indicate problems)


### **Build**

- `src/ingestion/chunker.py` with `SemanticChunker` class
    - Uses `RecursiveCharacterTextSplitter` from LangChain
    - Chunk size: 512 tokens, overlap: 50 tokens
    - Separators: `["\n\n", "\n", ". ", " ", ""]` (paragraph-first)
    - Returns `List[Chunk]` with token counts and metadata
- `scripts/03_chunk_and_analyze.py`
    - Chunks all parsed docs
    - Logs distribution: avg, min, max, P50, P95
    - Identifies outliers (<50 or >800 tokens)
    - Saves to `data/processed/chunks.json`
    - Prints 10 random sample chunks


### **Measure**

- Total chunks: N
- Avg tokens: X
- Min/Max tokens: Y/Z
- Outliers: K chunks outside 50-800 range
- Manual review: Are medical concepts intact?


### **Artifacts**

- ✓ `src/ingestion/chunker.py`
- ✓ `scripts/03_chunk_and_analyze.py`
- ✓ `data/processed/chunks.json`
- ✓ `docs/chunking_analysis.md` with concept splitting issues, table fragmentation cases, proposed overlap increase

***

## **Day 5: Dual Index Setup (Vector + BM25)**

### **Learn**

- Vector search fails on exact medical terms ("ibuprofen 800mg")
- BM25 fails on paraphrasing ("pain reliever" vs "analgesic")
- Both indexes use same chunks, different representations


### **Build**

- `src/retrieval/vector_store.py` with `VectorStore` class
    - ChromaDB persistent client
    - `sentence-transformers/all-MiniLM-L6-v2` embeddings
    - `add_chunks()` method with progress bar
    - `search()` returns `List[RetrievedChunk]` with cosine scores
- `src/retrieval/bm25.py` with `BM25Index` class
    - `rank-bm25` library
    - Tokenization: simple `text.lower().split()`
    - `search()` returns `List[RetrievedChunk]` with BM25 scores
    - `save()`/`load()` for persistence
- `scripts/04_build_indexes.py`
    - Builds both indexes from `chunks.json`
    - Saves BM25 to `data/processed/bm25_index.pkl`
    - ChromaDB auto-persists to `data/chromadb/`


### **Measure**

- Vector index: N chunks, 384D embeddings
- BM25 index: N chunks
- Index build time: X seconds


### **Artifacts**

- ✓ `src/retrieval/vector_store.py`
- ✓ `src/retrieval/bm25.py`
- ✓ `scripts/04_build_indexes.py`
- ✓ `data/processed/bm25_index.pkl`
- ✓ `data/chromadb/` populated

***

## **Day 6: Hybrid Search + Reciprocal Rank Fusion**

### **Learn**

- RRF combines incomparable scores (BM25 vs cosine) without normalization
- RRF rewards chunks appearing high in multiple retrievers
- Hybrid search is damage control, not magic


### **Build**

- `src/retrieval/hybrid.py` with `HybridRetriever` class
    - `reciprocal_rank_fusion()` method: `score = sum(1/(k+rank_i))`, k=60
    - `retrieve()` method:
        - Gets top-20 from vector
        - Gets top-20 from BM25
        - Fuses with RRF
        - Returns top-k final results
    - Logs contribution: "Top-5: 3 from vector, 4 from BM25"
- `scripts/05_test_retrieval.py`
    - Tests 5 queries:
        - Exact term ("ibuprofen dosage")
        - Symptom description ("chest pain and difficulty breathing")
        - Common medical query ("side effects of aspirin")
        - Medical terminology ("contraindications for warfarin")
        - Natural language ("How to treat fever in children?")
    - Compares vector, BM25, hybrid side-by-side
    - Prints top-3 chunks for each method


### **Measure**

- For exact term queries: BM25 rank 1 position?
- For paraphrased queries: Vector rank 1 position?
- Hybrid overlap: How many chunks appear in both retrievers?


### **Artifacts**

- ✓ `src/retrieval/hybrid.py`
- ✓ `scripts/05_test_retrieval.py`
- ✓ `docs/retrieval_comparison.md` with 5 query examples, winner analysis, failure cases

***

## **Day 7: API Boundary (No LLM Yet)**

### **Learn**

- System thinking: freeze interfaces before adding complexity
- Retrieval validation must happen before LLM generation
- API contracts enforce testability


### **Build**

- `src/api/main.py` with FastAPI
    - `POST /retrieve` endpoint:
        - Input: `{"query": str, "top_k": int}`
        - Output: `{"query": str, "chunks": List[dict]}`
    - `GET /health` endpoint
    - `GET /stats` endpoint (total chunks indexed)
    - `@app.on_event("startup")` loads indexes
- No `/ask` endpoint yet (no LLM generation)


### **Measure**

- `curl http://localhost:8000/health` returns 200
- `curl -X POST http://localhost:8000/retrieve -d '{"query":"ibuprofen","top_k":5}'` returns 5 chunks
- Response time: <500ms for retrieval


### **Artifacts**

- ✓ `src/api/main.py` (retrieval-only endpoints)
- ✓ API running on `uvicorn src.api.main:app --reload`
- ✓ Test script validating `/retrieve` endpoint

***

## **Day 8: LLM Prompt Engineering + Citation Extraction**

### **Learn**

- Citations are not automatic, must be engineered into prompt
- Few-shot examples teach refusal behavior ("I cannot answer...")
- Context window management: 5 chunks ~2500 tokens + prompt ~500 tokens = safe margin


### **Build**

- `src/generation/prompts.py` with `PromptTemplates` class
    - `build_system_prompt()`: Rules for faithfulness and citations
    - `build_user_prompt(query, chunks)`: Numbered context chunks
    - `build_few_shot_examples()`: 2 examples showing citations and refusal
- `src/generation/llm.py` with `LLMGenerator` class
    - OpenAI client wrapper
    - `generate_answer()` method:
        - Builds messages (system + user)
        - Counts input tokens
        - Calls OpenAI API with `temperature=0.0`, `max_tokens=500`
        - Extracts citations using regex `\[(\d+)\]`
        - Maps citations to chunk IDs
        - Calculates cost (input + output tokens × price)
        - Returns `GeneratedAnswer` with metadata


### **Measure**

- Token count for typical query: X input, Y output
- Cost per query: \$Z
- Citation extraction: Do `[^1]`, `[^2]` get parsed correctly?


### **Artifacts**

- ✓ `src/generation/prompts.py`
- ✓ `src/generation/llm.py`
- ✓ Tested on 3 manual queries, citations verified

***

## **Day 9: End-to-End RAG Pipeline + API Completion**

### **Learn**

- Pipeline sequence: retrieve → generate → track metadata
- Cost tracking prevents budget overruns during eval
- Generated answers include unused retrieved chunks (for eval)


### **Build**

- Update `src/api/main.py`:
    - Add `POST /ask` endpoint:
        - Input: `{"query": str, "top_k": int}`
        - Output: `{"query": str, "answer": str, "cited_chunks": List[dict], "cost_usd": float, "latency_ms": float}`
        - Process: `HybridRetriever.retrieve() → LLMGenerator.generate_answer()`
    - Add `GET /stats` with `total_cost_usd` field


### **Measure**

- End-to-end latency: retrieval + generation = X ms
- Cost per query: \$Y
- Test 5 queries: Do answers cite sources correctly?


### **Artifacts**

- ✓ `src/api/main.py` with complete `/ask` endpoint
- ✓ Tested 5 queries via curl
- ✓ Logged responses with citations and costs

***

## **Day 10: Synthetic Evaluation Set Creation**

### **Learn**

- Synthetic QA is proxy truth, not ground truth
- Evaluation set must cover: direct lookup, concept questions, multi-chunk questions
- Quality > quantity (50-80 good pairs > 200 bad pairs)


### **Build**

- `src/evaluation/synthetic.py` with `SyntheticQAGenerator` class
    - `generate_for_document(doc, num_questions=3)`: Uses GPT to generate QA pairs
    - Prompt instructs: "Questions must be answerable ONLY from this document"
    - Returns structured JSON: `{"id", "question", "expected_answer", "source_document"}`
- `scripts/04_generate_eval_set.py`
    - Generates 60-80 QA pairs across all documents
    - Saves to `data/evaluation/synthetic_qa.json`
- Manual review: Inspect 10 random pairs, remove/fix bad ones


### **Measure**

- Total QA pairs: N
- Documents covered: X/Y
- Questions per document: avg Z
- Manual fixes: K pairs edited or removed


### **Artifacts**

- ✓ `src/evaluation/synthetic.py`
- ✓ `scripts/04_generate_eval_set.py`
- ✓ `data/evaluation/synthetic_qa.json`
- ✓ `docs/evaluation_set.md` documenting types of questions, manual fixes

***

## **Day 11: RAGAS Integration + Metrics Run**

### **Learn**

- Faithfulness: Does answer align with retrieved context?
- Answer relevancy: Does answer address the question?
- Context precision: How many retrieved chunks are actually relevant?
- High faithfulness can coexist with bad answers


### **Build**

- `src/evaluation/ragas_eval.py` with `RAGASEvaluator` class
    - `_build_dataset(qa_pairs)`: For each QA:
        - Retrieve chunks
        - Generate answer
        - Build HF Dataset: `{"question", "answer", "contexts"}`
    - `evaluate(qa_pairs)`: Runs RAGAS metrics (faithfulness, answer_relevancy, context_precision)
- `scripts/05_run_evaluation.py`
    - Loads synthetic QA set
    - Initializes retriever + generator
    - Runs `RAGASEvaluator.evaluate()`
    - Saves results to `data/evaluation/ragas_results.json`


### **Measure**

- Global faithfulness: X
- Global answer relevancy: Y
- Global context precision: Z
- Evaluation cost: \$W
- Evaluation time: T minutes


### **Artifacts**

- ✓ `src/evaluation/ragas_eval.py`
- ✓ `scripts/05_run_evaluation.py`
- ✓ `data/evaluation/ragas_results.json`
- ✓ `docs/evaluation_results.md` with metric interpretation, good/bad case examples

***
## Baseline System Comparison (Mandatory)

Purpose:
Quantify how each retrieval strategy affects answer quality and hallucination.

Systems compared:
1) Vector-only retrieval
2) BM25-only retrieval
3) Hybrid retrieval (RRF)
4) Hybrid + reranking (optional extension)

Method:
For the same synthetic QA set, run RAGAS evaluation for each system.

Metrics recorded:
- Faithfulness
- Answer Relevancy
- Context Precision

Results Table:

| System | Faithfulness | Answer Relevancy | Context Precision |
|--------|------------|----------------|------------------|
| Vector-only | X | Y | Z |
| BM25-only | X | Y | Z |
| Hybrid (RRF) | X | Y | Z |
| Hybrid + Reranker | X | Y | Z |

Key Observations:
- Where vector search fails:
- Where BM25 fails:
- Where hybrid improves results:
- Tradeoffs observed:

Conclusion:
Retrieval strategy is the dominant factor in RAG system reliability, not the LLM.

## **Day 12: Failure Analysis (THE PROJECT)**

### **Learn**

- Failure categorization: retrieval failure, partial context hallucination, chunk boundary distortion, table collapse
- Diagnosis requires manual inspection, not just metrics
- Proposed fixes are more valuable than perfect systems


### **Build**

- Define failure categories in `docs/failure_modes.md`
- `scripts/06_analyze_failures.py`
    - Extracts all cases where `faithfulness < 0.7` from RAGAS results
    - Saves to `data/failures/raw_failures.json`
- Manual analysis:
    - For 15-20 failures:
        - Assign `failure_category`
        - Write `diagnosis` (2-3 sentences)
        - Write `proposed_fix` (1 line)
    - Save to `data/failures/failure_log.json`
- Create `docs/failure_analysis.md`:
    - Failure category distribution
    - 3-5 detailed case studies
    - Common patterns


### **Measure**

- Total failures: X (Y% of total)
- Retrieval failure: A%
- Partial context hallucination: B%
- Chunk boundary distortion: C%
- Table collapse: D%


### **Artifacts**

- ✓ `docs/failure_modes.md` (failure taxonomy)
- ✓ `scripts/06_analyze_failures.py`
- ✓ `data/failures/raw_failures.json`
- ✓ `data/failures/failure_log.json` (manually analyzed)
- ✓ `docs/failure_analysis.md` (most valuable document in repo)

***

## **Day 13: Dockerization + Reproducibility**

### **Learn**

- Dockerfile best practices (slim base, layer caching)
- docker-compose for multi-service orchestration
- Environment variables for secrets, not hardcoded


### **Build**

- `docker/Dockerfile`:
    - Base: `python:3.10-slim`
    - Copy requirements, install deps
    - Copy src/, data/processed/
    - CMD: `uvicorn src.api.main:app --host 0.0.0.0 --port 8000`
- `docker/docker-compose.yml`:
    - Service: `chromadb` (official image)
    - Service: `rag-api` (custom Dockerfile)
    - Environment: `OPENAI_API_KEY`, `LLAMA_CLOUD_API_KEY` from `.env`
    - Volumes: `../data:/app/data`
- `scripts/start_docker.sh`:
    - `docker-compose down && docker-compose up --build`


### **Measure**

- Docker build time: X minutes
- Startup time: Y seconds
- `curl http://localhost:8000/health` returns 200 inside Docker


### **Artifacts**

- ✓ `docker/Dockerfile`
- ✓ `docker/docker-compose.yml`
- ✓ `scripts/start_docker.sh`
- ✓ Tested: one-command startup works

***

## **Day 14: UI + Portfolio Packaging**

### **Learn**

- UI must expose uncertainty, not hide it
- README structure: problem → approach → metrics → failures → next steps
- Portfolio narrative: honest, measurable, systems-focused


### **Build**

- `src/ui/app.py` (Streamlit):
    - Input: query text, top_k slider
    - Output:
        - Answer
        - Metadata (cost, latency)
        - Expandable "Retrieved Evidence" section with chunk scores
    - Run: `streamlit run src/ui/app.py`
- Take 2-3 screenshots:
    - Correct answer with good evidence
    - Failure case (show honesty)
- `README.md` rewrite:
    - Title + one-liner
    - Problem statement (why PDF chatbots hallucinate)
    - Architecture diagram (text or image)
    - Key features (hybrid search, RAGAS eval, failure log)
    - Metrics table (faithfulness, answer relevancy, context precision, failures)
    - Failure modes section (2-3 examples each)
    - How to run (local + Docker)
    - What I'd do next (reranking, confidence refusal, fine-tune embeddings)
- `docs/portfolio_summary.md` (1-2 pages):
    - Problem, approach, tech stack, metrics, key learnings
    - 1 short "failure story" for interviews
- Minimal testing:
    - `tests/test_retrieval.py`: Vector search returns ≤ top_k results
    - `tests/test_api.py`: `/health` returns 200

## Project Philosophy

This is not a chatbot demo.

This project is an investigation into why RAG systems fail and how retrieval, chunking, and evaluation decisions shape hallucination.

Instead of optimizing prompts, the system focuses on:
- Evidence retrieval quality
- Quantifiable evaluation metrics
- Explicit failure analysis

The core objective is not to maximize accuracy, but to understand failure modes in real-world RAG pipelines.
## System-Level Insights Gained

After building and evaluating the system, the following conclusions emerged:

1) Retrieval quality dominates LLM performance.
2) Hybrid retrieval consistently outperformed single-method retrieval.
3) High faithfulness does not guarantee good answers.
4) Most hallucinations originated from retrieval and chunk boundary errors, not the LLM.
5) Failure analysis provided more actionable insights than raw metrics.

Example statement for interviews:

"I built a medical RAG system with hybrid retrieval and evaluated it using RAGAS. On synthetic QA benchmarks, hybrid retrieval improved faithfulness by X% compared to vector-only search. Most failures were retrieval-related rather than LLM hallucinations, which I verified through systematic failure analysis."


### **Measure**

- Can someone clone and run `docker-compose up` successfully?
- README clarity: Can you explain system in 3 minutes from README alone?


### **Artifacts**

- ✓ `src/ui/app.py`
- ✓ Screenshots (2-3)
- ✓ `README.md` (complete rewrite)
- ✓ `docs/portfolio_summary.md`
- ✓ `tests/test_retrieval.py`
- ✓ `tests/test_api.py`
- ✓ Architecture diagram (text or image)

***

## **Critical Sequencing Enforcement**

**Before Day 5:** No embeddings, no retrieval
**Before Day 8:** No LLM calls
**Before Day 10:** No evaluation
**Before Day 14:** No UI

If you're tempted to ask an LLM a question before Day 8, you're doing it wrong.

***

## Design Decision Log

This project intentionally records key system design decisions and their rationale.

### Chunk Size Selection
Decision: 512 tokens with 50-token overlap  
Reason:
- Smaller chunks (<256) lost medical context
- Larger chunks (>1024) reduced retrieval precision
Observed Tradeoff:
Context preservation vs retrieval granularity

### top_k Selection
Decision: top_k = 5 (default)
Reason:
- top_k < 3 caused missing evidence
- top_k > 10 increased noise and hallucination risk

### Hybrid Retrieval Choice
Decision: Reciprocal Rank Fusion (RRF)
Reason:
- BM25 and vector scores are not directly comparable
- RRF rewards agreement between retrievers

### No Reranking Initially
Decision: Reranking postponed until hybrid baseline stabilized
Reason:
- Needed to isolate retrieval errors before adding complexity

### Evaluation Strategy
Decision: Synthetic QA + RAGAS
Reason:
- No real ground truth available
- Need reproducible benchmarking

Summary:
Most system failures originated from retrieval and chunking decisions, not the LLM.


## **Final Interview Readiness**

By Day 14, you must confidently answer:

1. **3-minute flow:** Ingestion → Chunking → Hybrid Retrieval → LLM Answer → RAGAS Eval
2. **Metrics:** "On 80 synthetic questions, my system achieved 0.83 faithfulness and 0.79 answer relevancy."
3. **Failure story:** "For contraindications of warfarin, retrieval pulled dosage text instead of warnings. RAGAS flagged low faithfulness (0.43). I diagnosed it as retrieval failure and proposed increasing top_k and using synonyms."
4. **Design questions:**
    - Why hybrid retrieval? (Vector fails on exact terms, BM25 fails on paraphrasing)
    - Why 512-token chunks? (Balance between context preservation and retrieval precision)
    - Why no reranking yet? (Next step: cross-encoder reranking on top-20 hybrid results)

***

## **Success Criteria**

- **Repo:** Clean structure, no notebook mess, all code in `src/`
- **Docs:** 5 markdown files in `docs/` with parsing analysis, retrieval comparison, evaluation results, failure analysis, portfolio summary
- **Metrics:** RAGAS scores logged, failure log with 15+ analyzed cases
- **Reproducibility:** One-command Docker startup
- **Honesty:** Failure analysis more detailed than metrics dashboard

This roadmap produces a system that interviews trust, not hype.

