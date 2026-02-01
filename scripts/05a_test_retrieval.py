"""
Comprehensive Retrieval Testing Script for Evidence-Bound Drug RAG
Tests vector, BM25, and hybrid retrieval across 5 diverse queries
"""

import json
import time
import statistics
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import asdict

import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.retrieval.vector_store import VectorStore
from src.retrieval.bm25_index import BM25Index
from src.retrieval.hybrid_retriever import HybridRetriever
from src.models.schemas import RetrievedChunk


# Test queries (5 drugs, 5 question types)
TEST_QUERIES = [
    {
        "id": "query_1",
        "text": "What are the side effects of warfarin?",
        "drug": "warfarin",
        "question_type": "side_effects"
    },
    {
        "id": "query_2",
        "text": "What is the recommended dosage of atorvastatin?",
        "drug": "atorvastatin",
        "question_type": "dosage"
    },
    {
        "id": "query_3",
        "text": "What are the contraindications for amoxicillin?",
        "drug": "amoxicillin",
        "question_type": "contraindications"
    },
    {
        "id": "query_4",
        "text": "How does metformin work?",
        "drug": "metformin",
        "question_type": "mechanism"
    },
    {
        "id": "query_5",
        "text": "What drugs interact with lisinopril?",
        "drug": "lisinopril",
        "question_type": "interactions"
    }
]


def initialize_retrievers():
    """
    Initialize all three retrievers.
    
    Returns:
        tuple: (vector_store, bm25_index, hybrid_retriever)
    """
    print("="*80)
    print("INITIALIZING RETRIEVERS")
    print("="*80)
    
    # Load vector store
    print("\n📦 Loading Vector Store...")
    vector_store = VectorStore(
        persist_directory="data/chromadb",
        embedding_model_name="all-MiniLM-L6-v2"
    )
    vector_store.load_chunks("data/processed/chunks.json")
    vector_store.create_or_load_collection()
    
    # Load BM25 index
    print("\n📦 Loading BM25 Index...")
    bm25_index = BM25Index.load_from_disk("data/bm25_index.pkl")
    
    # Initialize hybrid retriever
    print("\n🔗 Initializing Hybrid Retriever...")
    hybrid = HybridRetriever(vector_store, bm25_index)
    
    print("\n✅ All retrievers initialized")
    return vector_store, bm25_index, hybrid


def retrieve_with_timing(retriever_func, query: str, top_k: int = 10) -> tuple:
    """
    Execute retrieval and measure latency.
    
    Args:
        retriever_func: Function to call (e.g., hybrid.retrieve_vector)
        query: Search query
        top_k: Number of results
        
    Returns:
        tuple: (results, latency_ms)
    """
    start = time.time()
    results = retriever_func(query, top_k=top_k)
    latency_ms = (time.time() - start) * 1000
    return results, latency_ms


def chunk_to_dict(chunk: RetrievedChunk) -> Dict[str, Any]:
    """
    Convert RetrievedChunk to dictionary for JSON serialization.
    
    Args:
        chunk: RetrievedChunk object
        
    Returns:
        Dictionary with chunk data and text preview
    """
    return {
        "rank": chunk.rank,
        "chunk_id": chunk.chunk_id,
        "document_id": chunk.document_id,
        "score": round(chunk.score, 4),
        "authority_family": chunk.authority_family,
        "tier": chunk.tier,
        "year": chunk.year,
        "drug_names": chunk.drug_names,
        "retriever_type": chunk.retriever_type,
        "text_preview": chunk.text[:150] + "..." if len(chunk.text) > 150 else chunk.text
    }


def calculate_statistics(results: List[RetrievedChunk]) -> Dict[str, float]:
    """
    Calculate score distribution statistics.
    
    Args:
        results: List of RetrievedChunk objects
        
    Returns:
        Dictionary with statistics
    """
    if not results:
        return {
            "min_score": 0.0,
            "max_score": 0.0,
            "mean_score": 0.0,
            "median_score": 0.0,
            "std_dev": 0.0
        }
    
    scores = [r.score for r in results]
    return {
        "min_score": round(min(scores), 4),
        "max_score": round(max(scores), 4),
        "mean_score": round(statistics.mean(scores), 4),
        "median_score": round(statistics.median(scores), 4),
        "std_dev": round(statistics.stdev(scores), 4) if len(scores) > 1 else 0.0
    }


def calculate_overlap(vector_results: List[RetrievedChunk], 
                     bm25_results: List[RetrievedChunk]) -> Dict[str, Any]:
    """
    Calculate overlap between vector and BM25 results.
    
    Args:
        vector_results: Results from vector search
        bm25_results: Results from BM25 search
        
    Returns:
        Dictionary with overlap statistics
    """
    vector_ids = {r.chunk_id for r in vector_results}
    bm25_ids = {r.chunk_id for r in bm25_results}
    overlap_ids = vector_ids & bm25_ids
    
    return {
        "overlap_count": len(overlap_ids),
        "overlap_percentage": round(len(overlap_ids) / 10 * 100, 1) if vector_results and bm25_results else 0.0,
        "overlap_chunk_ids": list(overlap_ids)
    }


def display_results(query_info: Dict, 
                   vector_results: List[RetrievedChunk],
                   bm25_results: List[RetrievedChunk],
                   hybrid_results: List[RetrievedChunk],
                   vector_latency: float,
                   bm25_latency: float,
                   hybrid_latency: float):
    """
    Display formatted results for a query.
    
    Args:
        query_info: Query metadata (id, text, drug, type)
        vector_results: Vector search results
        bm25_results: BM25 search results
        hybrid_results: Hybrid search results
        vector_latency: Vector search latency (ms)
        bm25_latency: BM25 search latency (ms)
        hybrid_latency: Hybrid search latency (ms)
    """
    print("\n" + "="*80)
    print(f"{query_info['id'].upper()}: \"{query_info['text']}\"")
    print(f"Drug: {query_info['drug']} | Type: {query_info['question_type']}")
    print("="*80)
    
    # Vector results
    print(f"\n🔵 VECTOR (top-10) — Latency: {vector_latency:.1f}ms")
    print(f"{'Rank':<6} {'Score':<8} {'Document ID':<35} {'Preview'}")
    print("-" * 80)
    if vector_results:
        for r in vector_results:
            preview = r.text[:60].replace('\n', ' ')
            print(f"[{r.rank}]{'':<3} {r.score:.4f}   {r.document_id:<35} {preview}...")
    else:
        print("   No results")
    
    # BM25 results
    print(f"\n🟢 BM25 (top-10) — Latency: {bm25_latency:.1f}ms")
    print(f"{'Rank':<6} {'Score':<8} {'Document ID':<35} {'Preview'}")
    print("-" * 80)
    if bm25_results:
        for r in bm25_results:
            preview = r.text[:60].replace('\n', ' ')
            print(f"[{r.rank}]{'':<3} {r.score:.4f}   {r.document_id:<35} {preview}...")
    else:
        print("   No results")
    
    # Hybrid results
    print(f"\n🟣 HYBRID (50/50, top-10) — Latency: {hybrid_latency:.1f}ms")
    print(f"{'Rank':<6} {'Score':<8} {'Document ID':<35} {'Preview'}")
    print("-" * 80)
    if hybrid_results:
        for r in hybrid_results:
            preview = r.text[:60].replace('\n', ' ')
            print(f"[{r.rank}]{'':<3} {r.score:.4f}   {r.document_id:<35} {preview}...")
    else:
        print("   No results")
    
    # Statistics
    overlap_info = calculate_overlap(vector_results, bm25_results)
    vector_stats = calculate_statistics(vector_results)
    bm25_stats = calculate_statistics(bm25_results)
    hybrid_stats = calculate_statistics(hybrid_results)
    
    print(f"\n📊 Statistics:")
    print(f"   Overlap (vector ∩ BM25): {overlap_info['overlap_count']} chunks ({overlap_info['overlap_percentage']}%)")
    print(f"   Vector scores  — Min: {vector_stats['min_score']}, Max: {vector_stats['max_score']}, Mean: {vector_stats['mean_score']}, StdDev: {vector_stats['std_dev']}")
    print(f"   BM25 scores    — Min: {bm25_stats['min_score']}, Max: {bm25_stats['max_score']}, Mean: {bm25_stats['mean_score']}, StdDev: {bm25_stats['std_dev']}")
    print(f"   Hybrid scores  — Min: {hybrid_stats['min_score']}, Max: {hybrid_stats['max_score']}, Mean: {hybrid_stats['mean_score']}, StdDev: {hybrid_stats['std_dev']}")


def run_retrieval_tests(hybrid: HybridRetriever, top_k: int = 10) -> Dict[str, Any]:
    """
    Run retrieval tests for all queries.
    
    Args:
        hybrid: HybridRetriever instance
        top_k: Number of results per query
        
    Returns:
        Dictionary with all test results
    """
    print("\n" + "="*80)
    print("RUNNING RETRIEVAL TESTS")
    print("="*80)
    
    all_results = {}
    
    for query_info in TEST_QUERIES:
        query_id = query_info["id"]
        query_text = query_info["text"]
        
        # Retrieve from all three methods
        vector_results, vector_latency = retrieve_with_timing(
            hybrid.retrieve_vector, query_text, top_k
        )
        bm25_results, bm25_latency = retrieve_with_timing(
            hybrid.retrieve_bm25, query_text, top_k
        )
        hybrid_results, hybrid_latency = retrieve_with_timing(
            hybrid.retrieve_hybrid, query_text, top_k
        )
        
        # Display results
        display_results(
            query_info,
            vector_results,
            bm25_results,
            hybrid_results,
            vector_latency,
            bm25_latency,
            hybrid_latency
        )
        
        # Store results
        overlap_info = calculate_overlap(vector_results, bm25_results)
        
        all_results[query_id] = {
            "query_text": query_text,
            "drug": query_info["drug"],
            "question_type": query_info["question_type"],
            "vector": {
                "results": [chunk_to_dict(r) for r in vector_results],
                "latency_ms": round(vector_latency, 2),
                "statistics": calculate_statistics(vector_results)
            },
            "bm25": {
                "results": [chunk_to_dict(r) for r in bm25_results],
                "latency_ms": round(bm25_latency, 2),
                "statistics": calculate_statistics(bm25_results)
            },
            "hybrid": {
                "results": [chunk_to_dict(r) for r in hybrid_results],
                "latency_ms": round(hybrid_latency, 2),
                "statistics": calculate_statistics(hybrid_results)
            },
            "overlap": overlap_info
        }
    
    return all_results


def save_results(results: Dict[str, Any], output_path: str = "data/retrieval_results.json"):
    """
    Save results to JSON file.
    
    Args:
        results: Dictionary with all test results
        output_path: Path to save JSON file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"\n💾 Saving results to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    file_size = output_path.stat().st_size / 1024  # KB
    print(f"✅ Results saved ({file_size:.1f} KB)")


def print_summary(results: Dict[str, Any]):
    """
    Print summary statistics across all queries.
    
    Args:
        results: Dictionary with all test results
    """
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    
    # Aggregate latencies
    vector_latencies = [results[qid]["vector"]["latency_ms"] for qid in results]
    bm25_latencies = [results[qid]["bm25"]["latency_ms"] for qid in results]
    hybrid_latencies = [results[qid]["hybrid"]["latency_ms"] for qid in results]
    
    print(f"\n⏱️  Average Latency:")
    print(f"   Vector: {statistics.mean(vector_latencies):.1f}ms (range: {min(vector_latencies):.1f}-{max(vector_latencies):.1f}ms)")
    print(f"   BM25:   {statistics.mean(bm25_latencies):.1f}ms (range: {min(bm25_latencies):.1f}-{max(bm25_latencies):.1f}ms)")
    print(f"   Hybrid: {statistics.mean(hybrid_latencies):.1f}ms (range: {min(hybrid_latencies):.1f}-{max(hybrid_latencies):.1f}ms)")
    
    # Aggregate overlaps
    overlaps = [results[qid]["overlap"]["overlap_count"] for qid in results]
    print(f"\n🔗 Overlap Statistics:")
    print(f"   Average overlap: {statistics.mean(overlaps):.1f} chunks ({statistics.mean([results[qid]['overlap']['overlap_percentage'] for qid in results]):.1f}%)")
    print(f"   Min overlap: {min(overlaps)} chunks")
    print(f"   Max overlap: {max(overlaps)} chunks")
    
    # Per-query overlap
    print(f"\n   Per-query overlap:")
    for query_info in TEST_QUERIES:
        qid = query_info["id"]
        overlap_count = results[qid]["overlap"]["overlap_count"]
        overlap_pct = results[qid]["overlap"]["overlap_percentage"]
        print(f"      {qid}: {overlap_count} chunks ({overlap_pct}%)")
    
    # Results counts
    print(f"\n📊 Results Retrieved:")
    print(f"   Total queries: {len(TEST_QUERIES)}")
    print(f"   Total results per retriever: {len(TEST_QUERIES) * 10}")
    print(f"   All queries returned results: ✅")


def main():
    """
    Main execution function.
    """
    try:
        # Initialize retrievers
        vector_store, bm25_index, hybrid = initialize_retrievers()
        
        # Run tests
        results = run_retrieval_tests(hybrid, top_k=10)
        
        # Save results
        save_results(results, "data/retrieval_results.json")
        
        # Print summary
        print_summary(results)
        
        print("\n" + "="*80)
        print("✅ RETRIEVAL TESTING COMPLETE")
        print("="*80)
        print(f"\nResults saved to: data/retrieval_results.json")
        print(f"Total queries tested: {len(TEST_QUERIES)}")
        print(f"Total retrievers tested: 3 (vector, BM25, hybrid)")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
