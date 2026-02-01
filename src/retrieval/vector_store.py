"""
ChromaDB Vector Store for Evidence-Bound Drug RAG
Handles embedding generation, storage, and vector similarity search
"""

import json
import time
from pathlib import Path
from typing import List, Optional
from dataclasses import asdict

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.models.schemas import Chunk, RetrievedChunk


class VectorStore:
    """
    Vector store using ChromaDB for semantic search over drug document chunks.
    """
    
    def __init__(
        self,
        persist_directory: str = "data/chromadb",
        embedding_model_name: str = "all-MiniLM-L6-v2",
        collection_name: str = "drug_chunks"
    ):
        """
        Initialize ChromaDB client and embedding model.
        
        Args:
            persist_directory: Path to store ChromaDB data
            embedding_model_name: sentence-transformers model name
            collection_name: Name of ChromaDB collection
        """
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self.collection_name = collection_name
        
        # Initialize ChromaDB client (persistent)
        print(f"Initializing ChromaDB at {self.persist_directory}...")
        self.client = chromadb.PersistentClient(path=str(self.persist_directory))
        
        # Initialize embedding model
        print(f"Loading embedding model: {embedding_model_name}...")
        self.embedding_model = SentenceTransformer(embedding_model_name)
        self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
        print(f"✅ Embedding model loaded ({self.embedding_dim} dimensions)")
        
        self.collection = None
        self.chunks_loaded = []
    
    def load_chunks(self, chunks_json_path: str) -> List[Chunk]:
        """
        Load chunks from JSON file.
        
        Args:
            chunks_json_path: Path to chunks.json
            
        Returns:
            List of Chunk objects
        """
        print(f"\nLoading chunks from {chunks_json_path}...")
        with open(chunks_json_path, 'r', encoding='utf-8') as f:
            chunks_data = json.load(f)
        
        chunks = []
        for chunk_data in chunks_data:
            chunk = Chunk(**chunk_data)
            chunks.append(chunk)
        
        print(f"✅ Loaded {len(chunks)} chunks")
        self.chunks_loaded = chunks
        return chunks
    
    def _generate_embeddings(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings
            batch_size: Batch size for embedding generation
            
        Returns:
            List of embedding vectors
        """
        print(f"\nGenerating embeddings for {len(texts)} texts...")
        start_time = time.time()
        
        # Generate embeddings with progress bar
        embeddings = []
        for i in tqdm(range(0, len(texts), batch_size), desc="Embedding batches"):
            batch = texts[i:i + batch_size]
            batch_embeddings = self.embedding_model.encode(
                batch,
                convert_to_numpy=True,
                show_progress_bar=False
            )
            embeddings.extend(batch_embeddings.tolist())
        
        elapsed = time.time() - start_time
        avg_time = (elapsed / len(texts)) * 1000  # ms per chunk
        
        print(f"✅ Generated {len(embeddings)} embeddings in {elapsed:.2f}s ({avg_time:.2f}ms/chunk)")
        return embeddings
    
    def create_or_load_collection(self, reset: bool = False):
        """
        Create or load ChromaDB collection with cosine similarity.
        
        Args:
            reset: If True, delete existing collection and create new
        """
        if reset:
            try:
                self.client.delete_collection(name=self.collection_name)
                print(f"🗑️  Deleted existing collection: {self.collection_name}")
            except:
                pass
        
        # Create collection with cosine similarity metric
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}  # Explicitly set cosine similarity
        )
        
        count = self.collection.count()
        print(f"✅ Collection '{self.collection_name}' ready (current count: {count})")
    
    def add_chunks(self, chunks: Optional[List[Chunk]] = None):
        """
        Add chunks to ChromaDB collection with embeddings and metadata.
        
        Args:
            chunks: List of Chunk objects (uses self.chunks_loaded if None)
        """
        if chunks is None:
            chunks = self.chunks_loaded
        
        if not chunks:
            raise ValueError("No chunks to add. Call load_chunks() first.")
        
        if self.collection is None:
            raise ValueError("Collection not initialized. Call create_or_load_collection() first.")
        
        print(f"\nAdding {len(chunks)} chunks to ChromaDB...")
        
        # Prepare data
        ids = []
        texts = []
        metadatas = []
        
        for chunk in chunks:
            ids.append(chunk.id)
            texts.append(chunk.text)
            
            # Store drug_names as JSON string (ChromaDB doesn't support list metadata)
            metadata = {
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "authority_family": chunk.authority_family,
                "tier": chunk.tier,
                "year": chunk.year if chunk.year else 0,  # ChromaDB doesn't support None
                "drug_names": json.dumps(chunk.drug_names)  # ✅ Serialize to JSON string
            }
            metadatas.append(metadata)
        
        # Generate embeddings
        embeddings = self._generate_embeddings(texts)
        
        # Add to ChromaDB
        print(f"Storing chunks in ChromaDB...")
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )
        
        print(f"✅ Added {len(chunks)} chunks to collection")
        print(f"   Total chunks in collection: {self.collection.count()}")

    
    def search(self, query: str, top_k: int = 10) -> List[RetrievedChunk]:
        """
        Perform vector similarity search.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            
        Returns:
            List of RetrievedChunk objects, sorted by score (highest first)
        """
        if self.collection is None:
            raise ValueError("Collection not initialized. Call create_or_load_collection() first.")
        
        # Handle empty query
        if not query or not query.strip():
            print("⚠️  Empty query provided, returning empty results")
            return []
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode(
            query,
            convert_to_numpy=True,
            show_progress_bar=False
        ).tolist()
        
        # Search ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        
        # Convert to RetrievedChunk objects
        retrieved_chunks = []
        
        if results['ids'] and results['ids'][0]:
            for rank, (chunk_id, distance, metadata, text) in enumerate(
                zip(
                    results['ids'][0],
                    results['distances'][0],
                    results['metadatas'][0],
                    results['documents'][0]
                ),
                start=1
            ):
                retrieved_chunk = self._chunk_to_retrieved_chunk(
                    chunk_id=chunk_id,
                    distance=distance,
                    metadata=metadata,
                    text=text,
                    rank=rank
                )
                retrieved_chunks.append(retrieved_chunk)
        
        return retrieved_chunks
    
    def _chunk_to_retrieved_chunk(
        self,
        chunk_id: str,
        distance: float,
        metadata: dict,
        text: str,
        rank: int
    ) -> RetrievedChunk:
        """
        Convert ChromaDB result to RetrievedChunk object.
        
        Args:
            chunk_id: Chunk ID
            distance: Cosine distance from ChromaDB (0-2, lower is better)
            metadata: Chunk metadata dict
            text: Chunk text
            rank: Result rank (1-indexed)
            
        Returns:
            RetrievedChunk object with normalized score
        """
        # Normalize score: cosine distance [0, 2] → score [0, 1]
        # Lower distance = higher similarity → higher score
        score = max(0.0, min(1.0, 1.0 - distance))
        
        return RetrievedChunk(
            chunk_id=chunk_id,
            document_id=metadata['document_id'],
            text=text,
            score=score,
            rank=rank,
            retriever_type="vector",
            authority_family=metadata['authority_family'],
            tier=metadata['tier'],
            year=metadata['year'] if metadata['year'] != 0 else None,
            drug_names=json.loads(metadata['drug_names'])  # ✅ Deserialize JSON string
        )

    
    def get_chunk_count(self) -> int:
        """
        Get total number of chunks in collection.
        
        Returns:
            Chunk count
        """
        if self.collection is None:
            return 0
        return self.collection.count()


# Example usage
if __name__ == "__main__":
    # Initialize vector store
    vs = VectorStore(
        persist_directory="data/chromadb",
        embedding_model_name="all-MiniLM-L6-v2"
    )
    
    # Load chunks
    chunks = vs.load_chunks("data/processed/chunks.json")
    
    # Create collection and add chunks
    vs.create_or_load_collection(reset=True)
    vs.add_chunks()
    
    # Test queries
    print("\n" + "="*80)
    print("TESTING VECTOR SEARCH")
    print("="*80)
    
    test_queries = [
        ("warfarin side effects", "In-corpus drug"),
        ("aspirin contraindications", "Out-of-corpus drug"),
        ("", "Empty query")
    ]
    
    for query, description in test_queries:
        print(f"\n📝 Query: '{query}' ({description})")
        results = vs.search(query, top_k=5)
        
        if results:
            print(f"   Found {len(results)} results:")
            for r in results[:3]:  # Show top 3
                print(f"   [{r.rank}] Score: {r.score:.4f} | {r.authority_family} | {r.document_id}")
                print(f"       {r.text[:100]}...")
        else:
            print(f"   No results returned")
    
    print(f"\n✅ Vector store validation complete")
    print(f"   Total chunks indexed: {vs.get_chunk_count()}")
