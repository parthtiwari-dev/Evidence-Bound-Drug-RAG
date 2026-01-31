"""
Day 3 — PDF Parsing Script

Parses all PDFs in data/raw/{fda,nice}/ using LlamaParse and logs failures.

Outputs:
    - data/processed/parsed_docs.json
    - data/failures/parsing_failures.json

Usage:
    python scripts/02_parse_documents.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import settings
from src.ingestion.parser import DocumentParser, ParsingError
from src.models.schemas import ParsedDocument


def discover_pdfs() -> List[Path]:
    """
    Find all PDFs in data/raw/{fda,nice}/.
    
    Returns:
        List of PDF paths
    """
    data_dir = Path(settings.data_dir)
    raw_dir = data_dir / "raw"
    
    pdf_paths = []
    
    for source_dir in ["fda", "nice"]:
        source_path = raw_dir / source_dir
        if source_path.exists():
            pdf_paths.extend(source_path.glob("*.pdf"))
    
    return sorted(pdf_paths)


def serialize_parsed_document(doc: ParsedDocument) -> Dict:
    """Convert ParsedDocument dataclass to dict for JSON serialization."""
    return {
        "document_id": doc.document_id,
        "source_path": doc.source_path,
        "authority_family": doc.authority_family,
        "tier": doc.tier,
        "year": doc.year,
        "drug_names": doc.drug_names,
        "raw_text": doc.raw_text,
        "parsed_markdown": doc.parsed_markdown,
        "token_count": doc.token_count,
        "page_count": doc.page_count,
        "estimated_table_count": doc.estimated_table_count,
        "parsing_method": doc.parsing_method,
        "parse_duration_seconds": doc.parse_duration_seconds,
        "parse_errors": doc.parse_errors,
        "parse_timestamp": doc.parse_timestamp
    }


def categorize_failure(error_message: str) -> str:
    """
    Categorize parsing failure into locked failure types.
    
    Categories: api_error, timeout, parse_error, unsupported_format, network_error
    """
    error_lower = error_message.lower()
    
    if "429" in error_lower or "rate limit" in error_lower:
        return "api_error"
    elif "401" in error_lower or "unauthorized" in error_lower:
        return "api_error"
    elif "500" in error_lower or "server error" in error_lower:
        return "api_error"
    elif "timeout" in error_lower or "timed out" in error_lower:
        return "timeout"
    elif "empty" in error_lower or "no content" in error_lower:
        return "parse_error"
    elif "scanned" in error_lower or "image" in error_lower:
        return "unsupported_format"
    elif "connection" in error_lower or "network" in error_lower:
        return "network_error"
    else:
        return "parse_error"  # Default


def main():
    print("=" * 60)
    print("Day 3 — PDF Parsing with LlamaParse")
    print("=" * 60)
    print()
    
    # Setup
    data_dir = Path(settings.data_dir)
    processed_dir = data_dir / "processed"
    failures_dir = data_dir / "failures"
    
    processed_dir.mkdir(parents=True, exist_ok=True)
    failures_dir.mkdir(parents=True, exist_ok=True)
    
    # Discover PDFs
    pdf_paths = discover_pdfs()
    total_pdfs = len(pdf_paths)
    
    print(f"📂 Found {total_pdfs} PDFs to parse")
    print(f"   - FDA: {len([p for p in pdf_paths if 'fda' in str(p)])}")
    print(f"   - NICE: {len([p for p in pdf_paths if 'nice' in str(p)])}")
    print()
    
    if total_pdfs == 0:
        print("❌ No PDFs found in data/raw/{fda,nice}/")
        return
    
    # Initialize parser
    print("🔧 Initializing LlamaParse...")
    try:
        parser = DocumentParser(api_key=settings.llama_cloud_api_key)
        print("✓ Parser initialized")
        print()
    except Exception as e:
        print(f"❌ Failed to initialize parser: {e}")
        return
    
    # Parse all PDFs
    parsed_docs = []
    failures = []
    
    print(f"🚀 Starting to parse {total_pdfs} PDFs (serial processing)...")
    print()
    
    for idx, pdf_path in enumerate(pdf_paths, 1):
        print(f"[{idx}/{total_pdfs}] Parsing: {pdf_path.name}")
        
        try:
            parsed_doc = parser.parse_pdf(str(pdf_path))
            parsed_docs.append(parsed_doc)
            
            print(f"   ✓ Success: {parsed_doc.page_count} pages, "
                  f"{parsed_doc.estimated_table_count} table rows, "
                  f"{parsed_doc.parse_duration_seconds}s")
            
        except ParsingError as e:
            error_message = str(e)
            failure_category = categorize_failure(error_message)
            
            failure_record = {
                "document_id": pdf_path.stem,
                "source_path": str(pdf_path),
                "failure_category": failure_category,
                "error_message": error_message,
                "timestamp": datetime.now().isoformat(),
                "retry_count": 3,  # Fixed retry count from parser
                "file_size_kb": round(pdf_path.stat().st_size / 1024, 1)
            }
            
            failures.append(failure_record)
            
            print(f"   ❌ Failed: {failure_category} - {error_message[:60]}...")
        
        print()
    
    # Save parsed documents
    output_path = processed_dir / "parsed_docs.json"
    print(f"💾 Saving {len(parsed_docs)} parsed documents to {output_path}")
    
    serialized_docs = [serialize_parsed_document(doc) for doc in parsed_docs]
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(serialized_docs, f, indent=2, ensure_ascii=False)
    
    print(f"   ✓ Saved to {output_path}")
    print()
    
    # Save failures
    failures_output = failures_dir / "parsing_failures.json"
    print(f"💾 Saving {len(failures)} failures to {failures_output}")
    
    failures_data = {
        "metadata": {
            "total_attempted": total_pdfs,
            "total_succeeded": len(parsed_docs),
            "total_failed": len(failures),
            "timestamp": datetime.now().isoformat()
        },
        "failures": failures
    }
    
    with open(failures_output, 'w', encoding='utf-8') as f:
        json.dump(failures_data, f, indent=2, ensure_ascii=False)
    
    print(f"   ✓ Saved to {failures_output}")
    print()
    
    # Summary statistics
    print("=" * 60)
    print("📊 PARSING SUMMARY")
    print("=" * 60)
    print()
    print(f"Total PDFs:        {total_pdfs}")
    print(f"Successfully parsed: {len(parsed_docs)} ({len(parsed_docs)/total_pdfs*100:.1f}%)")
    print(f"Failed:            {len(failures)} ({len(failures)/total_pdfs*100:.1f}%)")
    print()
    
    if parsed_docs:
        total_pages = sum(doc.page_count for doc in parsed_docs)
        total_tables = sum(doc.estimated_table_count for doc in parsed_docs)
        avg_duration = sum(doc.parse_duration_seconds for doc in parsed_docs) / len(parsed_docs)
        
        print(f"Total pages:       {total_pages}")
        print(f"Total table rows:  {total_tables}")
        print(f"Avg parse time:    {avg_duration:.1f}s")
        print()
    
    if failures:
        print("Failure breakdown:")
        failure_counts = {}
        for f in failures:
            cat = f["failure_category"]
            failure_counts[cat] = failure_counts.get(cat, 0) + 1
        
        for category, count in sorted(failure_counts.items()):
            print(f"  - {category}: {count}")
        print()
    
    print("✅ Parsing complete!")
    print()
    print("Next steps:")
    print("  1. Inspect data/processed/parsed_docs.json")
    print("  2. Review data/failures/parsing_failures.json")
    print("  3. Create docs/parsing_analysis.md (Task 6-7)")


if __name__ == "__main__":
    main()
