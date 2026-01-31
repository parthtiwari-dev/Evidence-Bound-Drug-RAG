"""
Semantic chunking for parsed documents using LangChain's RecursiveCharacterTextSplitter
with adaptive overlap based on table density.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
import tiktoken

from src.models.schemas import ParsedDocument, Chunk


class SemanticChunker:
    """
    Chunks parsed documents into semantic units with adaptive overlap.
    
    Features:
    - Adaptive overlap: 100 tokens for table-heavy docs (>200 estimated tables), 50 otherwise
    - Token counting via tiktoken (cl100k_base encoding)
    - Outlier detection (<50 or >800 tokens)
    - Table split detection (chunks starting mid-table)
    """
    
    def __init__(
        self,
        base_chunk_size: int = 512,
        base_overlap: int = 50,
        adaptive_overlap: bool = True,
        table_heavy_threshold: int = 200,
        separators: Optional[List[str]] = None
    ):
        """
        Initialize SemanticChunker.
        
        Args:
            base_chunk_size: Target chunk size in tokens (default: 512)
            base_overlap: Standard overlap in tokens (default: 50)
            adaptive_overlap: Enable adaptive overlap for table-heavy docs (default: True)
            table_heavy_threshold: Table count threshold for adaptive overlap (default: 200)
            separators: Hierarchy of text separators (default: ["\n\n", "\n", ". ", " ", ""])
        """
        self.base_chunk_size = base_chunk_size
        self.base_overlap = base_overlap
        self.adaptive_overlap = adaptive_overlap
        self.table_heavy_threshold = table_heavy_threshold
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]
        
        # Initialize tiktoken encoding
        self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def chunk_document(
        self, 
        parsed_doc: ParsedDocument
    ) -> Tuple[List[Chunk], List[dict]]:
        """
        Chunk a single parsed document into semantic units.
        
        Args:
            parsed_doc: ParsedDocument object from Day 3 parsing
        
        Returns:
            Tuple of (chunks, warnings)
            - chunks: List of Chunk objects
            - warnings: List of warning dicts
        """
        # Determine overlap for this document
        overlap = self._determine_overlap(parsed_doc)
        
        # Initialize text splitter with document-specific overlap
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.base_chunk_size,
            chunk_overlap=overlap,
            separators=self.separators,
            length_function=self._count_tokens,
            is_separator_regex=False
        )
        
        # Split document
        chunk_texts = splitter.split_text(parsed_doc.parsed_markdown)
        
        # Create Chunk objects
        chunks = []
        warnings = []
        
        for index, chunk_text in enumerate(chunk_texts):
            token_count = self._count_tokens(chunk_text)
            
            chunk = Chunk(
                id=f"{parsed_doc.document_id}_chunk_{index:04d}",
                document_id=parsed_doc.document_id,
                text=chunk_text,
                token_count=token_count,
                chunk_index=index,
                section=None,  # Future feature
                authority_family=parsed_doc.authority_family,
                tier=parsed_doc.tier,
                year=parsed_doc.year,
                drug_names=parsed_doc.drug_names
            )
            
            chunks.append(chunk)
            
            # Check for outliers
            outlier_warning = self._detect_outliers(chunk)
            if outlier_warning:
                warnings.append(outlier_warning)
            
            # Check for table splits (independent of overlap strategy)
            if self._detect_table_split(chunk_text):
                warnings.append({
                    "document_id": chunk.document_id,
                    "chunk_id": chunk.id,
                    "warning_category": "table_split_detected",
                    "message": "Chunk starts with table row but no table header detected (possible mid-table split)",
                    "chunk_token_count": token_count,
                    "chunk_index": index,
                    "severity": "medium"
                })
        
        return chunks, warnings
    
    def _determine_overlap(self, parsed_doc: ParsedDocument) -> int:
        """
        Determine overlap tokens based on document's table density.
        
        Args:
            parsed_doc: ParsedDocument with estimated_table_count
        
        Returns:
            100 if table-heavy (>200 estimated tables), else base_overlap (50)
        """
        if not self.adaptive_overlap:
            return self.base_overlap
        
        if parsed_doc.estimated_table_count > self.table_heavy_threshold:
            return 100  # Table-heavy: use 100-token overlap
        else:
            return self.base_overlap  # Standard: use 50-token overlap
    
    def _count_tokens(self, text: str) -> int:
        """
        Count tokens using tiktoken cl100k_base encoding.
        
        Args:
            text: String to tokenize
        
        Returns:
            Token count (int)
        """
        return len(self.encoding.encode(text))
    
    def _detect_table_split(self, chunk_text: str) -> bool:
        """
        Detect if chunk starts mid-table (starts with | but no table separator).
        
        Args:
            chunk_text: Chunk content string
        
        Returns:
            True if table split detected, False otherwise
        """
        lines = chunk_text.strip().split('\n')
        
        # Check if chunk starts with table row
        if not lines or not lines[0].startswith('|'):
            return False
        
        # Check if table separator exists in first 5 lines
        has_separator = any(
            '| ---' in line or '|---' in line 
            for line in lines[:5]
        )
        
        return not has_separator  # True if no separator found
    
    def _detect_outliers(self, chunk: Chunk) -> Optional[dict]:
        """
        Detect if chunk is an outlier (<50 or >800 tokens).
        
        Args:
            chunk: Chunk object with token_count
        
        Returns:
            Warning dict if outlier, None otherwise
        """
        token_count = chunk.token_count
        
        # Too small
        if token_count < 50:
            severity = self._assign_severity("outlier_too_small", token_count)
            return {
                "document_id": chunk.document_id,
                "chunk_id": chunk.id,
                "warning_category": "outlier_too_small",
                "message": f"Chunk contains only {token_count} tokens (threshold: 50)",
                "chunk_token_count": token_count,
                "chunk_index": chunk.chunk_index,
                "severity": severity
            }
        
        # Too large
        if token_count > 800:
            severity = self._assign_severity("outlier_too_large", token_count)
            return {
                "document_id": chunk.document_id,
                "chunk_id": chunk.id,
                "warning_category": "outlier_too_large",
                "message": f"Chunk contains {token_count} tokens (threshold: 800)",
                "chunk_token_count": token_count,
                "chunk_index": chunk.chunk_index,
                "severity": severity
            }
        
        return None  # No outlier
    
    def _assign_severity(self, warning_category: str, token_count: int) -> str:
        """
        Assign severity level based on warning category and token count.
        
        Args:
            warning_category: "outlier_too_small", "outlier_too_large", etc.
            token_count: Chunk token count
        
        Returns:
            "low", "medium", or "high"
        """
        if warning_category == "outlier_too_small":
            if token_count >= 40:
                return "low"      # 40-49: near threshold
            elif token_count >= 20:
                return "medium"   # 20-39: possibly missing context
            else:
                return "high"     # <20: likely error
        
        elif warning_category == "outlier_too_large":
            if token_count <= 900:
                return "low"      # 801-900: slightly over
            elif token_count <= 1200:
                return "medium"   # 901-1200: large chunk
            else:
                return "high"     # >1200: very large
        
        elif warning_category == "table_split_detected":
            return "medium"       # Always medium
        
        else:  # "other"
            return "medium"       # Default
