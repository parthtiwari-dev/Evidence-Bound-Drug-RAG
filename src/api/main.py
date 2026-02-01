"""
FastAPI Application for Evidence-Bound Drug RAG System
Phase 0: Retrieval-only API (no LLM integration)
"""
import time
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Import your existing retrievers
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.retrieval.vector_store import VectorStore
from src.retrieval.bm25_index import BM25Index
from src.retrieval.hybrid_retriever import HybridRetriever
from src.models.schemas import RetrievedChunk

# Import API models
from src.api.models import (
    RetrieveRequest,
    RetrieveResponse,
    ChunkResult,
    RetrievalMetadata,
    StatsResponse,
    HealthResponse
)
from src.api.logger import retrieval_logger, logger

# Initialize FastAPI app
app = FastAPI(
    title="Evidence-Bound Drug RAG API",
    version="0.1.0",
    description="Retrieval API for evidence-bound drug information (Phase 0 PoC)",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global retriever instances
vector_store: VectorStore | None = None
bm25_index: BM25Index | None = None
hybrid_retriever: HybridRetriever | None = None

# Paths
DATA_DIR = Path("data/processed")
CHROMA_DIR = Path("data/chromadb")
BM25_INDEX_PATH = Path("data/bm25_index.pkl")
CHUNKS_PATH = DATA_DIR / "chunks.json"


@app.on_event("startup")
async def startup_event():
    """
    Initialize retrievers on API startup
    
    Discipline A: All 3 retrievers loaded (vector, bm25, hybrid) for easy switching
    """
    global vector_store, bm25_index, hybrid_retriever
    
    logger.info("=" * 80)
    logger.info("[START] STARTING EVIDENCE-BOUND DRUG RAG API")
    logger.info("=" * 80)
    
    try:
        # Load Vector Store
        logger.info("[LOAD]Loading Vector Store (ChromaDB)...")
        vector_store = VectorStore(
            persist_directory=str(CHROMA_DIR),
            embedding_model_name="all-MiniLM-L6-v2"
        )
        vector_store.load_chunks(str(CHUNKS_PATH))
        vector_store.create_or_load_collection(reset=False)
        logger.info(f"[OK] Vector Store loaded: {vector_store.get_chunk_count()} chunks")
        
        # Load BM25 Index
        logger.info("[LOAD]Loading BM25 Index...")
        bm25_index = BM25Index.load_from_disk(str(BM25_INDEX_PATH))
        logger.info(f"[OK] BM25 Index loaded: {bm25_index.get_corpus_size()} chunks")
        
        # Initialize Hybrid Retriever
        logger.info("[LOAD]Initializing Hybrid Retriever...")
        hybrid_retriever = HybridRetriever(vector_store, bm25_index)
        logger.info("[OK] Hybrid Retriever initialized")
        
        logger.info("=" * 80)
        logger.info("[OK] API READY - All retrievers loaded")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"[ERROR] STARTUP FAILED: {e}")
        raise


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    
    Returns:
        Status of API and loaded retrievers
    """
    retrievers_loaded = {
        "vector": vector_store is not None,
        "bm25": bm25_index is not None,
        "hybrid": hybrid_retriever is not None
    }
    
    # Determine overall health status
    if all(retrievers_loaded.values()):
        status = "healthy"
    elif any(retrievers_loaded.values()):
        status = "degraded"
    else:
        status = "unhealthy"
    
    return HealthResponse(
        status=status,
        version="0.1.0",
        timestamp=datetime.now().isoformat(),
        retrievers_loaded=retrievers_loaded
    )


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """
    Get statistics about indexed data
    
    Returns:
        Total chunks, drugs covered, retriever availability
    """
    if not vector_store or not bm25_index:
        raise HTTPException(status_code=503, detail="Retrievers not initialized")
    
    # Get unique drugs from vector store chunks
    drugs_covered = set()
    if vector_store.chunks_loaded:
        for chunk in vector_store.chunks_loaded:
            drugs_covered.update(chunk.drug_names)
    
    return StatsResponse(
        total_chunks=vector_store.get_chunk_count(),
        drugs_covered=sorted(list(drugs_covered)),
        retriever_types_available=["vector", "bm25", "hybrid"],
        vector_store_status="loaded" if vector_store else "not loaded",
        bm25_index_status="loaded" if bm25_index else "not loaded",
        hybrid_status="available" if hybrid_retriever else "not available"
    )


@app.post("/retrieve", response_model=RetrieveResponse)
async def retrieve(request: RetrieveRequest):
    """
    Retrieve relevant chunks for a query
    
    Discipline A: Switchable retriever_type (vector | bm25 | hybrid)
    Discipline B: Log every query (query, latency, drugs retrieved)
    
    Args:
        request: RetrieveRequest with query, top_k, retriever_type
        
    Returns:
        RetrieveResponse with results and metadata
    """
    start_time = time.time()
    
    # Validate retrievers are loaded
    if not hybrid_retriever:
        raise HTTPException(status_code=503, detail="Retrievers not initialized")
    
    try:
        # Route to appropriate retriever based on request
        if request.retriever_type == "vector":
            results: List[RetrievedChunk] = hybrid_retriever.retrieve_vector(
                request.query, 
                top_k=request.top_k
            )
        elif request.retriever_type == "bm25":
            results: List[RetrievedChunk] = hybrid_retriever.retrieve_bm25(
                request.query, 
                top_k=request.top_k
            )
        elif request.retriever_type == "hybrid":
            results: List[RetrievedChunk] = hybrid_retriever.retrieve_hybrid(
                request.query, 
                top_k=request.top_k,
                vector_weight=0.5  # Default 50/50
            )
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid retriever_type: {request.retriever_type}"
            )
        
        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000
        
        # Convert RetrievedChunk objects to ChunkResult models
        chunk_results = []
        for chunk in results:
            chunk_results.append(ChunkResult(
                rank=chunk.rank,
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                score=chunk.score,
                text_preview=chunk.text[:300] + "..." if len(chunk.text) > 300 else chunk.text,
                authority_family=chunk.authority_family,
                tier=chunk.tier,
                year=chunk.year,
                drug_names=chunk.drug_names
            ))
        
        # Extract top drugs for metadata
        top_drugs = []
        seen_drugs = set()
        for chunk in results:
            for drug in chunk.drug_names:
                if drug not in seen_drugs:
                    top_drugs.append(drug)
                    seen_drugs.add(drug)
                if len(top_drugs) >= 5:
                    break
            if len(top_drugs) >= 5:
                break
        
        # Build response
        response = RetrieveResponse(
            query=request.query,
            results=chunk_results,
            latency_ms=round(latency_ms, 2),
            metadata=RetrievalMetadata(
                retriever_used=request.retriever_type,
                query_timestamp=datetime.now().isoformat(),
                top_drugs_retrieved=top_drugs,
                total_indexed_chunks=vector_store.get_chunk_count()
            )
        )
        
        # Discipline B: Log retrieval for future training/evaluation
        retrieval_logger.log_retrieval(
            query=request.query,
            retriever_type=request.retriever_type,
            latency_ms=latency_ms,
            top_k=request.top_k,
            results=[{
                'chunk_id': r.chunk_id,
                'drug_names': r.drug_names,
                'score': r.score
            } for r in results]
        )
        
        return response
        
    except Exception as e:
        # Log error
        retrieval_logger.log_error(
            query=request.query,
            retriever_type=request.retriever_type,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
