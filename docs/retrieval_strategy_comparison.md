# Retrieval Strategy Comparison & Recommendations
**Evidence-Bound Drug RAG System - Day 5 Analysis**  
**Generated**: February 1, 2026  
**Test Dataset**: 5 clean, well-formed queries across 5 drugs

---

## Executive Summary

Vector retrieval achieved **100% accuracy** on our Day 5 test queries, while hybrid achieved **64%** and BM25 achieved **40%**. However, these results are based on **only 5 clean, well-formed test queries** — insufficient to make definitive conclusions about production retrieval strategy[file:40].

### Performance Metrics (Day 5 Tests)

| Retriever | Accuracy | Avg Latency | Top-5 Precision | Best For |
|-----------|----------|-------------|----------------|----------|
| **Vector** | 100% (5/5) | 33.4ms | 100% | Semantic queries, clean input |
| **BM25** | 40% (2/5) | 3.0ms | 40% | Exact keyword matching (when working) |
| **Hybrid** | 64% (3.2/5) | 24.5ms | 64% | Mixed queries (needs fixing) |

### Key Decision for Phase 0

**Recommendation**: Use **vector-only** for Phase 0 API `/retrieve` endpoint.

**Rationale**:
- ✅ Proven 100% accuracy on clean test queries
- ✅ Fast enough (33ms acceptable for PoC)
- ✅ Simple implementation (already working)
- ✅ Eliminates BM25 contamination risk

**Critical Caveat**: Don't dismiss hybrid based on limited testing. Keep code intact for Phase 1 evaluation on diverse query types[file:36].

---

## Why Vector Won (On Our Limited Tests)

### Test Query Characteristics

All 5 Day 5 queries were **textbook examples** that favor semantic search:

1. **"What are the side effects of warfarin?"** — Perfect grammar, medical terminology
2. **"What is the recommended dosage of atorvastatin?"** — Formal question structure
3. **"What are the contraindications for amoxicillin?"** — Technical medical term
4. **"How does metformin work?"** — Clear, simple mechanism question
5. **"What drugs interact with lisinopril?"** — Well-structured interaction query

**Problem**: These queries don't represent **real-world user input diversity**[file:36].

### Vector Search Strengths (Observed)

✅ **Semantic understanding**: Maps "side effects" → relevant sections across documents  
✅ **Consistent scoring**: Score range [0.54-0.59] shows stable relevance judgments  
✅ **Drug-specific**: All top-10 results matched query drug (warfarin, atorvastatin, etc.)  
✅ **Authority-aware**: Ranked FDA Tier 1 documents highest  
✅ **Recency-weighted**: Prioritized 2025-2026 documents over older versions

**Latency breakdown**:
- Fastest: 16.92ms (Query 4: "How does metformin work?")
- Slowest: 85.11ms (Query 1: "What are side effects of warfarin?")
- Average: 33.4ms (acceptable for Phase 0)

---

## BM25's Critical Failure Pattern

### Failure Case Analysis

**Query 1: "What are the side effects of warfarin?"**

❌ **Rank 1 Result** (Score: 1.0):
- Chunk: `fda_ciprofloxacin_extended_release_2025_chunk_0048`
- Drug: **ciprofloxacin** (WRONG DRUG!)
- Why it matched: Contains "side effects" keyword with high TF-IDF
- Text preview: "If you miss a dose of ciprofloxacin extended-release tablets..."

❌ **Rank 2 Result** (Score: 0.9161):
- Chunk: `fda_metformin_highlights_2026_chunk_0032`  
- Drug: **metformin** (WRONG DRUG!)
- Why it matched: Title "Common side effects of metformin hydrochloride tablets"

✅ **Rank 3 Result** (Score: 0.9028):
- Chunk: `fda_warfarin_label_2025_chunk_0049`  
- Drug: **warfarin** (CORRECT, but rank 3!)

**Root Cause**: Generic medical keywords ("side effects", "dosage", "contraindications") appear in **every drug's documentation**. BM25 cannot distinguish drug context without pre-filtering[file:36].

---

**Query 3: "What are the contraindications for amoxicillin?"**

❌ **Rank 1 Result** (Score: 1.0):
- Chunk: `nice_osteoarthritis_management_ng226_2022_chunk_0013`
- Drug: **none** (Osteoarthritis guideline, completely unrelated!)
- Why it matched: Contains "contraindications" keyword from research section

**Query 5: "What drugs interact with lisinopril?"**

❌ **Rank 1 Result** (Score: 1.0):
- Chunk: `fda_warfarin_highlights_2022_chunk_0019`
- Drug: **warfarin** (WRONG DRUG!)
- Text: "# 7 DRUG INTERACTIONS" (matched "drug" + "interact" keywords)

### BM25 Success Case

**Query 4: "How does metformin work?"**

✅ **BM25 performed well** on this query:
- Rank 1: Correctly returned metformin mechanism document
- Rank 2: Correctly returned metformin pharmacokinetics
- Reason: "How does X work" is drug-specific enough that "metformin" dominates scoring

**Lesson**: BM25 works when drug name is weighted heavily in query. Fails on generic questions like "What are side effects?"

---

## Hybrid Contamination Problem

### Why Hybrid Failed (64% vs Vector's 100%)

**Query 1 Hybrid Results**:
- ✅ Rank 1: warfarin (score: 1.0) — **Correct** (from vector)
- ❌ Rank 2: **ciprofloxacin** (score: 1.0) — **CONTAMINATION** (from BM25)
- ❌ Rank 3: **metformin** (score: 0.96) — **CONTAMINATION** (from BM25)

**Technical cause**:
1. BM25 false positives have **perfect scores (1.0)**
2. Even at low weight (20%), they survive RRF merging:
   - `0.8 × (vector 0.58) + 0.2 × (BM25 1.0) = 0.664`
   - Still high enough to stay in top-5 results
3. Weight tuning ineffective: All tested weights (50/50, 60/40, 70/30, 80/20) produced **identical 72% accuracy**[file:36]

**Conclusion**: Weight tuning cannot fix architectural problem. Need drug-aware pre-filtering before ranking.

---

## When Hybrid Will Matter (Untested Scenarios)

### Real-World Query Types We Haven't Evaluated

Our 5 test queries were **clean and well-formed**. Real users write **messy queries**:

#### 1. **Typos & Spelling Errors**
```
User query: "warafin side efects"
```
- **Vector**: May struggle (embedding model not trained on typos)
- **BM25**: Fuzzy matching might catch "warafin" ≈ "warfarin"
- **Hybrid**: Safety net if vector fails

#### 2. **Colloquial Medical Terms**
```
User query: "blood thinner bad stuff that can happen"
```
- **Vector**: Might struggle with "bad stuff" (informal language)
- **BM25**: Catches "blood thinner" exact phrase
- **Hybrid**: Combines semantic understanding + keyword matching

#### 3. **Rare Exact Medical Jargon**
```
User query: "QT interval prolongation ciprofloxacin"
```
- **Vector**: Might generalize to "heart problems" (loses specificity)
- **BM25**: Exact match on rare term "QT interval prolongation"
- **Hybrid**: BM25's precision shines here

#### 4. **Abbreviations vs Full Terms**
```
User query: "ACE inhibitor side effects"
```
- **Vector**: Maps "ACE inhibitor" → "Angiotensin-Converting Enzyme inhibitor"
- **BM25**: Matches "ACE" exactly (what if doc only has abbreviation?)
- **Hybrid**: Covers both semantic + exact match

#### 5. **Mixed Layman + Medical Language**
```
User query: "can I take blood pressure medicine with grapefruit"
```
- **Vector**: Maps "blood pressure medicine" → specific drug class
- **BM25**: Matches "grapefruit" food interaction warnings
- **Hybrid**: Best of both worlds

### Why We Can't Conclude Hybrid is Useless

❌ **Limited test data**: Only 5 queries (need 50-100 for confidence)  
❌ **Clean test bias**: All queries well-formed (real users messier)  
❌ **No diversity**: Missing typos, slang, abbreviations, colloquial terms  
❌ **Architectural issue**: Current hybrid broken (fixable with drug-aware filtering)

**Critical insight**: Vector's 100% accuracy is **query-type specific**. We've only tested the query types where vector excels[file:36].

---

## Hybrid's Architectural Problems (Fixable)

### Current Implementation Issues

1. **No drug-aware pre-filtering**
   - BM25 searches across ALL drugs' documents
   - Returns ciprofloxacin when asked about warfarin
   - Generic keywords match everywhere

2. **RRF merging too early**
   - Merges results before validating drug context
   - False positives contaminate top-K results
   - Weight tuning ineffective (architectural, not parametric)

3. **No reranking stage**
   - Final results go straight to LLM
   - No cross-encoder validation of actual relevance
   - Contaminated results reach end user

### Solution Path (Phase 1)

#### **Fix #1: Drug-Aware Filtering** (Estimated: 90% accuracy)

**Before** (Current):
```
Query: "warfarin side effects"
↓
BM25 searches ALL documents → finds "side effects" in ciprofloxacin doc
↓
Returns wrong drug
```

**After** (Phase 1):
```
Query: "warfarin side effects"
↓
Extract drug name: "warfarin"
↓
Pre-filter corpus: Only search warfarin documents
↓
BM25 searches ONLY warfarin docs → no false positives possible
↓
Hybrid merge: Vector + filtered BM25 → clean results
```

**Expected improvement**: 40% → 90% BM25 accuracy (eliminates cross-drug contamination)

#### **Fix #2: Cross-Encoder Reranking** (Estimated: +5-10% accuracy)

```
Hybrid retrieves top-20 candidates
↓
Cross-encoder (e.g., ms-marco-MiniLM) rescores by actual relevance
↓
Rerank and return top-10
↓
Final results validated for query-document relevance
```

**Expected improvement**: Additional 5-10% on top of drug-aware filtering

---

## Recommendations by Phase

### Phase 0 (Current - February 2026)

**Decision**: ✅ **Use Vector-Only for `/retrieve` API endpoint**

**Why**:
- Proven 100% accuracy on clean queries
- Acceptable latency (33ms)
- Simple implementation (already working)
- Avoids BM25 contamination risk
- Fast to ship for PoC validation

**Important**: ✅ **Keep hybrid code intact** (don't delete!)
- Limited test data (5 queries insufficient)
- Need to evaluate on diverse query types
- Architectural fixes planned for Phase 1

**API design**:
```python
@app.post("/retrieve")
def retrieve(query: str, top_k: int = 10):
    # Phase 0: Vector-only
    results = vector_retriever.retrieve(query, top_k)
    return {"results": results, "retriever": "vector"}
```

---

### Phase 1 (Next Iteration - March 2026)

**Goal**: Fix hybrid and test on diverse query types

**Tasks**:
1. ✅ **Implement drug-aware filtering**
   - Extract drug names from queries (NER or regex)
   - Pre-filter corpus before BM25 search
   - Test on 50+ diverse queries (messy, typos, slang)

2. ✅ **Add cross-encoder reranking**
   - Integrate `ms-marco-MiniLM-L-12` or similar
   - Rescore top-20 hybrid results
   - Return validated top-10

3. ✅ **Expand test dataset**
   - Add messy queries ("warafin side efects")
   - Add colloquial terms ("blood thinner problems")
   - Add abbreviations ("ACE inhibitor effects")
   - Add typos and slang
   - Target: 50-100 diverse queries

4. ✅ **Compare fixed hybrid vs vector-only**
   - Measure accuracy on new test set
   - Analyze per-query-type performance
   - Decide: Keep hybrid or stay vector-only?

---

### Phase 2 (Production - April 2026+)

**Goal**: Query-type classification and routing

**Option A**: **Query Classifier Router**
```python
def retrieve(query: str):
    query_type = classify_query(query)  # clean vs messy vs technical

    if query_type == "clean_semantic":
        return vector_retriever.retrieve(query)
    elif query_type == "messy_or_typos":
        return hybrid_retriever.retrieve(query)  # fixed hybrid
    elif query_type == "exact_medical_term":
        return bm25_retriever.retrieve(query)
    else:
        return hybrid_retriever.retrieve(query)  # default
```

**Option B**: **Always Use Fixed Hybrid**
- If Phase 1 tests show fixed hybrid ≥ vector on all query types
- Simpler implementation (no classifier needed)
- Covers all edge cases

**Option C**: **A/B Testing**
- Route 50% traffic to vector, 50% to hybrid
- Measure user satisfaction, accuracy, latency
- Data-driven decision after 1000+ real queries

---

## Key Learnings & Meta-Insights

### 1. Limited Test Data = Limited Conclusions

**What we know**:
- Vector wins on 5 clean, semantic queries
- BM25 fails on generic medical keywords
- Hybrid contaminated by BM25 false positives

**What we DON'T know**:
- How vector performs on messy queries
- How vector handles typos
- How vector handles rare medical jargon
- How fixed hybrid performs on diverse queries

**Action**: Need 10x more test queries before confident production decision.

---

### 2. Clean Test Queries ≠ Real User Queries

**Test bias**:
- "What are the side effects of warfarin?" ← Perfect grammar
- Real user: "warafin side efects" ← Messy, typos
- Real user: "blood thinner bad stuff" ← Colloquial
- Real user: "warfrin make me bleed?" ← Very messy

**Lesson**: Vector's 100% accuracy might drop on real-world queries. Need diverse test set.

---

### 3. Vector's Perfect Score Might Be Misleading

**Concern**: Vector scored 100%, but:
- Only tested on **5 queries**
- All queries were **clean and well-formed**
- All queries were **semantic in nature** (vector's strength)
- Haven't tested on **exact medical terms** (BM25's strength)

**Example where vector might fail**:
```
Query: "CYP2C9 warfarin metabolism"
```
- Rare enzyme name "CYP2C9"
- Might need exact keyword match
- Vector might generalize too much
- BM25 would catch exact term

---

### 4. Hybrid's Low Score is Fixable

**Current state**: 64% accuracy (broken)

**Root cause**: Architectural, not parametric
- Drug-aware filtering missing
- Cross-encoder reranking missing
- Weight tuning ineffective

**Expected after fixes**: 90-95% accuracy
- Drug filtering eliminates cross-contamination
- Cross-encoder validates relevance
- Might exceed vector on messy queries

**Conclusion**: Don't dismiss hybrid based on current implementation. It's a fixable architectural issue, not a fundamental limitation[file:36].

---

## Next Steps (Day 6 Plan)

### Immediate Actions (Today - February 1, 2026)

1. ✅ **Document created** (this file)
2. ⏩ **Build FastAPI endpoint** (Task 9)
   - Implement `/retrieve` with vector-only
   - Add `/health` and `/stats` endpoints
   - Test API locally

3. ⏩ **Plan Phase 1 work** (documentation only)
   - Design drug-aware filtering strategy
   - Research cross-encoder models
   - Define expanded test dataset requirements

### Phase 1 Preparation

**Dataset expansion**:
- Collect 50+ messy/diverse queries
- Include typos, slang, abbreviations
- Cover all question types (side effects, dosage, interactions, etc.)
- Annotate expected results

**Architecture design**:
- Drug extraction pipeline (NER or regex)
- Filtered BM25 implementation
- Cross-encoder integration point
- Routing strategy (if needed)

---

## Appendix: Test Query Details

### Query 1: "What are the side effects of warfarin?"

| Retriever | Top Drug | Latency | Score Range | Correct? |
|-----------|----------|---------|-------------|----------|
| Vector    | warfarin | 85.1ms  | 0.54-0.59   | ✅ 100%  |
| BM25      | ciprofloxacin | 2.8ms | 0.00-1.00 | ❌ Rank 1 wrong |
| Hybrid    | warfarin (R1), cipro (R2) | 23.7ms | 0.77-1.00 | ⚠️ Contaminated |

### Query 2: "What is the recommended dosage of atorvastatin?"

| Retriever | Top Drug | Latency | Correct? |
|-----------|----------|---------|----------|
| Vector    | atorvastatin | 24.4ms | ✅ 100%  |
| BM25      | atorvastatin (mixed) | 4.0ms | ⚠️ Mixed results |
| Hybrid    | atorvastatin | 24.7ms | ✅ Mostly correct |

### Query 3: "What are the contraindications for amoxicillin?"

| Retriever | Top Drug | Latency | Correct? |
|-----------|----------|---------|----------|
| Vector    | amoxicillin | 21.3ms | ✅ 100%  |
| BM25      | osteoarthritis guideline | 2.9ms | ❌ Rank 1 wrong |
| Hybrid    | amoxicillin (R1), osteo (R2) | 26.0ms | ⚠️ Contaminated |

### Query 4: "How does metformin work?"

| Retriever | Top Drug | Latency | Correct? |
|-----------|----------|---------|----------|
| Vector    | metformin | 16.9ms | ✅ 100%  |
| BM25      | metformin | 2.4ms | ✅ 100%  |
| Hybrid    | metformin | 24.8ms | ✅ 100%  |

**Note**: BM25 performed well here because "metformin" keyword dominated scoring.

### Query 5: "What drugs interact with lisinopril?"

| Retriever | Top Drug | Latency | Correct? |
|-----------|----------|---------|----------|
| Vector    | lisinopril | 19.2ms | ✅ 100%  |
| BM25      | warfarin | 4.0ms | ❌ Rank 1 wrong |
| Hybrid    | lisinopril (R1), warfarin (R2-3) | 23.1ms | ⚠️ Contaminated |

---

## Summary Decision Matrix

| Phase | Retriever | Rationale | Status |
|-------|-----------|-----------|--------|
| **Phase 0** (Now) | **Vector-only** | Proven 100% on clean queries, simple, fast enough | ✅ **Recommended** |
| **Phase 1** (March) | **Fixed Hybrid** | Test on diverse queries after drug-filtering + reranking | 🔧 **Implement & Test** |
| **Phase 2** (Production) | **TBD** | Data-driven decision after Phase 1 testing | ⏳ **Depends on Phase 1** |

---

**Document Version**: 1.0  
**Last Updated**: February 1, 2026, 6:30 PM IST  
**Author**: AI Engineering Team  
**Status**: ✅ Ready for Review
