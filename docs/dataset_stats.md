# Dataset Statistics — Adult Drug Prescribing Guidelines Corpus

**Inspection run:** 2026-01-31 21:39:17

---

## 1. Overview

This document summarizes the dataset collected for the Evidence-Bound Drug RAG system, based on the inspection performed on Day 2 using `scripts/01_inspect_dataset.py`.

### Global counts

- **Total files:** 20
- **Total PDFs:** 20
- **Deferred:** 2 (WHO documents, ~940 pages)


### By source

| Source | PDF Count | Avg Size (KB) | Total Size (KB) |
|--------|-----------|---------------|-----------------|
| FDA    | 12        | 748.6         | 8,983.6         |
| NICE   | 8         | 425.5         | 3,403.6         |

**Note:** 2 WHO PDFs (3,649.6 KB combined) deferred to Day 13+.


**Total corpus size:** ~16 MB across 22 PDFs.

---

## 2. Size distribution

### Global stats (all files)

- **Minimum:** 90.3 KB
- **Average:** 729.0 KB
- **Maximum:** 2,801.4 KB

### Per-source size stats

- **FDA:** min 118.0 KB, max 2,801.4 KB
- **NICE:** min 90.3 KB, max 1,590.0 KB
- **WHO:** min 904.9 KB, max 2,744.7 KB

**Observation:** WHO documents are significantly larger on average (1,824 KB vs ~400–750 KB for FDA/NICE), likely due to comprehensive multi-drug essential medicines lists.

---

## 3. Year distribution

Documents are distributed across timeframes as follows:

| Source | Pre-2015 | 2015–2019 | 2020–2024 | Post-2024 |
|--------|----------|-----------|-----------|-----------|
| FDA    | 0        | 1         | 3         | 8         |
| NICE   | 0        | 2         | 5         | 1         |
| WHO    | 0        | 0         | 2         | 0         |

### Key observations

- **18 of 22 PDFs (82%)** are from 2020 or later.
- **9 PDFs (41%)** are post-2024, reflecting very recent label updates.
- **3 PDFs (14%)** are from 2015–2019.
- **0 pre-2015 documents** in the corpus.

This aligns well with the Phase 0 timeframe policy (2015–2024 preferred, with newer documents taking precedence).

---

## 4. Document type classification

Based on filename keyword heuristics:

- **Drug-centric documents:** 15  
  (Labels, highlights, prescribing guidelines directly focused on specific drugs)

- **Condition-guideline documents:** 2  
  (Management/diagnosis guidelines that mention locked drugs in context, e.g., osteoarthritis, upper GI bleeding)

- **Other:** 5  
  (Extended-release variants, technical summaries, or documents not clearly matching the above patterns)

### Interpretation

- 68% of the corpus is explicitly drug-centric.
- 23% (5 docs) are classified as "other"; these may be extended-release formulations, combination labels, or technical reports.
- This is **descriptive, not prescriptive**; if retrieval pulls "other" documents for core drug questions, that represents a retrieval failure, not a dataset error.

---

## 5. Estimated table presence

Using a simple heuristic (filename contains the word "table"):

- **Total hits:** 1
- **By source:** FDA (1), NICE (0), WHO (0)

**Note:** This is an extremely conservative filename-based estimate. Most PDFs likely contain tables internally (especially FDA labels with dosing tables and WHO essential medicines lists), but this inspection does not parse PDF content. Day 3 (parsing phase) will provide more accurate table detection.

---

## 6. Contract compliance checks

### 6.1 Naming violations

**Count:** 0

All filenames follow the locked naming convention:
- `fda_{drug}_{doc_type}_{year}.pdf`
- `nice_{topic}_{doc_type}_{year}.pdf`
- `who_{document_name}_{year}.pdf`

### 6.2 Non-locked drugs detected

**Count:** 0

No drug names outside the locked set (atorvastatin, lisinopril, amoxicillin, ciprofloxacin, ibuprofen, paracetamol/acetaminophen, metformin, warfarin) were detected in filenames using conservative heuristics.

### 6.3 Out-of-scope documents

**Count:** 0

All files are PDFs located under `data/raw/{fda,nice,who}/`. No stray files, no non-PDF documents.

---

## 7. Known issues and notes for Day 3 (parsing phase)

### 7.1 Potential parsing challenges

While all documents passed naming and scope checks, the following may still present challenges during PDF parsing (Day 3):

- **Scanned images:** None explicitly detected, but manual inspection may reveal scanned sections within otherwise text-based PDFs.
- **Complex tables:** FDA labels and WHO lists are known to contain dense dosing tables and multi-column layouts that may not parse cleanly into markdown.
- **Multi-drug labels:** Some FDA PDFs cover combination drugs (e.g., `fda_lisinopril_and_hydrochlorothiazide_label_2021.pdf`), which may require careful metadata extraction.

### 7.2 Year distribution skew

- 8 FDA PDFs are post-2024, reflecting very recent updates.
- This is acceptable under Phase 0 policy (documents outside 2015–2024 are allowed if clearly tagged), but it should be noted in metadata to avoid confusion during evaluation.

### 7.3 "Other" document classification

- 5 PDFs are classified as "other" based on filename keywords.
- These are not errors; they represent extended-release variants, combination labels, or technical summaries.
- If retrieval later surfaces these documents for core drug questions, that will be analyzed as a retrieval precision issue, not a dataset problem.

---

## 8. Summary and readiness for Day 3

### Dataset quality

- **Naming compliance:** 100% (0 violations)
- **Scope compliance:** 100% (0 out-of-scope docs)
- **Drug coverage:** All 8 locked drugs have at least one source document
- **Authority coverage:** FDA (Tier 1), NICE (Tier 1), WHO (Tier 2) all represented
- **Timeframe alignment:** 82% from 2020+, 0% pre-2015

---

---

## 9. WHO Documents (Deferred)

Two WHO essential medicines PDFs (~940 pages combined) were initially collected
but deferred during Day 3 parsing due to LlamaParse free-tier page limits.

All 8 locked drugs (atorvastatin, lisinopril, amoxicillin, ciprofloxacin,
ibuprofen, paracetamol, metformin, warfarin) are fully covered by Tier 1
authorities (FDA and/or NICE).

WHO documents are Tier 2 by design and provide supplementary global context,
not primary prescribing rules. They will be reconsidered in Day 13+
(extensions and hardening) if they add measurable value.

**Files deferred:**
- `who_essential_medicines_2023.pdf` (2,744.7 KB)
- `who_selection_and_use_of_essential_medicine_2023.pdf` (904.9 KB)

**Location:** Moved to `data/deferred/who/` for auditability.

**Updated corpus for Day 3:**
- FDA: 12 PDFs
- NICE: 8 PDFs
- **Total: 20 PDFs**



### Next steps (Day 3: PDF Parsing)

Day 3 will focus on:

1. Using **LlamaParse** to extract markdown from all 22 PDFs.
2. Logging parse errors and failures to `data/failures/parsing_failures.json`.
3. Detecting tables and assessing preservation quality.
4. Producing `data/processed/parsed_docs.json` with `ParsedDocument` objects including authority, tier, year, and drug metadata.

The inspection script and this document establish **data reality** before any modeling or retrieval begins. This is the foundation for all downstream failure analysis.
