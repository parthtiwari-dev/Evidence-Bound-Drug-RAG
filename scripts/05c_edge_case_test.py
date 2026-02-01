#!/usr/bin/env python3
"""
Script: 05c_edge_case_test.py
Purpose: Test edge cases (out-of-corpus drug, ambiguous terms)
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.retrieval.vector_store import VectorStore
from src.retrieval.bm25_index import BM25Index
from src.retrieval.hybrid_retriever import HybridRetriever

# Initialize retrievers
print("="*80)
print("INITIALIZING RETRIEVERS")
print("="*80)

print("\n📦 Loading Vector Store...")
vector_store = VectorStore(
    persist_directory="data/chromadb",
    embedding_model_name="all-MiniLM-L6-v2"
)
vector_store.load_chunks("data/processed/chunks.json")
vector_store.create_or_load_collection()

print("\n📦 Loading BM25 Index...")
bm25_index = BM25Index.load_from_disk("data/bm25_index.pkl")

print("\n🔗 Initializing Hybrid Retriever...")
hybrid = HybridRetriever(vector_store, bm25_index)

# Edge case queries
edge_cases = [
    {
        "query": "aspirin side effects",
        "expected": "Out-of-corpus (aspirin not in locked 8 drugs)",
        "behavior": "Should return low scores or related drugs (warfarin mentions aspirin)"
    },
    {
        "query": "blood thinner",
        "expected": "Ambiguous generic term for warfarin",
        "behavior": "Should find warfarin (semantic understanding)"
    }
]

print("\n" + "="*80)
print("EDGE CASE TESTING")
print("="*80)

for i, edge_case in enumerate(edge_cases, 1):
    print(f"\n{'='*80}")
    print(f"EDGE CASE {i}: {edge_case['query']}")
    print(f"{'='*80}")
    print(f"Expected: {edge_case['expected']}")
    print(f"Behavior: {edge_case['behavior']}")
    print("-" * 80)
    
    results = hybrid.retrieve_hybrid(edge_case['query'], top_k=5, vector_weight=0.7)
    
    print(f"\nTop-5 Results:")
    for j, result in enumerate(results, 1):
        chunk_id = result.chunk_id
        doc_id = result.document_id
        drug = result.drug_names[0] if result.drug_names else 'unknown'
        score = result.score
        
        print(f"  {j}. Drug: {drug:15} | Score: {score:.4f}")
        print(f"     Doc: {doc_id}")
        print(f"     Chunk: {chunk_id}")
    
    # Analysis
    print(f"\nAnalysis:")
    top_drug = results[0].drug_names[0] if results[0].drug_names else 'unknown'
    top_score = results[0].score
    
    if edge_case['query'] == "aspirin side effects":
        if top_score < 0.5:
            print(f"  ✅ PASS: Low scores ({top_score:.4f}) indicate out-of-corpus")
        else:
            print(f"  ⚠️  WARNING: High score ({top_score:.4f}) - may have aspirin mentions")
    
    elif edge_case['query'] == "blood thinner":
        if top_drug == "warfarin":
            print(f"  ✅ PASS: Correctly identified warfarin as blood thinner")
        else:
            print(f"  ❌ FAIL: Did not identify warfarin (got {top_drug})")

print(f"\n\n{'='*80}")
print("EDGE CASE TEST COMPLETE")
print(f"{'='*80}")
