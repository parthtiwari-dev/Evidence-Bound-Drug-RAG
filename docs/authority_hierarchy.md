# Authority Hierarchy — Drug Prescribing & Interaction Guidelines

## 1. Purpose

This document defines which sources are trusted, how they are ranked, and how conflicts are handled so the system never improvises its own medical authority. All retrieval, answer generation, and evaluation must respect this hierarchy.

## 2. Source tiers

### Tier 1 — Primary regulators / national authorities

Tier 1 consists of official, regulator-level prescribing information:

- **FDA** official drug labels and prescribing information (United States).  
- **NICE / NHS / BNF** official drug prescribing guidelines (United Kingdom).

Properties:

- Most specific and operational.
- Directly tied to legal and clinical practice in their jurisdictions.
- When available, Tier 1 **always takes precedence** over Tier 2 for overlapping questions.

### Tier 2 — Global guidelines

Tier 2 consists of global guidance:

- **WHO** Model List of Essential Medicines.  
- WHO technical reports and related official WHO PDFs directly connected to essential medicines and prescribing guidance.

Properties:

- Provides global baseline recommendations.
- Used primarily when no suitable Tier 1 document exists for a given drug/question, or when global context is explicitly requested.

Tier 2 **never overrides** Tier 1 when there is a direct conflict on the same drug and question.

### Tier 3 — Secondary or derived materials

For this project:

- **Tier 3 is disabled.**  
- We do **not** ingest or rely on secondary summaries, commentaries, blogs, or derivative compilations as part of the ground-truth corpus.

If any such documents are encountered, they are treated as out-of-scope for this system.

## 3. Encoding authority in the dataset

Authority is made explicit in both folder structure and filenames.

### 3.1 Folder structure

- `data/raw/nice/`  
  - NICE / NHS / BNF guideline PDFs (Tier 1, UK).  
- `data/raw/fda/`  
  - FDA drug labels and prescribing information PDFs (Tier 1, US).  
- `data/raw/who/`  
  - WHO essential medicines and related technical PDFs (Tier 2).

### 3.2 File naming conventions

Examples:

- `nice_atorvastatin_guideline_2021.pdf`  
- `nice_ibuprofen_prescribing_2020.pdf`  
- `fda_warfarin_label_2022.pdf`  
- `fda_metformin_highlights_2021.pdf`  
- `who_essential_medicines_2023.pdf`

Filenames encode:

- **Authority family** (`nice`, `fda`, `who`).  
- **Drug or document focus** (`atorvastatin`, `warfarin`, `essential_medicines`).  
- **Year** of publication or label/version (`2021`, `2022`, `2023`).

### 3.3 Document metadata (to be used later)

Each ingested document will carry at least:

- `authority_family` ∈ {`FDA`, `NICE`, `WHO`}  
- `tier` ∈ {1, 2}  
- `year` (integer, e.g., 2022)  
- `source_path` / filename

This metadata makes the hierarchy enforceable in retrieval, ranking, and answer construction.

## 4. Conflict resolution rules

### 4.1 General rule

If multiple authoritative documents provide conflicting guidance for the same drug and question:

- The system must **cite the higher-priority authority** according to this hierarchy.  
- It **may note** the existence of disagreement.  
- It must **not attempt to reconcile or average** the conflicting guidance.

Conflicts are **logged, not merged**.

### 4.2 Tier 1 vs Tier 2 (FDA/NICE vs WHO)

- When an FDA or NICE/NHS/BNF document (Tier 1) and a WHO document (Tier 2) disagree for the same adult prescribing question:
  - The system must **prefer the Tier 1 source** for the answer content.  
  - It may optionally mention that WHO guidance differs, but the primary recommendation in the answer must come from Tier 1.

### 4.3 FDA vs NICE (two Tier 1 authorities)

When both FDA and NICE/NHS/BNF provide guidance for the same drug and question:

- If the user question explicitly specifies geography:
  - For **US-specific questions** (e.g., “According to FDA…” or “In the US…”), prefer **FDA**.  
  - For **UK-specific questions** (e.g., “According to NICE…” or “In the UK…”), prefer **NICE/NHS/BNF**.
- If the question does **not** specify geography:
  - The system should answer **according to the authority explicitly mentioned** (e.g., “According to NICE…” vs “According to FDA…”).  
  - If no authority is mentioned and both FDA and NICE are relevant:
    - The system should **not silently merge** them.
    - It may either:
      - Choose one authority explicitly (e.g., “According to the FDA label…”), or  
      - State that FDA and NICE provide different recommendations and ask the user to clarify the jurisdiction if necessary.

In all cases, the system must avoid synthesizing a “compromise” dosage or recommendation that does not exist in any single document.

### 4.4 Multiple versions within the same authority

If there are multiple documents from the **same authority** (e.g., two FDA labels with different years or revisions):

- Prefer the **most recent version** (highest `year` or label revision) as the primary basis for the answer.  
- Older versions may still be used to explain that recommendations have changed, if relevant, but must not override the latest document.

## 5. When WHO guidance is used

WHO (Tier 2) should be used:

- When there is **no available Tier 1 document** for a given drug or for the specific question being asked.  
- When the question is about:
  - Inclusion of a drug in the **WHO Model List of Essential Medicines**, or  
  - Global framing of drug importance or baseline recommendations.

WHO guidance is **not** used to contradict or override FDA or NICE/NHS/BNF when those are present and explicit for the question at hand.

## 6. Out-of-authority sources

The system must treat the following as **out-of-scope** and not part of its authority:

- Blogs, forums, commercial medical websites, or news articles.  
- PDFs or text documents without clear FDA, NICE/NHS/BNF, or WHO provenance.  
- Individual research papers or journal articles not explicitly included as part of the curated corpus.

If a question can only be answered by going beyond FDA, NICE/NHS/BNF, or WHO sources, the system must **refuse** and explain that it is restricted to these authorities.

## 7. Summary of hierarchy

- **Tier 1:** FDA, NICE/NHS/BNF — primary, jurisdiction-specific prescribing authorities.  
- **Tier 2:** WHO — global guidance, used when Tier 1 is absent or for global questions.  
- **Tier 3:** Disabled for this project.

Conflicts:

- Higher tier overrides lower tier.  
- Conflicts are logged and may be mentioned, but never reconciled or merged by the system itself.
