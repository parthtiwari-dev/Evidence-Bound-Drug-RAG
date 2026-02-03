# OpenAI RAGAS Evaluation Setup Guide

## 🎯 Overview

This guide will help you set up and run the OpenAI-powered RAGAS evaluation script that is:
- **5-10x faster** than Groq sequential evaluation
- **Cheaper** than expected ($0.02-0.05 total cost)
- **Higher quality** evaluation with all 3 metrics
- **More reliable** with parallel processing

---

## 📋 Prerequisites

### 1. OpenAI API Key

You mentioned you've already purchased OpenAI API credit. Now you need to:

1. Go to: https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Name it something like "ragas-evaluation"
4. Copy the key (starts with `sk-proj-...`)
5. **IMPORTANT**: Save it immediately - you can only see it once!

### 2. Update Your .env File

Add your OpenAI API key to `.env`:

```bash
# Existing keys
APP_ENV=dev
DATA_DIR=./data
CHROMA_DB_DIR=./data/chromadb
DOCS_DIR=./docs
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
LLAMA_CLOUD_API_KEY=llx-HxG9X3tx6vEkfM2ODyv9CiDF7i92a23KybzBEqLOvflkn4MR
GROQ_API_KEY=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

# ADD THIS LINE:
OPENAI_API_KEY=sk-proj-YOUR-KEY-HERE
```

**Replace `sk-proj-YOUR-KEY-HERE` with your actual API key.**

### 3. Verify OpenAI Package is Installed

Your `requirements.txt` already has `openai` and `langchain-openai`, so you're good!

If you need to reinstall:
```bash
pip install openai langchain-openai --break-system-packages
```

---

## 💰 Cost Breakdown

### Using `gpt-4o-mini` (Recommended - Best Value)

**Pricing** (as of Feb 2025):
- Input: $0.150 per 1M tokens
- Output: $0.600 per 1M tokens

**For 20 test queries:**
- Estimated input: ~60,000 tokens = $0.009
- Estimated output: ~20,000 tokens = $0.012
- **Total: ~$0.02-0.05**

### Alternative: `gpt-4o` (Higher Quality, More Expensive)

**Pricing**:
- Input: $2.50 per 1M tokens
- Output: $10.00 per 1M tokens

**For 20 test queries:**
- **Total: ~$0.50-1.00**

**Recommendation**: Start with `gpt-4o-mini`. The quality is excellent for evaluation and costs 20x less!

---

## 🚀 Running the Evaluation

### Step 1: Run the Script

```bash
python scripts/09_ragas_evaluation_openai.py
```

### Step 2: Expected Output

```
================================================================================
INITIALIZING RAG SYSTEM FOR EVALUATION
================================================================================

📦 Loading Vector Store...
✅ Loaded 853 chunks

📦 Loading BM25 Index...
✅ BM25 index loaded

🔗 Initializing Hybrid Retriever...
✅ HybridRetriever initialized

🤖 Initializing LLM Generator (Groq)...
✅ LLMGenerator initialized

📋 Loading test queries...
✅ Loaded 20 test queries

================================================================================
RUNNING RAG PIPELINE ON ALL TEST QUERIES
================================================================================

[1/20] Processing: 1
  Query: What are the common side effects of warfarin?
  ✅ Answer generated (1728 chars, 5 citations)

[2/20] Processing: 2
...

================================================================================
RUNNING RAGAS EVALUATION WITH OPENAI
================================================================================

🤖 Initializing OpenAI evaluator...
   Model: gpt-4o-mini
   Embeddings: text-embedding-3-small
   Max workers: 4 (parallel processing)
   Total samples: 20

📊 Metrics: Faithfulness, Answer Relevancy, Context Precision
   Estimated cost: $0.02-0.05 (very cheap!)
   Estimated time: ~5-8 minutes

Evaluating: 100%|███████████████████| 60/60 [05:24<00:00,  5.41s/it]

✅ Evaluation complete! (5.4 minutes)

💰 Estimated Cost:
   Input tokens: ~60,000 @ $0.150/1M = $0.0090
   Output tokens: ~20,000 @ $0.600/1M = $0.0120
   Total: $0.0210

================================================================================
📊 RAGAS EVALUATION RESULTS (OpenAI)
================================================================================

🎯 FAITHFULNESS: 0.8234
🎯 ANSWER RELEVANCY: 0.7891
🎯 CONTEXT PRECISION: 0.6512

🏆 OVERALL SCORE: 0.7546 (GOOD ⭐⭐⭐⭐ - Acceptable for MVP)

💰 TOTAL COST: $0.0210
```

---

## ⚙️ Configuration Options

### Adjust Parallel Processing

In `09_ragas_evaluation_openai.py`, line 55:

```python
MAX_WORKERS = 4  # Default: 4 parallel workers
```

**Options:**
- `MAX_WORKERS = 1`: Sequential (slow but safe, ~20 min)
- `MAX_WORKERS = 2`: Moderate (10-12 min)
- `MAX_WORKERS = 4`: Fast (5-8 min) ⭐ **Recommended**
- `MAX_WORKERS = 8`: Very fast (3-5 min) - may hit rate limits

### Change Model

In `09_ragas_evaluation_openai.py`, line 52:

```python
EVALUATOR_MODEL = "gpt-4o-mini"  # Cheapest
# EVALUATOR_MODEL = "gpt-4o"     # Higher quality, 20x more expensive
# EVALUATOR_MODEL = "gpt-4-turbo" # Legacy, not recommended
```

### Adjust Timeout

In `09_ragas_evaluation_openai.py`, line 58:

```python
TIMEOUT = 60  # Seconds per request
```

Increase if you get timeout errors.

---

## 🔧 Troubleshooting

### Error: "OPENAI_API_KEY not found"

**Fix:**
1. Check `.env` file has the key
2. Restart your terminal/IDE
3. Verify with: `python -c "import os; print(os.getenv('OPENAI_API_KEY'))"`

### Error: "RateLimitError"

**Cause**: Too many parallel requests

**Fix**: Reduce `MAX_WORKERS` from 4 to 2 or 1

### Error: "Insufficient funds"

**Cause**: No credit in OpenAI account

**Fix**: Add credit at https://platform.openai.com/settings/organization/billing

### Script Crashes Midway

**Good news**: The script has checkpoint/resume capability!

**Fix**: Just run it again:
```bash
python scripts/09_ragas_evaluation_openai.py
```

It will resume from where it left off.

---

## 📊 Interpreting Results

### Faithfulness Score (0-1)
- **0.85+**: Excellent - Minimal hallucination
- **0.70-0.85**: Good - Acceptable hallucination rate
- **0.50-0.70**: Fair - Some hallucination, needs work
- **< 0.50**: Poor - Severe hallucination problem

### Answer Relevancy Score (0-1)
- **0.85+**: Excellent - Answers highly relevant to questions
- **0.70-0.85**: Good - Most answers are relevant
- **0.50-0.70**: Fair - Some answers miss the point
- **< 0.50**: Poor - Answers don't address questions

### Context Precision Score (0-1)
- **0.75+**: Excellent - Retrieval is highly accurate
- **0.60-0.75**: Good - Retrieval is mostly accurate
- **0.40-0.60**: Fair - Retrieval needs tuning
- **< 0.40**: Poor - Retrieval is missing relevant chunks

### Overall Score (Average of 3 metrics)
- **0.85+**: EXCELLENT ⭐⭐⭐⭐⭐ (Production-ready)
- **0.70-0.85**: GOOD ⭐⭐⭐⭐ (Acceptable for MVP)
- **0.60-0.70**: FAIR ⭐⭐⭐ (Needs improvement)
- **< 0.60**: POOR ⭐⭐ (Requires redesign)

---

## 🆚 Comparison: OpenAI vs Groq

| Aspect | Groq (Sequential) | OpenAI (Parallel) |
|--------|-------------------|-------------------|
| **Model** | llama-3.1-8b-instant | gpt-4o-mini |
| **Runtime** | 20-30 minutes | 5-8 minutes ✅ |
| **Cost** | Free (with limits) | $0.02-0.05 ✅ |
| **Metrics** | 2 (faithfulness + precision) | 3 (all metrics) ✅ |
| **Rate Limits** | 500K tokens/day 😞 | Essentially unlimited ✅ |
| **Quality** | Good | Better ✅ |
| **Reliability** | Can fail mid-run | Checkpoint/resume ✅ |

**Winner**: OpenAI for this use case!

---

## 📁 Output Files

After running, you'll get:

### 1. `data/evaluation/ragas_results_openai.json`
Full detailed results with per-query scores.

### 2. `data/evaluation/ragas_summary_openai.json`
High-level summary with aggregate metrics.

### 3. `data/evaluation/ragas_checkpoint.json` (temporary)
Checkpoint file for resume capability (auto-deleted on success).

---

## 🎯 Next Steps After Evaluation

Based on your scores:

### If Faithfulness < 0.70:
- Review `src/generation/prompts.py`
- Make prompt more strict about citing sources
- Reduce temperature (already at 0.0, so check prompt)

### If Answer Relevancy < 0.70:
- Review question understanding in prompts
- Adjust prompt to focus more on question

### If Context Precision < 0.60:
- Tune hybrid retriever weights (try 0.7 vector / 0.3 BM25)
- Increase `top_k` from 5 to 10
- Review chunk quality

---

## 💡 Pro Tips

1. **Run a test first**: Comment out 15 queries and test with just 5 to verify setup
2. **Monitor costs**: Check https://platform.openai.com/usage after running
3. **Save the results**: Git commit the results files for future comparison
4. **Compare with baseline**: Run again after making improvements to see delta
5. **Use parallel processing**: 4 workers is the sweet spot for speed vs reliability

---

## ❓ FAQ

**Q: Can I use this with Batch API for even cheaper?**
A: Not currently - RAGAS requires synchronous responses. Batch API is async.

**Q: Will this work with Azure OpenAI?**
A: Yes! Just change the API endpoint in the script.

**Q: Can I evaluate with GPT-4 but generate with Groq?**
A: Yes! That's exactly what this script does. Generation stays on Groq (free), evaluation uses OpenAI.

**Q: What if I run out of API credit mid-run?**
A: The checkpoint system will save progress. Add more credit and re-run.

**Q: How do I know if my results are good?**
A: Compare to RAGAS benchmarks: most production RAG systems score 0.70-0.85 overall.

---

## 🚀 Ready to Run!

You're all set! Just run:

```bash
python scripts/09_ragas_evaluation_openai.py
```

Expected cost: **$0.02-0.05** 💰
Expected time: **5-8 minutes** ⏱️
Expected quality: **All 3 metrics with high reliability** ✅

Good luck! 🍀
