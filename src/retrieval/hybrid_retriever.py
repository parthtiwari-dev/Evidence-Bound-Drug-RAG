"""
Hybrid Retrieval Orchestrator for Evidence-Bound Drug RAG
Combines vector search (semantic) and BM25 search (lexical) with weighted averaging
"""

from typing import List, Optional
from collections import defaultdict

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.models.schemas import RetrievedChunk
from src.retrieval.vector_store import VectorStore
from src.retrieval.bm25_index import BM25Index


class HybridRetriever:
    """
    Hybrid retrieval system combining vector search and BM25.
    
    Features:
    - Tunable weights (default 50/50 vector/BM25)
    - Score normalization before merging
    - Deduplication of overlapping results
    - 2× over-retrieval for better merge quality
    """
    
    def __init__(self, vector_store: VectorStore, bm25_index: BM25Index):
        """
        Initialize hybrid retriever with both search backends.
        
        Args:
            vector_store: VectorStore instance (from Task 3)
            bm25_index: BM25Index instance (from Task 4)
        """
        self.vector_store = vector_store
        self.bm25_index = bm25_index
        
        print("✅ HybridRetriever initialized")
        print(f"   Vector store: {self.vector_store.get_chunk_count()} chunks")
        print(f"   BM25 index: {self.bm25_index.get_corpus_size()} chunks")
    
    def retrieve_vector(self, query: str, top_k: int = 10) -> List[RetrievedChunk]:
        """
        Retrieve using vector search only.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of RetrievedChunk objects from vector search
        """
        return self.vector_store.search(query, top_k=top_k)
    
    def retrieve_bm25(self, query: str, top_k: int = 10) -> List[RetrievedChunk]:
        """
        Retrieve using BM25 search only.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of RetrievedChunk objects from BM25 search
        """
        return self.bm25_index.search(query, top_k=top_k)
    
    def retrieve_hybrid(
        self,
        query: str,
        top_k: int = 10,
        vector_weight: float = 0.5
    ) -> List[RetrievedChunk]:
        """
        Retrieve using hybrid search (vector + BM25).
        
        Strategy:
        1. Retrieve 2×top_k from each retriever (better merge quality)
        2. Normalize scores to [0, 1]
        3. Merge with weighted averaging:
           - Both retrievers: weighted_average
           - Single retriever: keep full score (no penalty)
        4. Sort by final score and return top_k
        
        Args:
            query: Search query
            top_k: Number of results to return
            vector_weight: Weight for vector scores (0-1), default 0.5 (50/50)
            
        Returns:
            List of RetrievedChunk objects with hybrid scores
        """
        if not query or not query.strip():
            print("⚠️  Empty query provided, returning empty results")
            return []
        
        # Retrieve 2× results from each retriever (Correction #4)
        retrieval_depth = top_k * 2
        vector_results = self.retrieve_vector(query, top_k=retrieval_depth)
        bm25_results = self.retrieve_bm25(query, top_k=retrieval_depth)
        
        # Handle edge cases
        if not vector_results and not bm25_results:
            return []
        if not vector_results:
            return bm25_results[:top_k]
        if not bm25_results:
            return vector_results[:top_k]
        
        # Normalize scores (Correction #3)
        vector_results = self._normalize_scores(vector_results)
        bm25_results = self._normalize_scores(bm25_results)
        
        # Merge and rerank (Correction #2)
        hybrid_results = self._merge_and_rerank(
            vector_results,
            bm25_results,
            vector_weight,
            top_k
        )
        
        return hybrid_results
    
    def _normalize_scores(self, chunks: List[RetrievedChunk]) -> List[RetrievedChunk]:
        """
        Normalize scores to [0, 1] range using min-max scaling.
        
        Correction #3: Active normalization (not a no-op).
        Ensures both retrievers use same scale before merging.
        
        Args:
            chunks: List of RetrievedChunk objects
            
        Returns:
            List of RetrievedChunk objects with normalized scores
        """
        if not chunks:
            return chunks
        
        scores = [c.score for c in chunks]
        min_score = min(scores)
        max_score = max(scores)
        
        # Handle edge case: all scores identical
        if max_score == min_score:
            for chunk in chunks:
                chunk.score = 1.0
            return chunks
        
        # Min-max normalization
        for chunk in chunks:
            chunk.score = (chunk.score - min_score) / (max_score - min_score)
        
        return chunks
    
    def _merge_and_rerank(
        self,
        vector_results: List[RetrievedChunk],
        bm25_results: List[RetrievedChunk],
        vector_weight: float,
        top_k: int
    ) -> List[RetrievedChunk]:
        """
        Merge results from both retrievers and rerank by weighted score.
        
        Correction #2: Don't penalize single-retriever results.
        - Both retrievers: weighted_average
        - Vector only: keep full vector_score
        - BM25 only: keep full bm25_score
        
        Args:
            vector_results: Results from vector search
            bm25_results: Results from BM25 search
            vector_weight: Weight for vector scores (0-1)
            top_k: Number of results to return
            
        Returns:
            List of RetrievedChunk objects with hybrid scores, sorted by score
        """
        # Build merged dictionary
        merged = {}
        
        # Add vector results
        for chunk in vector_results:
            merged[chunk.chunk_id] = {
                'vector_score': chunk.score,
                'bm25_score': None,
                'chunk': chunk
            }
        
        # Add BM25 results (and mark overlaps)
        for chunk in bm25_results:
            if chunk.chunk_id in merged:
                # Overlap: chunk found by both retrievers
                merged[chunk.chunk_id]['bm25_score'] = chunk.score
            else:
                # BM25 only
                merged[chunk.chunk_id] = {
                    'vector_score': None,
                    'bm25_score': chunk.score,
                    'chunk': chunk
                }
        
        # Calculate final scores (Correction #2: no penalty for single-retriever)
        final_results = []
        
        for chunk_id, data in merged.items():
            v_score = data['vector_score']
            b_score = data['bm25_score']
            chunk = data['chunk']
            
            if v_score is not None and b_score is not None:
                # Both retrievers found it: weighted average
                final_score = (vector_weight * v_score) + ((1 - vector_weight) * b_score)
            elif v_score is not None:
                # Vector only: keep full vector score (no penalty)
                final_score = v_score
            else:
                # BM25 only: keep full BM25 score (no penalty)
                final_score = b_score
            
            # Create new RetrievedChunk with hybrid score
            hybrid_chunk = RetrievedChunk(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                text=chunk.text,
                score=final_score,
                rank=0,  # Will be reassigned after sorting
                retriever_type="hybrid",  # Mark as hybrid result
                authority_family=chunk.authority_family,
                tier=chunk.tier,
                year=chunk.year,
                drug_names=chunk.drug_names
            )
            final_results.append(hybrid_chunk)
        
        # Sort by final score (descending) and take top_k
        final_results.sort(key=lambda x: x.score, reverse=True)
        final_results = final_results[:top_k]
        
        # Reassign ranks
        for rank, chunk in enumerate(final_results, start=1):
            chunk.rank = rank
        
        return final_results


# Example usage and comparison testing
if __name__ == "__main__":
    from src.retrieval.vector_store import VectorStore
    from src.retrieval.bm25_index import BM25Index
    
    print("="*80)
    print("INITIALIZING HYBRID RETRIEVER")
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
    print("\n" + "="*80)
    print("TESTING HYBRID RETRIEVAL")
    print("="*80)
    
    test_queries = [
        "warfarin side effects",
        "aspirin contraindications",
        ""
    ]
    
    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"📝 Query: '{query}'")
        print(f"{'='*80}")
        
        if not query:
            print("   (Empty query test)")
        
        # Retrieve from all three methods
        vector_results = hybrid.retrieve_vector(query, top_k=5)
        bm25_results = hybrid.retrieve_bm25(query, top_k=5)
        hybrid_results = hybrid.retrieve_hybrid(query, top_k=5, vector_weight=0.5)
        
        # Display results
        print(f"\n🔵 VECTOR (top-5):")
        if vector_results:
            for r in vector_results:
                print(f"   [{r.rank}] Score: {r.score:.4f} | {r.document_id[:30]}")
        else:
            print("   No results")
        
        print(f"\n🟢 BM25 (top-5):")
        if bm25_results:
            for r in bm25_results:
                print(f"   [{r.rank}] Score: {r.score:.4f} | {r.document_id[:30]}")
        else:
            print("   No results")
        
        print(f"\n🟣 HYBRID (50/50, top-5):")
        if hybrid_results:
            for r in hybrid_results:
                print(f"   [{r.rank}] Score: {r.score:.4f} | {r.document_id[:30]}")
        else:
            print("   No results")
        
        # Analyze overlap
        if hybrid_results:
            vector_ids = {r.chunk_id for r in vector_results}
            bm25_ids = {r.chunk_id for r in bm25_results}
            hybrid_ids = {r.chunk_id for r in hybrid_results}
            
            overlap = vector_ids & bm25_ids
            print(f"\n📊 Overlap Analysis:")
            print(f"   Vector ∩ BM25: {len(overlap)} chunks")
            print(f"   Hybrid unique sources:")
            print(f"      From vector only: {len(hybrid_ids & vector_ids - bm25_ids)}")
            print(f"      From BM25 only: {len(hybrid_ids & bm25_ids - vector_ids)}")
            print(f"      From both: {len(hybrid_ids & overlap)}")
    
    print(f"\n{'='*80}")
    print("✅ Hybrid retrieval testing complete")
    print(f"{'='*80}")
