"""
RAGAS Evaluation Script - VECTOR-ONLY VERSION

Changes from hybrid version:
- Uses VECTOR SEARCH ONLY (no BM25, no hybrid)
- Based on Feb 1, 2026 architecture decision: Vector achieved 100% accuracy
- Increased top_k from 5 to 8 for better coverage
- Simpler, faster, no BM25 contamination

Cost Estimates for 20 queries:
- Generation: ~$0.01 (20 queries with gpt-4o-mini)
- Evaluation: ~$0.05 (RAGAS with gpt-4o-mini)
- Total: ~$0.06-0.08 (₹5-7)

Runtime: 5-8 minutes (all parallel!)
"""

import json
import time
import os
import re
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import numpy as np
import statistics

# RAGAS and LangChain imports
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision
from ragas import RunConfig
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# Your existing imports
import sys
sys.path.append(str(Path(__file__).parent.parent))
from src.retrieval.vector_store import VectorStore
from src.models.schemas import RetrievedChunk

# Load environment
from dotenv import load_dotenv
load_dotenv(override=True)

# ============================================================================
# CONFIGURATION
# ============================================================================

# OpenAI Model Selection
GENERATION_MODEL = "gpt-4o-mini"      # For RAG answer generation
EVALUATOR_MODEL = "gpt-4o-mini"       # For RAGAS evaluation  
EMBEDDING_MODEL = "text-embedding-3-small"  # For embeddings

# Evaluation Settings
MAX_WORKERS = 4       # Parallel processing
TIMEOUT = 60
MAX_RETRIES = 2

# Cost per 1M tokens (as of Feb 2026)
COST_PER_1M_INPUT = 0.150      # gpt-4o-mini input
COST_PER_1M_OUTPUT = 0.600     # gpt-4o-mini output
COST_PER_1M_EMBEDDING = 0.020  # text-embedding-3-small


# ============================================================================
# SYSTEM PROMPT
# ============================================================================

def build_system_prompt() -> str:
    """Build system prompt with citation requirements and refusal policy."""
    return """You are a pharmaceutical information assistant that provides factual information from FDA and NICE drug documentation.

CRITICAL RULES FOR ANSWERING:

1. **Answer ONLY from provided context chunks**
   - Do NOT use general medical knowledge
   - Do NOT speculate or make assumptions
   - PRIORITIZE chunks with higher scores (shown in parentheses)
   - If the answer is not in the context, say: "I cannot answer this question based on the provided documentation."

2. **ALWAYS cite sources using [1], [2], [3] format**
   - Place citations immediately after EVERY claim
   - Use [1] for chunk 1, [2] for chunk 2, etc.
   - Every sentence with factual information MUST have a citation
   - ONLY cite chunks you actually use
   - Example: "Common side effects include nausea [1] and headache [2]."

3. **Refusal policy - refuse to answer:**
   - Medical advice (dosing, diagnosis, treatment recommendations)
   - Drug comparisons or recommendations  
   - Questions about combining medications
   - Pregnancy or pediatric questions without clear context

4. **Be precise and factual**
   - Use exact terminology from the documents
   - Include specific details (dosages, percentages, warnings)
   - Maintain medical accuracy
   - Focus on the most relevant information from high-scoring chunks

Remember: Your role is to retrieve and cite information, NOT to provide medical advice. Use the most relevant chunks provided."""



# ============================================================================
# SYSTEM INITIALIZATION - VECTOR-ONLY
# ============================================================================

def initialize_system():
    """
    Initialize all components: VECTOR RETRIEVAL ONLY + OpenAI generation.
    
    Returns:
        tuple: (vector_store, openai_llm)
    """
    print("="*80)
    print("INITIALIZING RAG SYSTEM FOR EVALUATION (Vector-Only)")
    print("="*80)
    
    # Check API key first
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        raise ValueError("OPENAI_API_KEY not found in .env file!")
    
    # Load vector store ONLY (no BM25, no hybrid!)
    print(f"\n📦 Loading Vector Store...")
    vector_store = VectorStore(
        persist_directory="data/chromadb",
        embedding_model_name="all-MiniLM-L6-v2"
    )
    vector_store.load_chunks("data/processed/chunks.json")
    vector_store.create_or_load_collection()
    
    # Initialize LLM generator with OpenAI
    print(f"\n🤖 Initializing LLM Generator (OpenAI {GENERATION_MODEL})...")
    openai_llm = ChatOpenAI(
        model=GENERATION_MODEL,
        api_key=openai_key,
        temperature=0.0,
        max_tokens=500
    )
    
    print(f"\n✅ All components initialized successfully")
    print(f"   Retrieval: Vector-Only (proven 100% accuracy)")
    print(f"   Generation: OpenAI {GENERATION_MODEL}")
    print(f"   Evaluation: OpenAI {EVALUATOR_MODEL}")
    
    return vector_store, openai_llm


# ============================================================================
# TEST QUERY LOADING
# ============================================================================

def load_test_queries(queries_path: str = "data/evaluation/test_queries.json") -> List[Dict]:
    """Load test queries from JSON file."""
    print(f"\n📋 Loading test queries from {queries_path}...")
    
    with open(queries_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    queries = data.get("queries", [])
    print(f"✅ Loaded {len(queries)} test queries")
    
    return queries


# ============================================================================
# RAG PIPELINE - VECTOR-ONLY RETRIEVAL
# ============================================================================

def run_rag_pipeline(
    query_text: str,
    vector_store: VectorStore,
    openai_llm: ChatOpenAI,
    top_k: int = 15  # ← CHANGED from 8 to 15
) -> Dict[str, Any]:
    """Run complete RAG pipeline with VECTOR-ONLY retrieval + reranking."""
    start_time = time.time()
    
    # 1. Retrieve MORE chunks initially (15 instead of 8)
    raw_chunks = vector_store.search(query_text, top_k=top_k)
    
    # 2. RERANK: Apply multi-stage filtering
    # Stage 1: Remove very low scores
    MIN_SCORE = 0.35
    filtered = [c for c in raw_chunks if c.score >= MIN_SCORE]
    
    # Stage 2: Identify primary drug(s) from top 3 chunks
    primary_drugs = set()
    for chunk in filtered[:3]:
        primary_drugs.update(chunk.drug_names)
    
    # Stage 3: Keep only chunks about primary drugs OR with high scores
    final_chunks = []
    for chunk in filtered:
        # Keep if drug matches OR score is very high
        if any(drug in primary_drugs for drug in chunk.drug_names) or chunk.score > 0.55:
            final_chunks.append(chunk)
            if len(final_chunks) >= 8:  # Final context size
                break
    
    # Fallback: if filtering was too aggressive, use top chunks
    if len(final_chunks) < 4:
        final_chunks = raw_chunks[:8]
    
    contexts = [chunk.text for chunk in final_chunks]
    
    # 3. Build prompt (rest stays the same)
    system_prompt = build_system_prompt()
    
    formatted_chunks = []
    for i, chunk in enumerate(final_chunks, 1):
        chunk_text = chunk.text
        if len(chunk_text) > 800:
            chunk_text = chunk_text[:800] + "... [truncated]"
        
        formatted_chunks.append(
            f"[{i}] (Drugs: {', '.join(chunk.drug_names)}, Score: {chunk.score:.3f})\n{chunk_text}"
        )
    
    context_text = "\n\n".join(formatted_chunks)
    
    # ... rest of function stays EXACTLY the same
    user_prompt = f"""CONTEXT DOCUMENTS:

{context_text}

---

QUESTION: {query_text}

Please answer the question using ONLY the information from the context documents above. Remember to cite your sources using [1], [2], [3] format after every claim."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    # 3. Generate answer with OpenAI
    try:
        response = openai_llm.invoke(messages)
        answer_text = response.content
        
        # Extract citations
        citations = re.findall(r'\[(\d+)\]', answer_text)
        cited_chunk_ids = list(set([int(c) for c in citations]))
        
        # Check for refusal - citation-based logic
        explicit_refusals = [
            "i cannot answer this question",
            "cannot answer this question based on",
            "cannot provide this information",
            "insufficient information in the provided",
            "not enough information in the context",
            "outside the scope"
        ]
        has_explicit_refusal = any(phrase in answer_text.lower() for phrase in explicit_refusals)
        
        # Refusal = no citations OR explicit refusal statement
        is_refusal = (len(cited_chunk_ids) == 0) or has_explicit_refusal
        
        latency_ms = (time.time() - start_time) * 1000
        
        return {
            'question': query_text,
            'answer': answer_text,
            'contexts': contexts,
            'chunks_retrieved': len(final_chunks),  # Report final count
            'cited_chunks': len(cited_chunk_ids),
            'is_refusal': is_refusal,
            'latency_ms': latency_ms
        }
        
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return {
            'question': query_text,
            'answer': f"ERROR: {str(e)}",
            'contexts': contexts,
            'chunks_retrieved': len(final_chunks),
            'cited_chunks': 0,
            'is_refusal': True,
            'latency_ms': latency_ms
        }



# ============================================================================
# RAGAS DATASET BUILDING
# ============================================================================

def build_ragas_dataset(
    queries: List[Dict],
    vector_store: VectorStore,
    openai_llm: ChatOpenAI,
    checkpoint_file: Path = None
) -> tuple:
    """
    Build RAGAS-compatible dataset with checkpoint/resume capability.
    
    Args:
        queries: List of query dictionaries
        vector_store: Vector store instance
        openai_llm: OpenAI ChatGPT instance
        checkpoint_file: Optional checkpoint file for resuming
    
    Returns:
        (dataset, metadata)
    """
    print("="*80)
    print("RUNNING RAG PIPELINE ON ALL TEST QUERIES (Vector-Only + OpenAI Generation)")
    print("="*80)
    
    # Check for existing checkpoint
    start_idx = 0
    existing_questions = []
    existing_answers = []
    existing_contexts = []
    existing_metadata = []
    
    if checkpoint_file and checkpoint_file.exists():
        print(f"\n📂 Found checkpoint: {checkpoint_file}")
        with open(checkpoint_file, 'r') as f:
            checkpoint = json.load(f)
        
        start_idx = checkpoint.get("last_completed_idx", -1) + 1
        existing_questions = checkpoint.get("questions", [])
        existing_answers = checkpoint.get("answers", [])
        existing_contexts = checkpoint.get("contexts", [])
        existing_metadata = checkpoint.get("metadata", [])
        
        print(f"✅ Resuming from query {start_idx + 1}/{len(queries)}")
    
    questions = existing_questions.copy()
    answers = existing_answers.copy()
    contexts = existing_contexts.copy()
    ground_truths = [""] * len(existing_questions)  # Empty ground truths
    metadata = existing_metadata.copy()
    
    # Process remaining queries
    for i in range(start_idx, len(queries)):
        query_info = queries[i]
        query_text = query_info["query_text"]
        query_id = query_info["query_id"]
        
        print(f"\n[{i + 1}/{len(queries)}] Processing: {query_id}")
        print(f"   Query: {query_text}")
        
        try:
            # Run RAG pipeline with vector-only retrieval
            result = run_rag_pipeline(query_text, vector_store, openai_llm, top_k=15)
            
            # Store results
            questions.append(result['question'])
            answers.append(result['answer'])
            contexts.append(result['contexts'])
            ground_truths.append("")  # Empty ground truth
            
            metadata.append({
                'query_id': query_id,
                'category': query_info.get('category', 'unknown'),
                'difficulty': query_info.get('difficulty', 'medium'),
                'expected_drug': query_info.get('expected_drug', 'unknown'),
                'chunks_retrieved': result['chunks_retrieved'],
                'cited_chunks': result['cited_chunks'],
                'is_refusal': result['is_refusal'],
                'latency_ms': result['latency_ms']
            })
            
            # Log result
            if result['is_refusal']:
                print(f"   ⚠️  REFUSAL detected (0 citations)")
            else:
                print(f"   ✅ Answer generated ({len(result['answer'])} chars, {result['cited_chunks']} citations)")
            
            # Save checkpoint after each query
            if checkpoint_file:
                checkpoint_data = {
                    'last_completed_idx': i,
                    'questions': questions,
                    'answers': answers,
                    'contexts': contexts,
                    'metadata': metadata,
                    'timestamp': datetime.now().isoformat()
                }
                with open(checkpoint_file, 'w') as f:
                    json.dump(checkpoint_data, f, indent=2)
            
            time.sleep(0.5)  # Rate limiting
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            questions.append(query_text)
            answers.append(f"ERROR: {str(e)}")
            contexts.append([])
            ground_truths.append("")
            metadata.append({
                'query_id': query_id,
                'error': str(e)
            })
    
    # Build final dataset
    dataset_dict = {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths
    }
    
    dataset = Dataset.from_dict(dataset_dict)
    
    print(f"\n✅ Dataset created successfully")
    print(f"   Total samples: {len(dataset)}")
    
    refusal_count = sum(1 for m in metadata if m.get('is_refusal', False))
    print(f"   Refusals detected: {refusal_count}/{len(dataset)}")
    
    return dataset, metadata


# ============================================================================
# RAGAS EVALUATION
# ============================================================================

def run_ragas_evaluation_openai(dataset: Dataset) -> tuple:
    """
    Run RAGAS evaluation using OpenAI API with parallel processing.
    
    Returns:
        (scores, total_cost_usd)
    """
    print("="*80)
    print("RUNNING RAGAS EVALUATION WITH OPENAI")
    print("="*80)
    
    # Check API key
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        raise ValueError("OPENAI_API_KEY not found in .env file!")
    
    print(f"\n⚙️  Initializing OpenAI evaluator...")
    print(f"   Model: {EVALUATOR_MODEL}")
    print(f"   Embeddings: {EMBEDDING_MODEL}")
    print(f"   Max workers: {MAX_WORKERS} (parallel processing)")
    print(f"   Total samples: {len(dataset)}")
    
    # Initialize LLM for evaluation
    evaluator_llm = ChatOpenAI(
        model=EVALUATOR_MODEL,
        api_key=openai_key,
        temperature=0.0,
        timeout=TIMEOUT,
        max_retries=MAX_RETRIES
    )
    
    # Initialize embeddings for evaluation
    evaluator_embeddings = OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        api_key=openai_key
    )
    
    # Configure RAGAS for parallel processing
    run_config = RunConfig(
        max_workers=MAX_WORKERS,
        max_wait=TIMEOUT,
        max_retries=MAX_RETRIES,
        timeout=TIMEOUT
    )
    
    # Define all metrics
    metrics = [faithfulness, answer_relevancy, context_precision]
    
    print(f"\n📊 Metrics: Faithfulness, Answer Relevancy, Context Precision")
    print(f"💰 Estimated total cost: ~$0.06-0.08")
    print(f"⏱️  Estimated time: 5-8 minutes\n")
    
    start_time = time.time()
    
    try:
        # Run evaluation
        results = evaluate(
            dataset=dataset,
            metrics=metrics,
            llm=evaluator_llm,
            embeddings=evaluator_embeddings,
            run_config=run_config
        )
        
        elapsed = time.time() - start_time
        print(f"\n✅ Evaluation complete! ({elapsed/60:.1f} minutes)")
        
        # Extract scores
        scores = {
            'faithfulness': list(results['faithfulness']),
            'answer_relevancy': list(results['answer_relevancy']),
            'context_precision': list(results['context_precision'])
        }
        
        # Estimate cost
        num_queries = len(dataset)
        
        # Generation cost
        gen_input_tokens = 1500 * num_queries
        gen_output_tokens = 500 * num_queries
        gen_cost = (gen_input_tokens / 1_000_000) * COST_PER_1M_INPUT + \
                   (gen_output_tokens / 1_000_000) * COST_PER_1M_OUTPUT
        
        # Evaluation cost
        eval_input_tokens = 3000 * 2.5 * 3 * num_queries
        eval_output_tokens = 1000 * 2.5 * 3 * num_queries
        eval_cost = (eval_input_tokens / 1_000_000) * COST_PER_1M_INPUT + \
                    (eval_output_tokens / 1_000_000) * COST_PER_1M_OUTPUT
        
        total_cost = gen_cost + eval_cost
        
        print(f"\n💰 Estimated Cost:")
        print(f"   Generation: ${gen_cost:.4f}")
        print(f"   Evaluation: ${eval_cost:.4f}")
        print(f"   Total: ${total_cost:.4f}")
        
        return scores, total_cost
        
    except Exception as e:
        print(f"\n❌ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        raise


# ============================================================================
# AGGREGATE METRICS
# ============================================================================

def calculate_aggregate_metrics(scores: Dict[str, List], metadata: List[Dict]) -> Dict:
    """Calculate aggregate statistics from RAGAS scores."""
    print("="*80)
    print("CALCULATING AGGREGATE METRICS")
    print("="*80)
    
    # Filter out NaN values
    faithfulness_scores = [float(s) for s in scores['faithfulness'] 
                          if not (isinstance(s, float) and np.isnan(s))]
    relevancy_scores = [float(s) for s in scores['answer_relevancy'] 
                       if not (isinstance(s, float) and np.isnan(s))]
    precision_scores = [float(s) for s in scores['context_precision'] 
                       if not (isinstance(s, float) and np.isnan(s))]
    
    def safe_stdev(values):
        if len(values) < 1:
            return 0.0
        return float(np.std(values, ddof=1))
    
    def safe_stat(func, values, default=0.0):
        try:
            return float(func(values)) if values else default
        except:
            return default
    
    aggregate = {
        'faithfulness': {
            'mean': safe_stat(statistics.mean, faithfulness_scores),
            'median': safe_stat(statistics.median, faithfulness_scores),
            'min': safe_stat(min, faithfulness_scores),
            'max': safe_stat(max, faithfulness_scores),
            'stdev': safe_stdev(faithfulness_scores),
            'valid_count': len(faithfulness_scores)
        },
        'answer_relevancy': {
            'mean': safe_stat(statistics.mean, relevancy_scores),
            'median': safe_stat(statistics.median, relevancy_scores),
            'min': safe_stat(min, relevancy_scores),
            'max': safe_stat(max, relevancy_scores),
            'stdev': safe_stdev(relevancy_scores),
            'valid_count': len(relevancy_scores)
        },
        'context_precision': {
            'mean': safe_stat(statistics.mean, precision_scores),
            'median': safe_stat(statistics.median, precision_scores),
            'min': safe_stat(min, precision_scores),
            'max': safe_stat(max, precision_scores),
            'stdev': safe_stdev(precision_scores),
            'valid_count': len(precision_scores)
        },
        'overall': {
            'mean': safe_stat(statistics.mean, 
                            faithfulness_scores + relevancy_scores + precision_scores)
        }
    }
    
    return aggregate


# ============================================================================
# SAVE RESULTS
# ============================================================================

def save_results(
    scores: Dict[str, List],
    aggregate: Dict,
    metadata: List[Dict],
    total_cost: float,
    output_dir: str = "data/evaluation"
):
    """Save RAGAS results to JSON files."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().isoformat()
    
    def convert_nan(obj):
        if isinstance(obj, float) and np.isnan(obj):
            return None
        return obj
    
    # Save detailed results
    results_file = output_dir / "ragas_results.json"
    detailed_results = {
        'timestamp': timestamp,
        'retrieval_method': 'vector_only',
        'evaluator': f"RAGAS + OpenAI {EVALUATOR_MODEL}",
        'generator': f"OpenAI {GENERATION_MODEL}",
        'metrics_used': ['faithfulness', 'answer_relevancy', 'context_precision'],
        'num_queries': len(scores['faithfulness']),
        'total_cost_usd': round(total_cost, 4),
        'aggregate_metrics': aggregate,
        'per_query_scores': {
            'faithfulness': [convert_nan(s) for s in scores['faithfulness']],
            'answer_relevancy': [convert_nan(s) for s in scores['answer_relevancy']],
            'context_precision': [convert_nan(s) for s in scores['context_precision']]
        },
        'metadata': metadata
    }
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(detailed_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Results saved to {results_file}")
    
    # Save summary
    summary_file = output_dir / "ragas_summary.json"
    summary = {
        'timestamp': timestamp,
        'retrieval_method': 'vector_only',
        'evaluator_model': EVALUATOR_MODEL,
        'generator_model': GENERATION_MODEL,
        'metrics_used': ['faithfulness', 'answer_relevancy', 'context_precision'],
        'num_queries': len(scores['faithfulness']),
        'total_cost_usd': round(total_cost, 4),
        'aggregate_metrics': aggregate
    }
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Summary saved to {summary_file}")


# ============================================================================
# PRINT RESULTS
# ============================================================================

def print_results(aggregate: Dict, total_cost: float):
    """Print formatted results to console."""
    print("="*80)
    print("RAGAS EVALUATION RESULTS (Vector-Only)")
    print("="*80)
    
    print(f"\n📊 FAITHFULNESS (Does answer stick to retrieved chunks?)")
    print(f"   Mean:   {aggregate['faithfulness']['mean']:.4f}")
    print(f"   Median: {aggregate['faithfulness']['median']:.4f}")
    print(f"   Range:  {aggregate['faithfulness']['min']:.4f} - {aggregate['faithfulness']['max']:.4f}")
    print(f"   StdDev: {aggregate['faithfulness']['stdev']:.4f}")
    print(f"   Valid:  {aggregate['faithfulness']['valid_count']} samples")
    
    print(f"\n📊 ANSWER RELEVANCY (Does answer address the question?)")
    print(f"   Mean:   {aggregate['answer_relevancy']['mean']:.4f}")
    print(f"   Median: {aggregate['answer_relevancy']['median']:.4f}")
    print(f"   Range:  {aggregate['answer_relevancy']['min']:.4f} - {aggregate['answer_relevancy']['max']:.4f}")
    print(f"   StdDev: {aggregate['answer_relevancy']['stdev']:.4f}")
    print(f"   Valid:  {aggregate['answer_relevancy']['valid_count']} samples")
    
    print(f"\n📊 CONTEXT PRECISION (Are retrieved chunks relevant?)")
    print(f"   Mean:   {aggregate['context_precision']['mean']:.4f}")
    print(f"   Median: {aggregate['context_precision']['median']:.4f}")
    print(f"   Range:  {aggregate['context_precision']['min']:.4f} - {aggregate['context_precision']['max']:.4f}")
    print(f"   StdDev: {aggregate['context_precision']['stdev']:.4f}")
    print(f"   Valid:  {aggregate['context_precision']['valid_count']} samples")
    
    print(f"\n🎯 OVERALL SCORE")
    print(f"   Mean across all metrics: {aggregate['overall']['mean']:.4f}")
    
    # Interpretation
    overall_mean = aggregate['overall']['mean']
    if overall_mean >= 0.85:
        grade = "EXCELLENT ✅ Production-ready"
    elif overall_mean >= 0.70:
        grade = "GOOD ✅ Acceptable for MVP"
    elif overall_mean >= 0.60:
        grade = "FAIR ⚠️  Needs improvement"
    else:
        grade = "POOR ❌ Requires redesign"
    
    print(f"   INTERPRETATION: {grade}")
    print(f"\n💰 TOTAL COST: ${total_cost:.4f} (~₹{total_cost * 85:.2f})")
    
    # Actionable insights
    print("\n💡 ACTIONABLE INSIGHTS:")
    if aggregate['faithfulness']['mean'] < 0.70:
        print("   ⚠️  LOW FAITHFULNESS: System is hallucinating. Review generation prompts.")
    elif aggregate['faithfulness']['mean'] >= 0.85:
        print("   ✅ EXCELLENT FAITHFULNESS: Minimal hallucination detected.")
    
    if aggregate['answer_relevancy']['mean'] < 0.70:
        print("   ⚠️  LOW RELEVANCY: Answers don't address questions well. Review prompts.")
    elif aggregate['answer_relevancy']['mean'] >= 0.85:
        print("   ✅ EXCELLENT RELEVANCY: Answers are highly relevant to questions.")
    
    if aggregate['context_precision']['mean'] < 0.60:
        print("   ⚠️  LOW CONTEXT PRECISION: Retrieval needs tuning.")
    elif aggregate['context_precision']['mean'] >= 0.75:
        print("   ✅ EXCELLENT PRECISION: Retrieval is highly relevant.")
    
    print("="*80)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function for RAGAS evaluation."""
    try:
        # Step 1: Initialize system (VECTOR-ONLY)
        vector_store, openai_llm = initialize_system()
        
        # Step 2: Load test queries
        queries = load_test_queries("data/evaluation/test_queries.json")
        
        # Step 3: Build RAGAS dataset with checkpoint support
        checkpoint_file = Path("data/evaluation/ragas_checkpoint.json")
        dataset, metadata = build_ragas_dataset(
            queries, vector_store, openai_llm, checkpoint_file=checkpoint_file
        )
        
        # Step 4: Run RAGAS evaluation with OpenAI
        scores, total_cost = run_ragas_evaluation_openai(dataset)
        
        # Step 5: Calculate aggregate metrics
        aggregate = calculate_aggregate_metrics(scores, metadata)
        
        # Step 6: Save results
        save_results(scores, aggregate, metadata, total_cost)
        
        # Step 7: Print results
        print_results(aggregate, total_cost)
        
        # Step 8: Cleanup checkpoint
        if checkpoint_file.exists():
            checkpoint_file.unlink()
            print(f"\n🗑️  Checkpoint file removed: {checkpoint_file}")
        
        print("="*80)
        print("✅ RAGAS EVALUATION COMPLETE!")
        print("="*80)
        print(f"\n📊 VECTOR-ONLY EVALUATION")
        print(f"   Generation: {GENERATION_MODEL}")
        print(f"   Evaluation: {EVALUATOR_MODEL}")
        print(f"\n💾 Results saved to:")
        print(f"   - data/evaluation/ragas_results_vector_only.json (detailed)")
        print(f"   - data/evaluation/ragas_summary_vector_only.json (summary)")
        print(f"\n💰 Total cost: ${total_cost:.4f} (~₹{total_cost * 85:.2f})")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
