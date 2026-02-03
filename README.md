# Evidence-Bound-Drug-RAG

A Retrieval-Augmented Generation (RAG) system that provides evidence-grounded answers about drugs using curated FDA/NICE documents and a reproducible evaluation pipeline (RAGAS).

**Key result:** RAGAS overall score **0.71 / 1.0 (GOOD)** — production-ready for an MVP with strong faithfulness and a focused roadmap to improve retrieval precision.

**Quick links**
- Evaluation report: [docs/evaluation_results_final.md](docs/evaluation_results_final.md)
- Project stats & conclusion: [docs/PROJECT_STATISTICS.md](docs/PROJECT_STATISTICS.md)
- Sprint summary (Day 10): [new_folder/day 10 summary.md](new_folder/day%2010%20summary.md)
- Main evaluation script: [scripts/09_ragas_evaluation.py](scripts/09_ragas_evaluation.py)

**What this repo contains**
- Data ingestion, chunking, and retrieval pipelines under `scripts/` and `src/`
- Evaluation artifacts in `data/evaluation/` (results, summaries)
- Documentation and analysis in `docs/`

**High-level findings**
- Overall RAGAS score: **0.71 (GOOD)**
- Faithfulness: **~0.80** (minimal hallucination)
- Answer Relevancy: **~0.70**
- Context Precision: **~0.64** (primary improvement area)
- Success rate on the 20-query test set: **80%** (16/20 answered)
- Refusal policy: **Correct and safe** (4/20 safe refusals)

Getting started
1. Create and activate a Python virtual environment (Windows PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Prepare the Chroma DB and chunks (ingest + chunk):

```powershell
python scripts/04_chunk_and_analyze.py
```

3. Run the RAGAS evaluation (reproduces the results in the docs):

```powershell
python scripts/09_ragas_evaluation.py
```

Outputs and reproducibility
- Evaluation outputs: `data/evaluation/ragas_results.json`, `data/evaluation/ragas_summary.json` (see `data/evaluation/`).
- Final report and interpretation: [docs/evaluation_results_final.md](docs/evaluation_results_final.md)

Where to look next
- Improve retrieval (context precision) with cross-encoder reranking or medical embeddings — documented in [docs/evaluation_results_final.md](docs/evaluation_results_final.md).
- For a quick read on the sprint and rationale, see [new_folder/day 10 summary.md](new_folder/day%2010%20summary.md).

Contributing
- Open an issue or a PR with improvements to retrieval, evaluation, or additional test queries. For major changes, add tests and update `data/evaluation/` results.

Contact
- Author / maintainer notes and contact are in the project docs.

----
Last updated: February 3, 2026 — evaluation and documentation consolidated.