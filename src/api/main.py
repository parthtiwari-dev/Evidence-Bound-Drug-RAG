"""
Evidence-Bound Drug RAG API
"""
print("="*80)
print("[DEBUG] Starting API script...")
print("="*80)

import sys
print(f"[DEBUG] Python version: {sys.version}")
print(f"[DEBUG] Python path: {sys.executable}")

try:
    print("[DEBUG] Importing FastAPI...")
    from fastapi import FastAPI
    print("[DEBUG] ✅ FastAPI imported")
    
    print("[DEBUG] Importing pathlib...")
    from pathlib import Path
    print("[DEBUG] ✅ Pathlib imported")
    
    print("[DEBUG] Checking data files...")
    chunks_path = Path("data/processed/chunks.json")
    chromadb_path = Path("data/chromadb")
    
    print(f"[DEBUG] chunks.json exists: {chunks_path.exists()}")
    print(f"[DEBUG] chromadb exists: {chromadb_path.exists()}")
    
    if chunks_path.exists():
        print(f"[DEBUG] chunks.json size: {chunks_path.stat().st_size / 1024:.1f} KB")
    
    print("[DEBUG] Importing retrieval modules...")
    from src.retrieval.vector_store import VectorStore
    print("[DEBUG] ✅ VectorStore imported")
    
    from src.retrieval.bm25_index import BM25Index
    print("[DEBUG] ✅ BM25Index imported")
    
    from src.retrieval.hybrid_retriever import HybridRetriever
    print("[DEBUG] ✅ HybridRetriever imported")
    
except Exception as e:
    print(f"[DEBUG] ❌ IMPORT ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("[DEBUG] All imports successful!")
print("="*80)

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
from src.generation.llm import LLMGenerator  
from src.models.schemas import GeneratedAnswer 

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
llm_generator: LLMGenerator | None = None

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
    global vector_store, bm25_index, hybrid_retriever, llm_generator
    
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

        current_count = vector_store.get_chunk_count()

        if current_count == 0:
            logger.info("[LOAD] Vector store empty — generating embeddings...")
            vector_store.add_chunks()
            logger.info(f"[OK] Vector store populated: {vector_store.get_chunk_count()} chunks")
        else:
            logger.info(f"[OK] Vector Store loaded: {current_count} chunks")

        # Load BM25 Index
        # Build BM25 Index from loaded chunks (avoids pickle issues)
        logger.info("[LOAD] Building BM25 Index from chunks...")
        if vector_store.chunks_loaded:
            bm25_index = BM25Index(k1=1.5, b=0.75)
            bm25_index.chunks = vector_store.chunks_loaded  # Reuse already loaded chunks
            bm25_index.build_index()
            logger.info(f"[OK] BM25 Index built: {bm25_index.get_corpus_size()} chunks")
        else:
            logger.error("[ERROR] No chunks loaded, cannot build BM25 index")
            raise RuntimeError("Cannot build BM25 without chunks")

        
        # Initialize Hybrid Retriever
        logger.info("[LOAD]Initializing Hybrid Retriever...")
        hybrid_retriever = HybridRetriever(vector_store, bm25_index)
        logger.info("[OK] Hybrid Retriever initialized")
        
        # Initialize LLM Generator
        logger.info("[LOAD] Initializing LLM Generator (Groq)...")
        llm_generator = LLMGenerator(
            model="llama-3.3-70b-versatile",
            temperature=0.0,
            max_tokens=500
        )
        logger.info("[OK] LLM Generator initialized")
        
        logger.info("=" * 80)
        logger.info("[OK] API READY - All retrievers + LLM loaded")  
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

    # ✅ NEW: Filter out "unknown" and invalid values
    drugs_filtered = [
        d for d in drugs_covered 
        if d and d.lower() not in ["unknown", "n/a", "none", ""]
    ]
    
    return StatsResponse(
        total_chunks=vector_store.get_chunk_count(),
        drugs_covered=sorted(list(drugs_filtered)),     # ✅ Changed from drugs_covered to drugs_filtered
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


@app.post(
    "/ask",
    summary="Ask a question about drug information",
    response_description="Generated answer with citations and metadata",
    tags=["Generation"]
)
async def ask(request: RetrieveRequest):
    """
    Ask a pharmaceutical question and get a cited answer.
    
    This endpoint combines:
    1. Hybrid retrieval (BM25 + Vector search)
    2. LLM generation with Groq (llama-3.3-70b-versatile)
    3. Citation extraction and validation
    4. Refusal policy enforcement
    
    **Parameters**:
    - **query**: Your question about drugs (e.g., "What are side effects of warfarin?")
    - **top_k**: Number of chunks to retrieve (default: 5, max: 20)
    - **retriever_type**: Search method - "vector", "bm25", or "hybrid" (default: hybrid)
    
    **Returns**:
    - **answer**: Generated answer with [1], [2], [3] citations
    - **cited_chunks**: List of chunk IDs that were cited in the answer
    - **is_refusal**: True if question was refused (medical advice, etc.)
    - **authorities_used**: Which sources were used (FDA, NICE, WHO)
    - **retrieval_time_ms**: Time spent retrieving chunks
    - **generation_time_ms**: Time spent generating answer
    - **total_latency_ms**: Total end-to-end time
    - **cost_usd**: Cost of generation (always $0.00 with Groq)
    
    **Example Request**:
    ```json
    {
        "query": "What are the side effects of warfarin?",
        "top_k": 5,
        "retriever_type": "hybrid"
    }
    ```
    
    **Example Response**:
    ```json
    {
        "query": "What are the side effects of warfarin?",
        "answer": "Common side effects include bleeding  and bruising...",[41][42]
        "is_refusal": false,
        "cited_chunks": ["fda_warfarin_label_2025_chunk_0044"],
        "authorities_used": ["FDA"],
        "retrieval_time_ms": 450.5,
        "generation_time_ms": 1200.8,
        "total_latency_ms": 1651.3,
        "cost_usd": 0.0
    }
    ```
    """
    start_time = time.time()
    
    # Check components are initialized
    if not hybrid_retriever:
        raise HTTPException(
            status_code=503, 
            detail="Retriever not initialized. Server still starting up."
        )
    if not llm_generator:
        raise HTTPException(
            status_code=503, 
            detail="LLM Generator not initialized. Server still starting up."
        )
    
    try:
        # STEP 1: Retrieve chunks
        logger.info(f"[ASK] Query: {request.query[:100]}...")
        retrieval_start = time.time()
        
        if request.retriever_type == "vector":
            chunks = hybrid_retriever.retrieve_vector(request.query, request.top_k)
        elif request.retriever_type == "bm25":
            chunks = hybrid_retriever.retrieve_bm25(request.query, request.top_k)
        else:  # hybrid (default)
            chunks = hybrid_retriever.retrieve_vector(
            request.query,
            request.top_k
            )
        
        retrieval_time = (time.time() - retrieval_start) * 1000
        logger.info(f"[ASK] Retrieved {len(chunks)} chunks in {retrieval_time:.1f}ms")
        
        # STEP 2: Generate answer with LLM
        generation_start = time.time()
        
        result: GeneratedAnswer = llm_generator.generate_answer(
            query=request.query,
            chunks=chunks,
            question_id=f"api_{int(time.time())}"
        )
        
        generation_time = (time.time() - generation_start) * 1000
        total_time = (time.time() - start_time) * 1000
        
        logger.info(f"[ASK] Generated answer in {generation_time:.1f}ms")
        logger.info(f"[ASK] Total time: {total_time:.1f}ms | Refusal: {result.is_refusal}")
        
        # STEP 3: Build response
        response = {
            "query": result.query,
            "answer": result.answer_text,
            "is_refusal": result.is_refusal,
            "cited_chunks": result.cited_chunk_ids,
            "authorities_used": result.authorities_used,
            "retrieval_time_ms": round(retrieval_time, 2),
            "generation_time_ms": round(generation_time, 2),
            "total_latency_ms": round(total_time, 2),
            "cost_usd": result.cost_usd or 0.0,
            "chunks_retrieved": len(chunks),
            "chunks_cited": len(result.cited_chunk_ids),
            "total_tokens": result.total_token_count
        }
        
        return response
        
    except Exception as e:
        logger.error(f"[ASK] Error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate answer: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    import os
    
    port = int(os.getenv("PORT", 7860))  # Read PORT from Render, default to 8000 locally
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        log_level="info"
    )
