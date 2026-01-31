# Dataset Blueprint — Drug Guidelines Corpus

## 1. Purpose

This document defines the exact dataset blueprint for the medical RAG system: which PDFs to collect, from where, how many, and how they must be structured and named on disk. These rules are part of the system’s epistemic contract.

## 2. Target dataset size and composition

### 2.1 Total size

- **Total PDFs:** 22–30 documents.

### 2.2 By source family

- **NICE / NHS / BNF (Tier 1, UK):** 10–12 PDFs  
- **WHO (Tier 2, Global):** 1–2 PDFs  
- **FDA (Tier 1, US):** 8–12 PDFs

The final count within these ranges should be documented once collection is complete.

## 3. Locked drug list by source

The system focuses on a fixed set of drugs. For each drug, we expect coverage from specific authorities where available.

### 3.1 Cardiovascular

- **Atorvastatin**
  - Expected sources: NICE / NHS / BNF, possibly FDA, possibly WHO.
- **Lisinopril**
  - Expected sources: NICE / NHS / BNF, FDA.

### 3.2 Antibiotics

- **Amoxicillin**
  - Expected sources: NICE / NHS / BNF, FDA.
- **Ciprofloxacin**
  - Expected sources: NICE / NHS / BNF, FDA.

### 3.3 Analgesics / Painkillers

- **Ibuprofen**
  - Expected sources: NICE / NHS / BNF, FDA.
- **Paracetamol**
  - Expected sources: NICE / NHS / BNF, WHO.

### 3.4 Endocrine / Anticoagulant

- **Metformin**
  - Expected sources: NICE / NHS / BNF, FDA, WHO.
- **Warfarin**
  - Expected sources: FDA, possibly NICE / NHS / BNF.

During dataset collection, a simple table can track, for each drug, which authorities have at least one PDF in the corpus.

## 4. Folder structure rules

All raw documents must conform to the following structure:

```text
data/
├- raw/
-- nice/
-- who/
-- fda/
├- processed/
├- evaluation/
├- failures/
```

Rules:

All guideline PDFs are stored under data/raw/ in the appropriate subfolder:

- data/raw/nice/ for NICE / NHS / BNF documents.

- data/raw/fda/ for FDA label and prescribing PDFs.

- data/raw/who/ for WHO essential medicines PDFs.

No additional subfolders should be created under data/raw/ for this project.

data/processed/, data/evaluation/, and data/failures/ are reserved for downstream processing outputs, not raw PDFs.

## 5. File naming convention

Filenames encode authority, drug/topic, document type, and year. This supports authority and timeframe rules later in the pipeline.

### 5.1 NICE / NHS / BNF (Tier 1, UK)
  - **NICE / NHS / BNF (Tier 1, UK):** 10–12 PDFs  
  - **Current (Day 2):** 8 PDFs in `data/raw/nice/`

Pattern:

```text
nice_{drug_or_topic}_{doc_type}_{year}.pdf
```

drug_or_topic: short identifier such as atorvastatin, ibuprofen, paracetamol, metformin.

doc_type: e.g., guideline, prescribing, summary (small, consistent set).

year: 4-digit publication or last-update year (e.g., 2021).

Examples:

- nice_atorvastatin_guideline_2021.pdf
- nice_ibuprofen_prescribing_2020.pdf
- nice_metformin_guideline_2019.pdf

### 5.2 FDA (Tier 1, US)
- **FDA (Tier 1, US):** 8–12 PDFs  
- **Current (Day 2):** 12 PDFs in `data/raw/fda/`

Pattern:

```text
fda_{drug}_{doc_type}_{year}.pdf
```

drug: warfarin, metformin, ibuprofen, etc.

doc_type: typically label or highlights for “Highlights of Prescribing Information”.

year: 4-digit year of the label version.

Examples:

- fda_warfarin_label_2022.pdf
- fda_metformin_highlights_2021.pdf
- fda_amoxicillin_label_2018.pdf

### 5.3 WHO (Tier 2, Global)
- **WHO (Tier 2, Global):** 1–2 PDFs  
- **Current (Day 2):** 2 PDFs in `data/raw/who/`

Pattern:

```text
who_{document_name}_{year}.pdf
```

document_name: concise identifier, e.g., essential_medicines, technical_report.

year: 4-digit publication year.

Examples:

- who_essential_medicines_2023.pdf
- who_essential_medicines_technical_report_2023.pdf

Filenames must be in lowercase with underscores separating tokens.

## 6. Source discovery rules

### 6.1 NICE / NHS / BNF (Tier 1)

Target: Official guideline or prescribing PDFs for the locked drugs.

Primary domains:

- nice.org.uk
- nhs.uk
- Official BNF sources linked via NHS/NICE.

Example search queries:

- site:nice.org.uk atorvastatin guideline pdf
- site:nhs.uk ibuprofen prescribing pdf
- {drug} NICE guideline pdf

Selection rules:

- Prefer PDFs that are clearly labeled as guidelines, prescribing information, or official summaries.
- Avoid non-official mirrors or secondary re-hosts if an official source is available.

### 6.2 WHO (Tier 2)

Primary target: WHO Model List of Essential Medicines (most recent edition, e.g., 2023).

Domain: who.int

Example search query:

- "WHO Model List of Essential Medicines 2023 pdf"

Documents:

- who_essential_medicines_2023.pdf

Optionally, a related WHO technical report explicitly connected to the essential medicines list.

### 6.3 FDA (Tier 1)

Primary sources:

- Drugs@FDA
- DailyMed (dailymed.nlm.nih.gov)

Example search queries:

- {drug} FDA label pdf
- {drug} FDA highlights of prescribing information pdf

Selection rules:

- Only official label/highlights PDFs from authoritative FDA/DailyMed sources.
- Prefer the most recent label version when multiple are available.

## 7. Dataset constraints and exclusions

### 7.1 Exclusions

The following must not be included as part of the raw corpus:

- Non-official mirrors or third-party re-hosts when an official source is available.
- Blogs, forums, or commercial medical websites.
- PDFs whose provenance (FDA, NICE/NHS/BNF, WHO) is unclear.
- Documents that mainly cover drugs outside the locked list, unless they are multi-drug documents that still contain substantial content on the locked drugs.

### 7.2 Scanned PDFs and unreadable documents

Scanned image-only PDFs may still be downloaded if they are the only available official source, but:

- Their parseability issues will be documented in parsing analysis later.
- If a document is completely unreadable by parsers, it may be excluded from the effective corpus while still listed as an attempted source.

### 7.3 Multi-drug documents

Documents that cover multiple drugs (e.g., WHO essential medicines list) are allowed as long as they include sections about at least one locked drug.

They are named by document-level topic (e.g., who_essential_medicines_2023.pdf), not by individual drug.

## 8. Dataset completeness tracking

### Current collected files (Day 2 snapshot)

**FDA (`data/raw/fda/`):**

- 📕 fda_acetaminophen_highlights_2025.pdf
- 📕 fda_amoxicillin_highlights_2025.pdf
- 📕 fda_amoxicillin_tablets_2015.pdf
- 📕 fda_atorvastatin_highlights_2024.pdf
- 📕 fda_ciprofloxacin_extended_release_2025.pdf
- 📕 fda_ciprofloxacin_highlights_2025.pdf
- 📕 fda_ibuprofen_label_2024.pdf
- 📕 fda_lisinopril_highlights_2025.pdf
- 📕 fda_metformin_extended_release_2025.pdf
- 📕 fda_metformin_highlights_2026.pdf
- 📕 fda_warfarin_highlights_2022.pdf
- 📕 fda_warfarin_label_2025.pdf

**NICE / NHS / BNF (`data/raw/nice/`):**

- 📕 nice_amoxicillin_guideline_antibiotics_2025.pdf
- 📕 nice_amoxicillin_guideline_antimicrobial_2021.pdf
- 📕 nice_atorvastatin_guideline_cardiovascular_2023.pdf
- 📕 nice_lisinopril_guideline_hypertension_2019.pdf
- 📕 nice_metformin_guideline_diabetes_2021.pdf
- 📕 nice_metformin_guideline_diabetes_ng28_2022.pdf
- 📕 nice_osteoarthritis_management_ng226_2022.pdf
- 📕 nice_upper_gi_bleeding_management_cg141_2016.pdf

**WHO (`data/raw/who/`):**

- 📕 who_essential_medicines_2023.pdf
- 📕 who_selection_and_use_of_essential_medicine_2023.pdf


### Naming deviations to fix later

Some NICE filenames currently do not fully follow the `nice_{drug_or_topic}_{doc_type}_{year}.pdf` pattern
(e.g., `NG136_Visual_summary_20231019.pdf`, `RightCare-Pneumonia-toolkit.pdf`,
or mixed names like `acute-upper-gastrointestinal-bleeding-in-over-16s-management-pdf nice_warfarin_bnf_2023.pdf`).

These will either be:
- Renamed into the canonical pattern, or
- Explicitly handled in ingestion metadata extraction.

For now, they are documented here as known deviations.


## 9. Role of this blueprint in Phase 0

In Phase 0, this document is a contract, not an implementation:

- It defines which documents are allowed to enter the system.
- It encodes authority, geography, timeframe, and scope into folder and naming rules.
- Later phases (ingestion, retrieval, evaluation) must respect these constraints and treat violations as data or configuration errors, not as acceptable variation.

