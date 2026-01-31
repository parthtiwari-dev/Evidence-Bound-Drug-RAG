# Domain Scope — Adult Drug Prescribing & Drug Interaction Guidelines

## 1. One-line description

This system answers questions about adult drug dosing, interactions, contraindications, and warnings strictly from official guideline documents (FDA, NICE/NHS/BNF, WHO) for a fixed set of drugs.

## 2. Domain definition

- **Domain name:** Adult Drug Prescribing & Drug Interaction Guidelines  
- **Primary focus:**
  - Recommended adult dosages
  - Drug–drug interactions
  - Contraindications and precautions
  - Warnings and boxed warnings
- **Locked drug set:**
  - Cardiovascular: Atorvastatin, Lisinopril
  - Antibiotics: Amoxicillin, Ciprofloxacin
  - Analgesics: Ibuprofen, Paracetamol
  - Endocrine / Anticoagulant: Metformin, Warfarin

The system is not a general medical assistant; it is restricted to prescribing-related information for the drugs listed above.

## 3. Population

- **In-scope population:** Adults (age ≥ 18 years).  
- **Out-of-scope population:**
  - Pediatric dosing, indications, and contraindications.
  - Neonatal and adolescent-specific guidance.

If a question explicitly targets pediatric use, the system must refuse and state that it is limited to adult prescribing guidelines.

## 4. Geography

The system operates over guideline documents from three authority families:

- **United States:** FDA drug labels and official prescribing information.  
- **United Kingdom:** NICE / NHS / BNF prescribing guidance.  
- **Global:** WHO essential medicines and related technical documents.

Guidance specific to other countries or regions is considered out-of-scope unless it is embedded inside FDA, NICE/NHS/BNF, or WHO documents, in which case it is treated as contextual but not as a separate authority.


If multiple authoritative documents provide conflicting guidance for the same drug and question, the system must cite the higher-priority authority and may note the existence of disagreement without attempting to reconcile it.


## 5. Timeframe

- **Target timeframe for primary documents:** 2015–2024.  
- Documents within this range are considered current for the purposes of this system.

If only pre-2015 documents are available for a given drug/source:

- They may be included, but must be **explicitly tagged in metadata** as “pre-2015”.  
- Where relevant, the system should reflect that the information comes from an older document and may not represent the most recent guidance.

## 6. In-scope information types

The system is allowed to answer questions about:

- Standard adult dosing ranges and recommended regimens.  
- Dose adjustments where clearly specified in guidelines without requiring patient-specific clinical judgment beyond
  the document text.  
- Listed drug–drug interactions for the locked drugs.  
- Stated contraindications and precautions.  
- Warnings and boxed warnings, including serious risks and safety alerts.  
- References to specific sections of FDA, NICE/NHS/BNF, or WHO documents, when available.

## 7. Handling pregnancy and lactation content

Pregnancy and lactation sections frequently appear in FDA and NICE/NHS/BNF documents.

- The system **may answer** questions about what the guideline states for pregnancy or lactation, **but only by quoting or summarizing the guideline text**, not by making recommendations.  
- Answers must clearly attribute the information to the source guideline (e.g., “According to the FDA label for metformin…”).  
- The system **must not** provide personalized advice such as whether a specific user should or should not take a drug during pregnancy or breastfeeding.

## 8. Explicit out-of-scope information

The system must **not** answer questions that require:

- Personalized treatment recommendations (e.g., “What should I take?”, “Is this safe for me?”).  
- Diagnostic decisions or disease classification.  
- Comparative treatment optimization (e.g., “What is the best treatment for X?”).  
- General medical education outside the locked drugs and authorities.  
- Information coming from non-official sources (blogs, forums, non-official PDFs).

For these, the system must refuse and reference its limited domain.

## 9. Boundary rule

If a question:

- Requires patient-specific clinical judgment, **or**  
- Involves drugs outside the locked list, **or**  
- Depends on guidelines outside FDA, NICE/NHS/BNF, or WHO, **or**  
- Requests recommendations beyond what the documents explicitly state,

then the system must **refuse to answer** and explain that it is restricted to adult prescribing and interaction information for the specified drugs from FDA, NICE/NHS/BNF, and WHO documents.
