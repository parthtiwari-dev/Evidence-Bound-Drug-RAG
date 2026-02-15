# Day 1–2 Execution Summary — Foundation & Data Reality

**Project:** Evidence-Bound Drug RAG  
**Period:** January 31, 2026 (Phase 0 → Day 2 complete)  
**Status:** ✅ Foundation locked, dataset collected and inspected

---

## Executive Summary

Over Phase 0 through Day 2, we established a **production-grade foundation** for an enterprise RAG system focused on adult drug prescribing and interaction guidelines. Unlike typical RAG demos, this system is built on an explicit epistemic contract that defines what it can answer, what it must refuse, and how correctness is measured.

**What we built:**
- 6 Phase 0 contract documents defining domain, authorities, questions, ground truth, dataset, and refusals
- Complete project structure (`src/`, `scripts/`, `data/`, `docs/`, `docker/`, `tests/`)
- Type-safe configuration system using Pydantic
- 6 core dataclass schemas encoding authority/tier/year metadata
- 22 curated guideline PDFs from FDA, NICE/NHS/BNF, and WHO
- Dataset inspection script with contract compliance checks
- Full statistical analysis of the corpus

**What we did NOT build (by design):**
- No notebooks
- No LLM calls yet (Day 8+)
- No embeddings yet (Day 5+)
- No retrieval yet (Day 5+)
- No parsing yet (Day 3)

This is **systems engineering**, not rapid prototyping.

---

## Phase 0 — Epistemic Contract (Pre-Day 1)

### Objective

Define **what the system is allowed to know, answer, and refuse** before writing any code.

### What we locked

1. **Domain** (`docs/domain_scope.md`):
   - Adult drug prescribing & interactions only
   - 8 locked drugs: Atorvastatin, Lisinopril, Amoxicillin, Ciprofloxacin, Ibuprofen, Paracetamol, Metformin, Warfarin
   - Adults only (≥18 years)
   - US (FDA), UK (NICE/NHS/BNF), Global (WHO) authorities
   - Timeframe: 2015–2024 preferred, older docs tagged

2. **Authority Hierarchy** (`docs/authority_hierarchy.md`):
   - Tier 1: FDA, NICE/NHS/BNF (primary regulators)
   - Tier 2: WHO (global guidance)
   - Tier 3: Disabled (no secondary sources)
   - Conflict rule: Higher tier overrides lower; conflicts logged, never merged

3. **Question Policy** (`docs/question_policy.md`):
   - Allowed: Document-grounded queries about dosing, interactions, contraindications, warnings
   - Disallowed: Personalized advice, diagnostics, best treatment, non-locked drugs, pediatric use

4. **Ground Truth Definition** (`docs/ground_truth_definition.md`):
   - Correct = cited, semantically aligned, authority-respecting, scope-compliant
   - Refusals are correct behavior when questions violate policy
   - Incorrect = hallucination/retrieval failure

5. **Dataset Blueprint** (`docs/dataset_blueprint.md`):
   - 22–30 PDFs: 10–12 NICE, 8–12 FDA, 1–2 WHO
   - Folder structure: `data/raw/{nice,fda,who}/`
   - Naming: `{authority}_{drug/topic}_{doc_type}_{year}.pdf`

6. **Refusal Policy** (`docs/refusal_policy.md`):
   - When to refuse: domain/population/authority/safety violations
   - How to refuse: brief, factual, scoped, non-moralizing
   - Templates for common refusal scenarios

### Why Phase 0 matters

- Prevents scope creep
- Makes retrieval/generation auditable
- Gives evaluation a clear notion of correctness
- Distinguishes this from toy chatbot demos

**Artifact:** `docs/phase0_readme.md`

---

## Day 1 — Foundation + Data Reality

### Objective

Create a production-grade project skeleton with type-safe config and schema definitions.

### Task 1: Repository naming

**Decision:** `evidence-bound-drug-rag`

**Rationale:**
- "evidence-bound" signals answers constrained by documented evidence
- "drug" clarifies the domain (not generic RAG)
- "rag" keeps it technically clear for engineers

### Task 2: Directory structure

Created complete layout:

```
evidence-bound-drug-rag/
├── src/
│   ├── config/
│   ├── models/
│   ├── ingestion/
│   ├── retrieval/
│   ├── generation/
│   ├── evaluation/
│   └── api/
├── scripts/
├── data/
│   ├── raw/{nice,fda,who}/
│   ├── processed/
│   ├── evaluation/
│   └── failures/
├── docs/
├── docker/
├── tests/
├── requirements.txt
├── .env.example
└── .gitignore
```

**Key design choice:** `src/` for library code, `scripts/` for entrypoints (clean separation).

### Task 3: Virtual environment setup

- Created `.venv` using Python 3.10+
- Activated in PowerShell: `\.\.venv\Scripts\Activate.ps1`

### Task 4: Dependencies planning

Initial `requirements.txt`:
```
pydantic
pydantic-settings
python-dotenv
```

**Issue encountered:** Pydantic v2 moved `BaseSettings` to separate package.

**Resolution:** Added `pydantic-settings` to requirements.

### Task 5: Configuration system

**File:** `src/config/settings.py`

**Design:**
- Uses `pydantic-settings.BaseSettings` for type validation
- Loads from `.env` (not committed)
- Fields:
  - Environment: `app_env`, `log_level`
  - Paths: `data_dir`, `chroma_db_dir`, `docs_dir`
  - API: `api_host`, `api_port`
  - Services: `openai_api_key`, `llama_cloud_api_key`

**Validation:** `python -c "from src.config.settings import settings"` works ✅

### Task 6: Core schemas

**File:** `src/models/schemas.py`

**Dataclasses created:**
1. `ParsedDocument` – authority, tier, year, text, parse_errors
2. `Chunk` – document_id, text, token_count, section, authority metadata
3. `RetrievedChunk` – chunk_id, score, rank, retriever_type, authority metadata
4. `GeneratedAnswer` – query, answer_text, cited_chunk_ids, is_refusal, authorities_used, cost
5. `EvaluationResult` – question_id, system_variant, faithfulness, answer_relevancy, context_precision
6. `FailureCase` – question_id, failure_category, diagnosis, proposed_fix

**Key design:** All schemas carry `authority_family`, `tier`, `year`, `drug_names` to enforce Phase 0 rules.

### Task 7: Environment + gitignore

**`.env.example`:**
```
APP_ENV=dev
DATA_DIR=./data
CHROMA_DB_DIR=./data/chromadb
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
OPENAI_API_KEY=
LLAMA_CLOUD_API_KEY=
```

**`.gitignore`:**
- `.env` (secrets)
- `data/raw/` (licensed PDFs)
- `__pycache__/`, `.pytest_cache/`

### Day 1 artifacts

✅ Complete directory structure  
✅ `requirements.txt`  
✅ `.env.example`  
✅ `src/config/settings.py` (verified working)  
✅ `src/models/schemas.py`  
✅ `.gitignore`

---

## Day 2 — Dataset Selection + Inspection

### Objective

Physically collect guideline PDFs matching Phase 0 blueprint, then run inspection script to understand counts, sizes, and contract compliance.

### Task 1: Manual PDF collection

**Target:** 22–30 PDFs across FDA, NICE/NHS/BNF, WHO

**Process:**
- Searched Google: `site:nice.org.uk {drug} guideline pdf`, `{drug} FDA label pdf`, etc.
- Downloaded from official sources:
  - FDA: `accessdata.fda.gov`, DailyMed
  - NICE: `nice.org.uk`, NHS websites
  - WHO: `who.int` essential medicines lists
- Named consistently: `{authority}_{drug/topic}_{doc_type}_{year}.pdf`

**Initial collection issues:**
- Some NICE filenames were non-standard (e.g., `NG136_Visual_summary_20231019.pdf`)
- Cleaned up to match blueprint where possible
- Removed mixed/duplicate files

**Final collection:**
- FDA: 12 PDFs
- NICE: 8 PDFs
- WHO: 2 PDFs
- **Total: 22 PDFs**

### Task 2: Dataset blueprint update

Updated `docs/dataset_blueprint.md` with:
- Actual counts per source
- List of all collected filenames
- Note on naming deviations for later cleanup

### Task 3: Inspection script design

**Goal:** Compute statistics without parsing PDF content (filename + filesystem only).

**JSON schema locked:**
```json
{
  "total_files": int,
  "total_pdfs": int,
  "by_source": {
    "fda|nice|who": {
      "file_count", "pdf_count", "sizes",
      "year_distribution": {"pre_2015", "2015_2019", "2020_2024", "post_2024"}
    }
  },
  "size_stats": {"min_kb", "max_kb", "avg_kb"},
  "estimated_tables": {"total_hits", "by_source": {...}},
  "document_types": {"drug_centric", "condition_guideline", "other"},
  "contract_checks": {
    "non_locked_drugs_detected",
    "naming_violations",
    "out_of_scope_docs"
  }
}
```

**Why this schema:**
- `year_distribution` ties to Phase 0 timeframe policy
- `document_types` helps understand corpus balance
- `contract_checks` surfaces naming/scope violations early (data reality mindset)

### Task 4: Script implementation

**File:** `scripts/01_inspect_dataset.py`

**Capabilities:**
1. Walk `data/raw/{fda,nice,who}/` recursively
2. Extract year from filename using regex `\d{4}`
3. Bucket years into pre-2015, 2015–2019, 2020–2024, post-2024
4. Classify documents via filename keywords (drug-centric vs condition-guideline vs other)
5. Check naming violations (spaces, missing year, missing prefix)
6. Detect non-locked drug names (conservative heuristic)
7. Count files outside expected folders
8. Output `data/dataset_stats.json` + print summary

**Bug encountered:** `estimated_tables.by_source` schema violation

**Issue:** Script wrote `stats["estimated_tables"][source] = 0` instead of `stats["estimated_tables"]["by_source"][source] = 0`, breaking nested structure.

**Fix:** Two lines changed:
- Line 90: Initialize `stats["estimated_tables"]["by_source"][source] = 0`
- Line 153: Increment `stats["estimated_tables"]["by_source"][source] += 1`

**Resolution:** Re-ran script; JSON now schema-compliant ✅

### Task 5: Results analysis

**Final stats:**
```
Total files: 22
Total PDFs: 22
FDA: 12 PDFs, avg 748.6 KB
NICE: 8 PDFs, avg 425.5 KB
WHO: 2 PDFs, avg 1824.8 KB

Year distribution:
- Pre-2015: 0
- 2015–2019: 3
- 2020–2024: 10
- Post-2024: 9

Document types:
- Drug-centric: 15
- Condition-guideline: 2
- Other: 5

Contract checks:
- Naming violations: 0
- Non-locked drugs: 0
- Out-of-scope docs: 0
```

**Key observations:**
- 82% of corpus from 2020+ (aligned with Phase 0 preference)
- 41% post-2024 (very recent; acceptable if tagged)
- 0 pre-2015 docs
- 100% naming compliance
- 68% drug-centric docs; 23% "other" (extended-release, combination labels, technical summaries)

**Design decision:** Accepted 5 "other" docs as descriptive reality, not an error. If retrieval later pulls "other" docs for core drug questions, that's a retrieval failure, not a dataset problem.

### Task 6: Documentation

**File:** `docs/dataset_stats.md`

**Sections:**
1. Overview (counts, size distribution)
2. Year distribution analysis
3. Document type classification
4. Contract compliance checks
5. Known issues for Day 3 (potential parsing challenges)
6. Summary and readiness statement

### Day 2 artifacts

✅ 22 PDFs in `data/raw/{fda,nice,who}/`  
✅ `scripts/01_inspect_dataset.py`  
✅ `data/dataset_stats.json`  
✅ `docs/dataset_stats.md`

---

## What Worked

### Phase 0
- Explicit epistemic boundaries forced us to think like system designers, not prompt engineers
- 6-document contract is **readable in 5 minutes** and **enforceable in code**
- No ambiguity about what "correct" means

### Day 1
- Clean project structure (no notebook mess) from day one
- Type-safe config via Pydantic caught errors early
- Dataclass schemas encode Phase 0 metadata (authority, tier, year) natively

### Day 2
- Manual curation (not web scraping) ensured high-quality official sources
- Inspection-before-parsing philosophy surfaced issues early (naming, year distribution)
- Contract compliance checks (0 violations) validate that Phase 0 rules are enforceable

---

## What Didn't Work (And How We Fixed It)

### Issue 1: Pydantic v2 breaking change
**Problem:** `BaseSettings` moved to `pydantic-settings` package in Pydantic v2  
**Symptom:** `ImportError` when running `from src.config.settings import settings`  
**Fix:** Added `pydantic-settings` to requirements, updated import  
**Lesson:** Always check library migration guides for major version bumps

### Issue 2: Inconsistent NICE filenames
**Problem:** Some NICE PDFs had non-standard names (e.g., `RightCare-Pneumonia-toolkit.pdf`)  
**Fix:** Manually renamed to match `nice_{topic}_{doc_type}_{year}.pdf` pattern  
**Lesson:** Manual curation requires manual cleanup; inspection scripts catch violations

### Issue 3: `estimated_tables.by_source` schema bug
**Problem:** Script wrote `stats["estimated_tables"][source]` instead of `stats["estimated_tables"]["by_source"][source]`, breaking nested JSON structure  
**Symptom:** Output JSON had flat keys instead of nested `by_source` object  
**Fix:** Changed two lines (initialization + increment) to use correct nested path  
**Lesson:** Lock schema first, then implement; verify output matches schema exactly

### Issue 4: Post-2024 year skew
**Problem:** 9 of 22 PDFs (41%) are post-2024, outside Phase 0 "preferred" range  
**Decision:** Accepted as valid; Phase 0 says pre-2015 and post-2024 are allowed if tagged  
**Rationale:** Recent FDA label updates are higher quality than older docs; tier + year metadata makes this explicit  
**Lesson:** "Preferred" ≠ "required"; data reality > arbitrary constraints

---

## Design Decisions Log

### Decision 1: Repo name
**Choice:** `evidence-bound-drug-rag`  
**Rationale:** "Evidence-bound" conveys the Phase 0 philosophy; distinguishes from generic chatbots

### Decision 2: Dataset size
**Choice:** 22 PDFs (not forcing to 30)  
**Rationale:** Quality > quantity; 22 official docs with 100% naming compliance > 30 with mixed quality

### Decision 3: Year distribution acceptance
**Choice:** Allow post-2024 docs (9 PDFs)  
**Rationale:** Recent FDA labels are more accurate; tagging via `year` metadata maintains auditability

### Decision 4: "Other" document type classification
**Choice:** Keep 5 "other" docs in corpus  
**Rationale:** Extended-release variants and combination labels are still official sources; if retrieval mis-uses them, that's a retrieval failure to analyze, not a dataset error

### Decision 5: Inspection scope
**Choice:** Filename + filesystem only (no PDF parsing)  
**Rationale:** Day 2 is about **data reality**, not parsing complexity; parsing comes on Day 3 with LlamaParse

### Decision 6: Contract checks as counts, not enforcement
**Choice:** Log violations as counts, don't reject files  
**Rationale:** Inspection is descriptive; actual enforcement happens during ingestion (Day 3+)

---

## Architecture Snapshot (End of Day 2)

```
┌─────────────────────────────────────────────────────────┐
│ Phase 0 Epistemic Contract (6 markdown docs)           │
│ - domain_scope.md                                       │
│ - authority_hierarchy.md                                │
│ - question_policy.md                                    │
│ - ground_truth_definition.md                            │
│ - dataset_blueprint.md                                  │
│ - refusal_policy.md                                     │
└─────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────┐
│ Day 1: Foundation                                       │
│ - Project structure (src/, scripts/, data/, docs/)     │
│ - src/config/settings.py (Pydantic BaseSettings)       │
│ - src/models/schemas.py (6 dataclasses)                │
│ - .env.example, .gitignore, requirements.txt           │
└─────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────┐
│ Day 2: Dataset + Inspection                            │
│ - 22 curated PDFs in data/raw/{fda,nice,who}/          │
│ - scripts/01_inspect_dataset.py                        │
│ - data/dataset_stats.json (schema-compliant)           │
│ - docs/dataset_stats.md (human summary)                │
└─────────────────────────────────────────────────────────┘
```

**Status:** ✅ Foundation locked  
**Next:** Day 3 — PDF Parsing + Parse Failure Logging

---

## What's Next (Day 3 Preview)

### Objective
Parse all 22 PDFs into markdown using LlamaParse; log failures and table preservation quality.

### Key tasks
1. Implement `src/ingestion/parser.py` with `DocumentParser` class
2. Use LlamaParse API with `result_type="markdown"`
3. Extract metadata from filenames (authority, tier, year, drug)
4. Count tables (heuristic: count `|` chars in markdown)
5. Create `scripts/02_parse_documents.py` to batch-parse all PDFs
6. Output `data/processed/parsed_docs.json` (list of `ParsedDocument` objects)
7. Log failures to `data/failures/parsing_failures.json`
8. Write `docs/parsing_analysis.md` documenting table collapse, scanned PDF issues, page header problems

### Critical sequencing
**Before Day 5:** No embeddings, no retrieval  
**Before Day 8:** No LLM calls  
This is by design: isolate ingestion errors before adding retrieval complexity.

---

## Metrics Summary

| Metric | Value |
|--------|-------|
| Phase 0 docs created | 6 |
| Phase 0 decisions locked | ~40 |
| Day 1 files created | 7 |
| Day 1 dataclasses defined | 6 |
| Day 2 PDFs collected | 22 |
| Naming compliance | 100% |
| Contract violations | 0 |
| Bugs encountered | 3 |
| Bugs fixed | 3 |
| Lines of code written | ~400 |
| Time to first working inspection | <2 hours |

---

## Lessons for Interviews

### 1. Phase 0 as competitive advantage
**Statement:** "Before writing any code, I locked the system's epistemic boundaries in 6 markdown documents: domain, authorities, question policy, ground truth, dataset, and refusals. This made later retrieval and evaluation auditable."

**Why it matters:** Shows systems thinking, not just coding.

### 2. Data reality over toy datasets
**Statement:** "I manually curated 22 official guideline PDFs from FDA, NICE, and WHO, then ran a contract compliance inspection that found 0 naming violations. This dataset inspection revealed that 41% of docs are post-2024, which I accepted as valid under my timeframe policy rather than forcing artificial constraints."

**Why it matters:** Shows you understand real-world data messiness and make explicit design choices.

### 3. Failure logging from day one
**Statement:** "My inspection script doesn't just count files; it checks naming violations, non-locked drugs, and out-of-scope documents. Even though I had 0 violations, the infrastructure to log failures is already in place before any LLM or retrieval is added."

**Why it matters:** Shows you think about observability and debugging, not just happy paths.

### 4. Schema-first engineering
**Statement:** "I locked the JSON schema for `dataset_stats.json` before writing the inspection script. When I discovered a bug where `estimated_tables.by_source` was malformed, I fixed it immediately to maintain schema compliance. This discipline prevents downstream parsing errors."

**Why it matters:** Shows you care about contracts and interfaces, not just "working code."

---

## Success Criteria Check

From the roadmap:

- ✅ **Repo:** Clean structure, no notebook mess, all code in `src/`
- ✅ **Docs:** Phase 0 + Day 2 = 8 markdown files with explicit decisions
- ⏳ **Metrics:** Not yet (Day 10+)
- ⏳ **Reproducibility:** Not yet (Day 13)
- ✅ **Honesty:** `docs/dataset_stats.md` documents "other" doc types and year skew openly

**Phase 0 + Day 1–2 status:** Foundation complete, dataset ready for parsing.

---

## Appendix: File Tree (End of Day 2)

```
evidence-bound-drug-rag/
├── .venv/                              # Virtual environment (not committed)
├── data/
│   ├── raw/
│   │   ├── fda/                        # 12 PDFs
│   │   ├── nice/                       # 8 PDFs
│   │   └── who/                       # 2 PDFs
│   ├── processed/                      # (empty, for Day 3+)
│   ├── evaluation/                     # (empty, for Day 10+)
│   ├── failures/                       # (empty, for Day 3+)
│   └── dataset_stats.json              # ✅ Day 2 artifact
├── docs/
│   ├── domain_scope.md                 # ✅ Phase 0
│   ├── authority_hierarchy.md          # ✅ Phase 0
│   ├── question_policy.md              # ✅ Phase 0
│   ├── ground_truth_definition.md      # ✅ Phase 0
│   ├── dataset_blueprint.md            # ✅ Phase 0 + Day 2 updates
│   ├── refusal_policy.md               # ✅ Phase 0
│   ├── phase0_readme.md                # ✅ Phase 0 summary
│   └── dataset_stats.md                # ✅ Day 2 artifact
├── scripts/
│   └── 01_inspect_dataset.py           # ✅ Day 2 artifact
├── src/
│   ├── config/
│   │   └── settings.py                 # ✅ Day 1 artifact
│   ├── models/
│   │   └── schemas.py                  # ✅ Day 1 artifact
│   ├── ingestion/                      # (empty, for Day 3)
│   ├── retrieval/                      # (empty, for Day 5+)
│   ├── generation/                     # (empty, for Day 8+)
│   ├── evaluation/                     # (empty, for Day 10+)
│   └── api/                            # (empty, for Day 7+)
├── docker/                             # (empty, for Day 13)
├── tests/                              # (empty, for Day 14)
├── requirements.txt                    # ✅ Day 1 artifact
├── .env.example                        # ✅ Day 1 artifact
└── .gitignore                          # ✅ Day 1 artifact
```

**Total artifacts:** 16 files created, 22 PDFs collected, 0 code executed yet (inspection only).

---

**End of Day 1–2 Summary**  
**Next session:** Day 3 — PDF Parsing + Parse Failure Logging  
**Status:** Ready to proceed ✅

