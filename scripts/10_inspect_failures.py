# Save as scripts/10_inspect_failures.py

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.retrieval.vector_store import VectorStore
from src.retrieval.bm25_index import BM25Index
from src.retrieval.hybrid_retriever import HybridRetriever

# Initialize
vector_store = VectorStore(
    persist_directory="data/chromadb",
    embedding_model_name="all-MiniLM-L6-v2"
)
vector_store.load_chunks("data/processed/chunks.json")
vector_store.create_or_load_collection()

bm25_index = BM25Index.load_from_disk("data/bm25_index.pkl")
hybrid = HybridRetriever(vector_store, bm25_index)

# Test 3 failed queries
failed_queries = [
    "What side effects should I watch for when taking metformin?",
    "Can I take ibuprofen with lisinopril?",
    "What is the maximum daily dose of paracetamol for adults?"
]

for query in failed_queries:
    print("\n" + "="*80)
    print(f"QUERY: {query}")
    print("="*80)
    
    chunks = hybrid.retrieve_hybrid(query, top_k=5)
    
    print(f"\nRetrieved {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks, 1):
        print(f"\n[{i}] Score: {chunk.score:.4f} | Rank: {chunk.rank}")
        print(f"Drugs: {', '.join(chunk.drug_names)}")
        print(f"Authority: {chunk.authority_family} (Tier {chunk.tier})")
        print(f"Retriever: {chunk.retriever_type}")
        print(f"Chunk ID: {chunk.chunk_id}")
        print(f"\nText preview:")
        print(f"{chunk.text[:300]}...")
        print("-" * 80)

print("\n" + "="*80)
print("🔍 ANALYSIS COMPLETE")
print("="*80)
