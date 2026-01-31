# Ground Truth Definition — Answer Correctness Criteria

## 1. Purpose

This document defines when an answer produced by the system is considered correct, partially correct, or incorrect. These criteria guide both system design and later evaluation runs.

Ground truth for this project is not an abstract medical truth, but **what the authoritative documents say, used correctly under the system’s epistemic rules**.

## 2. Core correctness criteria

An answer is **correct** if all of the following hold:

1. **Authoritative citation**

   - The answer cites at least one chunk from an authoritative document:
     - Tier 1: FDA, NICE/NHS/BNF.
     - Tier 2: WHO.
   - The cited chunks respect the timeframe policy (2015–2024 preferred, older documents clearly identified when used).

2. **Semantic alignment**

   - The main claims in the answer are semantically aligned with the cited chunks.
   - The answer does not introduce new medical claims that are absent from or contradicted by the cited text.

3. **No conflict merging**

   - When multiple authorities disagree, the answer does **not** merge them into a synthesized recommendation.
   - Any mentioned disagreement is clearly attributed to specific authorities (e.g., “FDA states X, while WHO states Y”).

4. **Scope compliance**

   - The answer stays within the domain, population, and authority boundaries defined in:
     - `docs/domain_scope.md`
     - `docs/authority_hierarchy.md`
     - `docs/question_policy.md`
   - It does not drift into personalized medical advice or off-domain content.

If all four conditions are met, the answer is considered **correct** for this system.

## 3. Partial correctness

An answer is **partially correct** if:

- It cites relevant chunks from valid authorities, **but** one or more of the following apply:
  - It omits important constraints or conditions present in the source (e.g., special warnings, renal adjustment notes).
  - It mixes in minor additional statements that are not clearly supported, but also not clearly contradicted.
  - It is incomplete relative to the question (e.g., mentions some key interactions, but not all that are clearly emphasized in the document).

An answer that is correct but explicitly limited by missing information (for example, “the document does not specify a recommendation for X”) may still be considered **correct** if it accurately reflects what the source does and does not say.

In evaluation, partially correct answers may receive medium faithfulness or answer relevancy scores but should be distinguished from fully correct and clearly incorrect answers.

## 4. Incorrect answers

An answer is **incorrect** if any of the following occur:

- **No authoritative citation**
  - The answer does not cite any chunk from FDA, NICE/NHS/BNF, or WHO documents.

- **Misaligned citation**
  - The cited chunks do not actually support the main claims in the answer.
  - The answer contradicts the content of the cited guideline text.

- **Conflict merging**
  - The answer merges conflicting guidance from different authorities into a new recommendation that exists in none of the documents (e.g., “averaging” two different dosages).

- **Out-of-scope behavior**
  - The answer provides personalized recommendations or diagnostic conclusions.
  - The answer relies on sources outside the defined authorities (e.g., blogs, random articles not in the corpus).

Incorrect answers in this system are treated as **hallucinations or retrieval/generation failures** for analysis purposes.

## 5. Handling multiple authorities

For overlapping questions where multiple documents exist:

- If the answer:
  - Follows the authority hierarchy (Tier 1 preferred over Tier 2).
  - Clearly attributes guidance to a specific authority (e.g., FDA vs NICE vs WHO).
  - Avoids synthesizing a compromise dosage or recommendation.
  then it can still be considered **correct**, even if other documents exist with different guidance.

- If the answer:
  - Attempts to “average” FDA and WHO recommendations, or
  - Presents a unified dosage that exists in **none** of the documents,
  then it is **incorrect**, regardless of the underlying retrieval.

## 6. Timeframe and document versioning

- Answers based on documents from **2015–2024** are considered aligned with the target timeframe.
- If only pre-2015 documents are available and have been explicitly tagged as such:
  - Answers based on them can still be considered **correct**, with the understanding that they rely on older guidance.
- When multiple versions from the **same authority** exist (e.g., different FDA label years):
  - Correct answers should align with the **most recent version**.
  - Answers that clearly rely on superseded information when a newer version is present are considered **incorrect**.

## 7. Refusals and correctness

When a question is **out of scope** under the question policy:

- A proper **refusal** that:
  - Briefly explains that the system is limited to adult prescribing and interaction guidelines for the locked drugs, and
  - Does **not** attempt to provide medical advice,
  is considered the **correct behavior**.

- Attempting to answer such a question, even if the answer seems reasonable, is considered **incorrect** under this ground truth definition.

## 8. Connection to evaluation metrics

In later evaluation (e.g., with RAGAS or similar):

- **Faithfulness**
  - Measures how well the answer aligns with the cited chunks, penalizing unsupported or contradictory statements.

- **Answer relevancy**
  - Measures whether the answer addresses the user’s question while staying inside the defined domain and authority scope.

- **Context precision**
  - Measures how many of the retrieved/cited chunks are actually relevant to the answer.

These metrics are interpreted using this ground truth definition: correctness is defined by **document-grounded, authority-respecting, scope-compliant behavior**, not by clinical optimality.
