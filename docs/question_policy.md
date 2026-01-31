# Question Policy — Allowed and Disallowed Questions

## 1. Purpose

This document defines which question patterns are in-scope for this system and which must be refused. The goal is to ensure that all answered questions stay within adult drug prescribing and interaction guidelines for a fixed set of drugs and authorities.

## 2. High-level rule

The system only answers questions that:

- Concern the **locked drug set**:
  - Atorvastatin, Lisinopril, Amoxicillin, Ciprofloxacin, Ibuprofen, Paracetamol, Metformin, Warfarin.
- Are about **adult** drug prescribing, interactions, contraindications, warnings, or closely related metadata explicitly covered in the documents.
- Can be answered **directly from FDA, NICE/NHS/BNF, or WHO documents** in the curated corpus.

All other questions must be refused according to the refusal policy.

## 3. Allowed question classes

The following patterns are explicitly allowed.

### 3.1 Authority + drug + topic

Questions that explicitly reference an authority, a drug, and a prescribing-related topic:

- “According to FDA, what are the contraindications of warfarin?”  
- “According to NICE, what is the recommended adult dosage of metformin?”  
- “According to WHO, what interactions are noted for ibuprofen?”

### 3.2 Drug + dosage (implicit authority)

Questions about standard adult dosing where the answer is derived from one or more guideline documents:

- “What dosage does NICE recommend for atorvastatin in adults?”  
- “What is the usual adult dose of amoxicillin according to FDA labeling?”  
- “What is the typical adult dose of ciprofloxacin for infections, based on guidelines?”

### 3.3 Drug interactions

Questions about interactions involving one or more locked drugs:

- “What interactions are listed for ibuprofen in the FDA label?”  
- “According to WHO, what important drug–drug interactions are noted for metformin?”  

Questions involving interactions between **two locked drugs** are allowed, provided both drugs are in the locked set:

- “Are there any interactions between warfarin and ibuprofen according to FDA or NICE?”

### 3.4 Warnings and boxed warnings

Questions about warnings, boxed warnings, and serious risks:

- “What boxed warnings does the FDA label include for warfarin?”  
- “What serious warnings are mentioned for ciprofloxacin in NICE guidance?”  
- “What safety warnings does the FDA label provide for metformin?”

### 3.5 Document-specific questions

Questions that refer directly to specific documents:

- “What does the WHO Model List of Essential Medicines 2023 say about paracetamol?”  
- “In the FDA label for lisinopril, what are the key warnings?”  
- “According to the NICE guideline document on atorvastatin, what are the main contraindications?”

## 4. Special allowed cases

### 4.1 Pregnancy and lactation sections

Questions about **what the guideline text states** for pregnancy or lactation are allowed:

- “According to the FDA label, what does it say about using ibuprofen during pregnancy?”  
- “What does NICE guidance mention about metformin use during breastfeeding?”

The system may summarize or quote the guideline text but must **not** turn this into personalized recommendations for an individual.

### 4.2 Timeframe and “current” recommendations

When questions imply recency, such as:

- “What are the current FDA recommendations for lisinopril dosage?”

The system should:

- Base answers on documents from **2015–2024** when available.  
- If only pre-2015 documents exist, it may answer but should reflect that the information comes from an older document when this is relevant.

## 5. Disallowed question classes

The following patterns are explicitly disallowed and must trigger refusal.

### 5.1 Personalized treatment and safety questions

- “What should I take for my back pain?”  
- “Is warfarin safe for me if I have kidney disease?”  
- “Can I take ibuprofen with my other medications?”  
- “Should I stop taking metformin?”

These require patient-specific clinical judgment and are outside the system’s scope.

### 5.2 Best / optimal treatment decisions

- “What is the best drug to treat my hypertension?”  
- “Is metformin better than insulin for diabetes?”  
- “Which antibiotic is the best choice for my infection?”

The system must not rank or recommend treatments beyond what specific documents state.

### 5.3 Diagnostic or disease management questions

- “How should I manage my high blood pressure?”  
- “Do these symptoms mean I need antibiotics?”  
- “How should I adjust treatment if my INR is too high on warfarin?”

These are diagnostic or management decisions, not document lookup.

### 5.4 Outside locked drugs or authorities

- “What does FDA say about omeprazole?” (drug not in locked list)  
- “What does UpToDate recommend for warfarin?” (non-authority source)  
- “What do local hospital guidelines say about ciprofloxacin dosing?”

If the question concerns drugs outside the locked set or sources outside FDA, NICE/NHS/BNF, or WHO, the system must refuse.

### 5.5 Non-adult populations

- “What is the pediatric dose of amoxicillin?”  
- “Is ibuprofen safe for infants?”  
- “What is the neonatal dosing of paracetamol?”

These are out-of-scope populations.

## 6. Borderline and ambiguous questions

When questions are ambiguous, the system should favor a conservative, document-based interpretation.

Examples:

- Question: “Is metformin safe in pregnancy?”  
  - Allowed frame: “According to the FDA label for metformin, the pregnancy section states that…”  
  - Not allowed: Direct advice on whether a specific person should or should not take metformin.

- Question: “How should the dose be adjusted for kidney problems?”  
  - If the question is generic and the document explicitly describes standard adjustments (e.g., by creatinine clearance ranges), the system may answer **only** by restating those ranges and conditions.  
  - If the question is clearly patient-specific (e.g., “for my kidney function” or with individual lab values), the system must refuse.

Ambiguous questions should be interpreted in the most **non-personalized, document-focused** way possible. If that is not possible, the system must refuse.

## 7. Enforcement rule and refusal tone

If a question violates any of:

- Domain scope (drug not in locked set, non-adult population, non-prescribing topic),  
- Authority scope (requires sources beyond FDA, NICE/NHS/BNF, or WHO),  
- Safety scope (personalized treatment or diagnostic advice),

then the system must **refuse to answer** and defer to a qualified healthcare professional.

Refusals should be **brief, factual, and reference the system’s limited scope**, without moralizing or offering medical advice. The detailed wording style for refusals is defined in `docs/refusal_policy.md`.
