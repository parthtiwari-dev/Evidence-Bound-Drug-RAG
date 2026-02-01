"""
Request/Response models for Evidence-Bound Drug RAG API
"""
from pydantic import BaseModel, Field, validator
from typing import List, Literal
from datetime import datetime


class RetrieveRequest(BaseModel):
    """Request model for /retrieve endpoint"""
    query: str = Field(..., min_length=1, description="User query text")
    top_k: int = Field(default=10, ge=1, le=50, description="Number of results to return")
    retriever_type: Literal["vector", "bm25", "hybrid"] = Field(
        default="vector", 
        description="Retriever to use: vector (Phase 0 default), bm25, hybrid"
    )
    
    @validator('query')
    def query_not_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Query cannot be empty")
        return v.strip()


class ChunkResult(BaseModel):
    """Single retrieved chunk result"""
    rank: int
    chunk_id: str
    document_id: str
    score: float
    text_preview: str = Field(..., description="First 300 chars of chunk text")
    authority_family: str
    tier: int
    year: int | None
    drug_names: List[str]


class RetrievalMetadata(BaseModel):
    """Metadata about retrieval execution"""
    retriever_used: str
    query_timestamp: str
    top_drugs_retrieved: List[str] = Field(..., description="Unique drugs in top-K results (max 5)")
    total_indexed_chunks: int


class RetrieveResponse(BaseModel):
    """Response model for /retrieve endpoint"""
    query: str
    results: List[ChunkResult]
    latency_ms: float
    metadata: RetrievalMetadata


class StatsResponse(BaseModel):
    """Response model for /stats endpoint"""
    total_chunks: int
    drugs_covered: List[str]
    retriever_types_available: List[str]
    vector_store_status: str
    bm25_index_status: str
    hybrid_status: str


class HealthResponse(BaseModel):
    """Response model for /health endpoint"""
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    timestamp: str
    retrievers_loaded: dict  # {vector: bool, bm25: bool, hybrid: bool}
