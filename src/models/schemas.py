from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class ParsedDocument:
    document_id: str
    source_path: str
    authority_family: str  # "FDA", "NICE", "WHO"
    tier: int              # 1 or 2
    year: int
    drug_names: List[str]
    raw_text: str
    parsed_markdown: str
    token_count: int
    page_count: int
    estimated_table_count: int      # NEW: Count of '|' chars in markdown
    parsing_method: str             # NEW: "llamaparse_markdown"
    parse_duration_seconds: float   # NEW: Time taken to parse
    parse_errors: List[str]
    parse_timestamp: str



@dataclass
class Chunk:
    id: str
    document_id: str
    text: str
    token_count: int
    chunk_index: int
    section: Optional[str]
    authority_family: str
    tier: int
    year: Optional[int]
    drug_names: List[str]

@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    text: str
    score: float
    rank: int
    retriever_type: str  # e.g. "vector", "bm25", "hybrid"
    authority_family: str
    tier: int
    year: Optional[int]
    drug_names: List[str]


@dataclass
class GeneratedAnswer:
    question_id: str
    query: str
    answer_text: str
    cited_chunk_ids: List[str]
    is_refusal: bool
    authorities_used: List[str]
    total_token_count: Optional[int] = None
    latency_ms: Optional[float] = None
    cost_usd: Optional[float] = None


@dataclass
class EvaluationResult:
    question_id: str
    system_variant: str  # e.g. "vector", "bm25", "hybrid"
    faithfulness: Optional[float]
    answer_relevancy: Optional[float]
    context_precision: Optional[float]
    raw_answer: str
    raw_context_ids: List[str]
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class FailureCase:
    question_id: str
    failure_category: str  # e.g. "retrieval_failure", "hallucination", etc.
    description: str
    diagnosis: str
    proposed_fix: str
    evaluation_result_id: Optional[str] = None
