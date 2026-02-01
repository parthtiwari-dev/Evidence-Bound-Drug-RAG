#!/usr/bin/env python3
"""
Script: 05d_tune_weights.py
Purpose: Test different vector/BM25 weights to find optimal hybrid configuration
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.retrieval.vector_store import VectorStore
from src.retrieval.bm25_index import BM25Index
from src.retrieval.hybrid_retriever import HybridRetriever

# Initialize retrievers (same as 05a_test_retrieval.py)
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

# Test queries
test_queries = [
    {"text": "What are the side effects of warfarin?", "drug": "warfarin"},
    {"text": "What is the recommended dosage of atorvastatin?", "drug": "atorvastatin"},
    {"text": "What are the contraindications for amoxicillin?", "drug": "amoxicillin"},
    {"text": "How does metformin work?", "drug": "metformin"},
    {"text": "What drugs interact with lisinopril?", "drug": "lisinopril"}
]

# Weights to test
weights_to_test = [
    {"vector_weight": 0.5, "name": "50/50 (Baseline)"},
    {"vector_weight": 0.6, "name": "60/40"},
    {"vector_weight": 0.7, "name": "70/30"},
    {"vector_weight": 0.8, "name": "80/20"}
]

print("\n" + "="*80)
print("WEIGHT TUNING EXPERIMENT")
print("="*80)

results = {}

for weight_config in weights_to_test:
    weight = weight_config["vector_weight"]
    name = weight_config["name"]
    
    print(f"\n{'='*80}")
    print(f"TESTING: {name}")
    print(f"{'='*80}")
    
    results[name] = {"weight": weight, "queries": []}
    
    for query in test_queries:
        query_text = query["text"]
        expected_drug = query["drug"]
        
        print(f"\nQuery: \"{query_text}\"")
        print(f"Expected: {expected_drug}")
        print("-" * 80)
        
        hybrid_results = hybrid.retrieve_hybrid(query_text, top_k=5, vector_weight=weight)
        
        correct_count = 0
        print(f"Top-5:")
        for i, result in enumerate(hybrid_results, 1):
            chunk_drug = result.drug_names[0] if result.drug_names else 'unknown'
            is_correct = expected_drug in result.drug_names
            correct_count += is_correct
            indicator = "✅" if is_correct else "❌"
            print(f"  {i}. {chunk_drug:15} (score: {result.score:.4f}) {indicator}")
        
        accuracy = correct_count / 5
        print(f"Accuracy: {correct_count}/5 ({accuracy*100:.0f}%)")
        
        results[name]["queries"].append({
            "query": query_text,
            "accuracy": accuracy,
            "correct_count": correct_count
        })

# Summary
print(f"\n\n{'='*80}")
print("SUMMARY")
print(f"{'='*80}\n")

print(f"{'Weight':<25} {'Avg Accuracy':<15} {'Total Correct':<15}")
print("-" * 80)

best_name = None
best_accuracy = 0

for name, data in results.items():
    avg_accuracy = sum(q["accuracy"] for q in data["queries"]) / len(data["queries"])
    total_correct = sum(q["correct_count"] for q in data["queries"])
    total_possible = len(data["queries"]) * 5
    
    print(f"{name:<25} {avg_accuracy*100:>6.1f}%        {total_correct}/{total_possible}")
    
    if avg_accuracy > best_accuracy:
        best_accuracy = avg_accuracy
        best_name = name

print(f"\n🏆 BEST: {best_name} with {best_accuracy*100:.1f}% accuracy")
print(f"\nRecommendation: Use vector_weight={results[best_name]['weight']} for production")
