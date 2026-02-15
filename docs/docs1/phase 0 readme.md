# Phase 0 — Epistemic Contract for the Drug Prescribing RAG System

## 1. What Phase 0 Achieved

Phase 0 defined the **epistemic boundaries** of the system before any modeling or coding.  
The goal was to lock in **what the system is allowed to know, answer, and refuse**, and how correctness is defined.

By the end of Phase 0, we produced six markdown documents that together act as a **contract** for the system’s behavior.

Artifacts:

- `docs/domain_scope.md`
- `docs/authority_hierarchy.md`
- `docs/question_policy.md`
- `docs/ground_truth_definition.md`
- `docs/dataset_blueprint.md`
- `docs/refusal_policy.md`

No code was written in this phase; only rules and structure.

---

## 2. Locked Domain and Scope

Defined in: `docs/domain_scope.md`

- **Domain name:** Adult Drug Prescribing & Drug Interaction Guidelines  
- **Primary focus:**
  - Adult dosing recommendations
  - Drug–drug interactions
  - Contraindications and precautions
  - Warnings and boxed warnings

- **Locked drug set:**
  - Cardiovascular: Atorvastatin, Lisinopril
  - Antibiotics: Amoxicillin, Ciprofloxacin
  - Analgesics: Ibuprofen, Paracetamol
  - Endocrine / Anticoagulant: Metformin, Warfarin

- **Population:** Adults (≥ 18 years).  
  - Pediatric / neonatal / adolescent content is out-of-scope.

- **Geography via authorities:**
  - US: FDA labels
  - UK: NICE / NHS / BNF
  - Global: WHO essential medicines and related docs

- **Timeframe:**
  - Prefer documents from **2015–2024**.
  - Older documents may be used but must be clearly tagged as pre-2015.

- **Key rule:**  
  If a question requires patient-specific judgment, involves drugs outside the locked list, or depends on other authorities, the system must **refuse**.

---

## 3. Authority Hierarchy and Conflicts

Defined in: `docs/authority_hierarchy.md`

- **Tier 1:** FDA, NICE / NHS / BNF  
  - Primary regulators, jurisdiction-specific prescribing authorities.  
  - Always preferred over lower tiers for overlapping questions.

- **Tier 2:** WHO  
  - Global baseline guidance.  
  - Used when Tier 1 is absent or for explicitly global questions.

- **Tier 3:** Disabled for this project  
  - No secondary summaries, blogs, or derivative sources.

- **Encoding:**
  - `data/raw/nice/`, `data/raw/fda/`, `data/raw/who/`
  - Filenames encode authority + drug/topic + doc type + year
    (e.g., `fda_warfarin_label_2022.pdf`, `who_essential_medicines_2023.pdf`).

- **Conflict rules:**
  - Higher tier overrides lower tier.
  - Conflicts are **logged, not merged**.
  - FDA vs NICE:
    - Respect explicit geography if mentioned in the question.
    - If both are relevant and geography is ambiguous, never silently average; either pick one and name it, or state that they differ.

Reason: this forces the system to stay honest about which authority it is using and prevents “made up” compromise recommendations.

---

## 4. Question Policy (What We Answer vs Refuse)

Defined in: `docs/question_policy.md`

The system only answers questions that:

- Are about the **locked drugs**.
- Concern adult prescribing, interactions, contraindications, or warnings.
- Can be answered **directly** from FDA, NICE/NHS/BNF, or WHO docs.

**Allowed examples:**

- “According to FDA, what are the contraindications of warfarin?”  
- “What dosage does NICE recommend for metformin in adults?”  
- “What interactions are listed for ibuprofen in the FDA label?”  
- “What boxed warnings does the FDA label include for warfarin?”  
- “What does the WHO Model List of Essential Medicines 2023 say about paracetamol?”  
- Interactions between two locked drugs (e.g., warfarin + ibuprofen).

**Special allowed:**

- Reporting what labels say about pregnancy/lactation (purely document-based, no personal advice).
- Timeframe-aware answers using 2015–2024 docs, clearly noting when only older guidance exists.

**Disallowed examples:**

- Personalized advice: “What should I take?”, “Is this safe for me?”  
- Best treatment: “What is the best drug for hypertension?”  
- Diagnostic/management: “How should I manage my blood pressure?”  
- Non-locked drugs: “What does FDA say about omeprazole?”  
- Non-adult populations: “What is the pediatric dose of amoxicillin?”

Reason: this makes the line between “lookup from docs” and “clinical judgment” very explicit and enforceable.

---

## 5. Ground Truth and Evaluation Criteria

Defined in: `docs/ground_truth_definition.md`

An answer is **correct** if:

1. **Authoritative citation**  
   - Cites at least one chunk from FDA, NICE/NHS/BNF, or WHO (Tier 1/2), respecting timeframe metadata.

2. **Semantic alignment**  
   - Main claims match what the cited chunks actually say.  
   - No new unsupported or contradictory medical claims.

3. **No conflict merging**  
   - Does not synthesize a compromise between conflicting authorities.  
   - Disagreement can be mentioned, but not reconciled by the system.

4. **Scope compliance**  
   - Respects domain, question, and authority boundaries.  
   - Does not slide into personalized advice.

**Partial correctness:**  
Correct authority and general idea, but missing important constraints, incomplete, or slightly sloppy while still largely aligned.

**Incorrect (treated as hallucination/failure):**

- No authoritative citation.
- Cited text does not support the answer.
- Merges conflicting guidance into a new recommendation.
- Uses out-of-scope sources.
- Answers questions that should have been refused.

**Refusals:**  
For out-of-scope questions, a proper refusal **is** the correct answer.

Reason: this anchors RAGAS-style metrics to a precise notion of “correct” for this system, not vague clinical truth.

---

## 6. Dataset Blueprint and File Layout

Defined in: `docs/dataset_blueprint.md`

- **Target size:** 22–30 PDFs total.

- **By source:**
  - NICE / NHS / BNF: 10–12
  - WHO: 1–2
  - FDA: 8–12

- **Folder layout:**

```text
data/
├── raw/
│   ├── nice/
│   ├── who/
│   ├── fda/
├── processed/
├── evaluation/
├── failures/
```

Naming convention examples:

```
nice_atorvastatin_guideline_2021.pdf

fda_warfarin_label_2022.pdf

who_essential_medicines_2023.pdf
```

Explicit rules on:

- Only using official sources.
- Handling multi-drug docs (like WHO list).
- Tracking which authorities exist for each locked drug.

Reason: turns directory layout into part of the epistemic model (authority, timeframe, scope encoded in filenames and paths).

---

## 7. Refusal Policy (How We Say “No”)

Defined in: `docs/refusal_policy.md`

The system must refuse when:

- A question violates domain, population, authority, or safety/clinical judgment constraints.

Refusal style:

- Brief (1–3 sentences).
- Factual and neutral.
- Explicit about limitations:
  - Adult prescribing only.
  - Locked drug set.
  - FDA / NICE / WHO only.
- No moralizing, no medical advice.

Templates defined for:

- Personalized treatment questions.
- Non-locked drugs.
- Pediatric questions.
- Outside-authority requests.
- Non-prescribing topics.

Reason: refusals are treated as first-class, correct behavior, not as errors.

---

## 8. Why Phase 0 Matters

By finishing Phase 0, we:

- Prevent scope creep (no random drugs, no random PDFs, no “medical chatbot” behavior).
- Make retrieval and generation auditable against explicit rules.
- Give evaluation (e.g., RAGAS + failure analysis) a clear notion of correct vs incorrect.
- Set up a repo that looks like enterprise AI, not a toy PDF chatbot.

From now on, every design or code decision should be checkable against this Phase 0 contract.

---

## 9. Next: Day 1 — Foundation + Data Reality

With Phase 0 locked, the next step (Day 1) will focus on:

- Creating the project skeleton (`src/`, `scripts/`, `data/`, `docs/`, `docker/`, `tests/`).
- Adding config (`settings.py`), schemas, requirements, and basic environment setup.

This will be done without changing any of the Phase 0 rules.

