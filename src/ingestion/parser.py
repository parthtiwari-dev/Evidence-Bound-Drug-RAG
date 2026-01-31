"""
PDF parsing module using LlamaParse for table-preserving markdown extraction.

This module provides DocumentParser class for converting drug guideline PDFs
into structured ParsedDocument objects with authority metadata.
"""

import time
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from llama_parse import LlamaParse

from src.models.schemas import ParsedDocument


class ParsingError(Exception):
    """Raised when PDF parsing fails after all retries."""
    pass


class DocumentParser:
    """
    Parser for drug guideline PDFs using LlamaParse API.
    
    Preserves table structure via markdown output and extracts authority
    metadata from filenames following Phase 0 naming conventions.
    """
    
    def __init__(self, api_key: str, result_type: str = "markdown"):
        """
        Initialize LlamaParse client.
        
        Args:
            api_key: LlamaCloud API key
            result_type: Output format (default "markdown")
        """
        self.parser = LlamaParse(
            api_key=api_key,
            result_type=result_type,
            verbose=True
        )
        self.result_type = result_type
        
    def parse_pdf(self, pdf_path: str) -> ParsedDocument:
        """
        Parse single PDF using LlamaParse with retry logic.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            ParsedDocument with all fields populated
            
        Raises:
            ParsingError: If parsing fails after 3 retries
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise ParsingError(f"PDF not found: {pdf_path}")
        
        # Extract metadata from filename
        metadata = self.extract_metadata_from_path(str(pdf_path))
        
        # Parse with retry logic
        max_retries = 3
        retry_delay = 2  # seconds
        
        parse_errors = []
        start_time = time.time()
        
        for attempt in range(max_retries):
            try:
                # Call LlamaParse API
                documents = self.parser.load_data(str(pdf_path))
                
                if not documents:
                    raise ParsingError("LlamaParse returned empty document list")
                
                # Extract markdown text
                parsed_markdown = "\n\n".join([doc.text for doc in documents])
                
                if not parsed_markdown.strip():
                    raise ParsingError("Parsed markdown is empty")
                
                # Calculate metrics
                parse_duration = time.time() - start_time
                token_count = len(parsed_markdown.split())
                page_count = len(documents)
                estimated_table_count = self.estimate_table_count(parsed_markdown)
                
                # Create ParsedDocument
                parsed_doc = ParsedDocument(
                    document_id=pdf_path.stem,
                    source_path=str(pdf_path),
                    authority_family=metadata["authority_family"],
                    tier=metadata["tier"],
                    year=metadata["year"],
                    drug_names=metadata["drug_names"],
                    raw_text=parsed_markdown,  # LlamaParse gives markdown, not "raw" text
                    parsed_markdown=parsed_markdown,
                    token_count=token_count,
                    page_count=page_count,
                    estimated_table_count=estimated_table_count,
                    parsing_method="llamaparse_markdown",
                    parse_duration_seconds=round(parse_duration, 2),
                    parse_errors=parse_errors,
                    parse_timestamp=datetime.now().isoformat()
                )
                
                return parsed_doc
                
            except Exception as e:
                error_msg = f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}"
                parse_errors.append(error_msg)
                
                if attempt < max_retries - 1:
                    # Exponential backoff
                    time.sleep(retry_delay * (2 ** attempt))
                else:
                    # Final failure
                    raise ParsingError(
                        f"Failed to parse {pdf_path.name} after {max_retries} attempts. "
                        f"Last error: {str(e)}"
                    )
    
    def estimate_table_count(self, markdown_text: str) -> int:
        """
        Estimate number of tables in markdown text.
        
        Heuristic: Count lines with 3+ pipe characters (markdown table rows).
        
        Args:
            markdown_text: Parsed markdown content
            
        Returns:
            Estimated number of table rows
        """
        table_rows = 0
        for line in markdown_text.split('\n'):
            if line.count('|') >= 3:
                table_rows += 1
        return table_rows
    
    def extract_metadata_from_path(self, pdf_path: str) -> Dict:
        """
        Extract authority, tier, year, drug names from filename.
        
        Follows Phase 0 naming convention:
            fda_{drug}_{doc_type}_{year}.pdf
            nice_{topic}_{doc_type}_{year}.pdf
            
        Args:
            pdf_path: Full path to PDF
            
        Returns:
            Dict with authority_family, tier, year, drug_names
            
        Example:
            "data/raw/fda/fda_warfarin_label_2022.pdf"
            → {"authority_family": "FDA", "tier": 1, "year": 2022, 
               "drug_names": ["warfarin"]}
        """
        path = Path(pdf_path)
        filename = path.stem  # Without extension
        
        # Extract authority from first part
        parts = filename.split('_')
        authority_prefix = parts[0].upper()
        
        # Map to authority family
        authority_map = {
            "FDA": ("FDA", 1),
            "NICE": ("NICE", 1),
            "WHO": ("WHO", 2)
        }
        
        authority_family, tier = authority_map.get(
            authority_prefix, 
            ("UNKNOWN", 3)
        )
        
        # Extract year (4-digit number)
        year_match = re.search(r'\d{4}', filename)
        year = int(year_match.group()) if year_match else 0
        
        # Extract drug names (locked set)
        locked_drugs = [
            "atorvastatin", "lisinopril", "amoxicillin", "ciprofloxacin",
            "ibuprofen", "paracetamol", "acetaminophen", "metformin", "warfarin"
        ]
        
        drug_names = []
        filename_lower = filename.lower()
        for drug in locked_drugs:
            if drug in filename_lower:
                # Normalize acetaminophen → paracetamol
                if drug == "acetaminophen":
                    drug_names.append("paracetamol")
                else:
                    drug_names.append(drug)
        
        # Remove duplicates
        drug_names = list(set(drug_names))
        
        return {
            "authority_family": authority_family,
            "tier": tier,
            "year": year,
            "drug_names": drug_names if drug_names else ["unknown"]
        }
