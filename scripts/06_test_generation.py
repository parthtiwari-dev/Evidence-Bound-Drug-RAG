"""
Test LLM generation with 5 queries covering different scenarios.

Tests:
1. Answerable - Direct factual (side effects)
2. Answerable - Contraindications
3. UNANSWERABLE - Medical advice (should refuse)
4. Answerable - Drug interactions
5. Answerable - Mechanism of action (conceptual)
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.retrieval.hybrid_retriever import HybridRetriever
from src.generation.llm import LLMGenerator


def print_divider(char="=", length=80):
    """Print a divider line"""
    print(char * length)


def print_result(query_num: int, query: str, result, chunks):
    """Print formatted result for a query"""
    print_divider()
    print(f"QUERY {query_num}: {query}")
    print_divider()
    
    print(f"\n📄 RETRIEVED CHUNKS: {len(chunks)}")
    for i, chunk in enumerate(chunks[:3], 1):  # Show top 3
        print(f"\n[{i}] {chunk.chunk_id}")
        print(f"    Score: {chunk.score:.3f} | {chunk.authority_family} Tier {chunk.tier}")
        print(f"    Preview: {chunk.text[:150]}...")
    
    print(f"\n\n📝 GENERATED ANSWER:")
    print(f"{result.answer_text}")
    
    print(f"\n\n📊 METADATA:")
    print(f"   - Cited chunks: {result.cited_chunk_ids}")
    print(f"   - Authorities used: {result.authorities_used}")
    print(f"   - Is refusal: {result.is_refusal}")
    print(f"   - Total tokens: {result.total_token_count}")
    print(f"   - Latency: {result.latency_ms:.2f}ms")
    print(f"   - Cost: ${result.cost_usd:.6f}")
    
    # Validation check
    if result.cited_chunk_ids:
        print(f"   ✅ Citations present")
    else:
        print(f"   ⚠️  No citations found")
    
    if result.is_refusal:
        print(f"   ✅ Proper refusal detected")
    
    print()

def main():
    """Run test queries through complete RAG pipeline"""
    
    print_divider("=")
    print("DAY 8 - GENERATION TESTING")
    print("Testing 5 queries with retrieval + generation pipeline")
    print_divider("=")
    
    # Initialize retriever and generator
    print("\n🔧 Initializing components...")
    
    # Import the stores
    from src.retrieval.vector_store import VectorStore
    from src.retrieval.bm25_index import BM25Index
    
        # Initialize retriever and generator
    print("\n🔧 Initializing components...")
    
    # Import the stores
    from src.retrieval.vector_store import VectorStore
    from src.retrieval.bm25_index import BM25Index
    
    # Initialize vector store
    print("   Loading VectorStore...")
    vector_store = VectorStore()
    vector_store.create_or_load_collection()
    
    # Initialize BM25 index
    print("   Loading BM25Index...")
    bm25_index = BM25Index()
    bm25_index.load_chunks("data/processed/chunks.json") 
    bm25_index.build_index()  # ← CHANGED from load_index()
    
    # Initialize hybrid retriever with both stores
    print("   Initializing HybridRetriever...")
    retriever = HybridRetriever(
        vector_store=vector_store,
        bm25_index=bm25_index
    )
    
    # Initialize LLM generator
    print("   Initializing LLMGenerator...")
    generator = LLMGenerator()
    
    print("✅ Components ready!\n")

    
    # Test queries
    test_queries = [
        {
            "id": "q1_side_effects",
            "query": "What are the side effects of warfarin?",
            "expected": "answerable_direct",
            "description": "Direct factual lookup from documentation"
        },
        {
            "id": "q2_contraindications",
            "query": "What are the contraindications for atorvastatin?",
            "expected": "answerable_direct",
            "description": "Contraindication information"
        },
        {
            "id": "q3_medical_advice",
            "query": "What's the best medication for high blood pressure?",
            "expected": "refusal",
            "description": "Medical advice - should refuse per refusal policy"
        },
        {
            "id": "q4_interactions",
            "query": "What drugs interact with lisinopril?",
            "expected": "answerable_direct",
            "description": "Drug interaction information"
        },
        {
            "id": "q5_mechanism",
            "query": "How does atorvastatin lower cholesterol?",
            "expected": "answerable_conceptual",
            "description": "Mechanism of action (conceptual)"
        }
    ]
    
    # Track overall stats
    total_cost = 0.0
    total_latency = 0.0
    total_tokens = 0
    results_summary = []
    
    # Run each test query
        # Run each test query
    for i, test in enumerate(test_queries, 1):
        query = test["query"]
        question_id = test["id"]
        
        try:
            # 1. Retrieve chunks
            # Use hybrid by default (you can change to "vector" or "bm25")
            retriever_type = "hybrid"
            
            if retriever_type == "vector":
                chunks = retriever.retrieve_vector(query, top_k=5)
            elif retriever_type == "bm25":
                chunks = retriever.retrieve_bm25(query, top_k=5)
            else:  # hybrid
                chunks = retriever.retrieve_hybrid(query, top_k=5)
            
            # 2. Generate answer
            result = generator.generate_answer(
                query=query,
                chunks=chunks,
                question_id=question_id
            )
                        
            # 3. Print result
            print_result(i, query, result, chunks)
            
            # 4. Track stats
            total_cost += result.cost_usd
            total_latency += result.latency_ms
            total_tokens += result.total_token_count
            
            # 5. Validate against expectation
            validation_status = "✅"
            if test["expected"] == "refusal" and not result.is_refusal:
                validation_status = "⚠️  EXPECTED REFUSAL"
            elif test["expected"] == "refusal" and result.is_refusal:
                validation_status = "✅ CORRECT REFUSAL"
            elif result.cited_chunk_ids:
                validation_status = "✅ CITED ANSWER"
            else:
                validation_status = "⚠️  NO CITATIONS"
            
            results_summary.append({
                "query_num": i,
                "query": query[:50] + "...",
                "expected": test["expected"],
                "is_refusal": result.is_refusal,
                "has_citations": len(result.cited_chunk_ids) > 0,
                "validation": validation_status,
                "latency_ms": result.latency_ms,
                "tokens": result.total_token_count
            })
            
        except Exception as e:
            print(f"❌ ERROR on query {i}: {e}")
            import traceback
            traceback.print_exc()
            
            results_summary.append({
                "query_num": i,
                "query": query[:50] + "...",
                "expected": test["expected"],
                "is_refusal": False,
                "has_citations": False,
                "validation": f"❌ ERROR: {str(e)[:30]}",
                "latency_ms": 0,
                "tokens": 0
            })
    
    # Print summary
    print_divider("=")
    print("SUMMARY - ALL TEST RESULTS")
    print_divider("=")
    
    print(f"\n📊 OVERALL STATS:")
    print(f"   - Total queries: {len(test_queries)}")
    print(f"   - Total tokens: {total_tokens:,}")
    print(f"   - Total cost: ${total_cost:.6f}")
    print(f"   - Average latency: {total_latency / len(test_queries):.2f}ms")
    
    print(f"\n📋 RESULTS TABLE:")
    print(f"\n{'#':<3} {'Expected':<20} {'Validation':<25} {'Latency':<12} {'Tokens':<8}")
    print("-" * 80)
    
    for r in results_summary:
        print(f"{r['query_num']:<3} {r['expected']:<20} {r['validation']:<25} {r['latency_ms']:<12.1f} {r['tokens']:<8}")
    
    print_divider("=")
    print("✅ DAY 8 TESTING COMPLETE!")
    print(f"📁 Full logs: logs/api/generation_log.jsonl")
    print_divider("=")



if __name__ == "__main__":
    main()
