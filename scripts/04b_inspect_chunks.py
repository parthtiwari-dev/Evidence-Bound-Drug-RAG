"""
Day 4 Task 8: Semi-Automated Chunk Inspection

Performs automated validation on all chunks and displays 10 strategic samples
for human review with quality metrics.
"""

import json
import random
from pathlib import Path
from collections import defaultdict
from typing import List, Dict


def load_data():
    """Load chunks and warnings."""
    chunks_path = Path("data/processed/chunks.json")
    warnings_path = Path("data/failures/chunking_warnings.json")
    
    with open(chunks_path, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    
    with open(warnings_path, 'r', encoding='utf-8') as f:
        warnings_data = json.load(f)
    
    return chunks, warnings_data


def automated_validation(chunks: List[dict]) -> Dict:
    """
    Perform automated validation checks on all chunks.
    
    Returns dict with validation results and issues.
    """
    issues = {
        "zero_token": [],
        "empty_text": [],
        "missing_metadata": [],
        "invalid_id_format": [],
        "chunk_index_mismatch": [],
        "duplicate_ids": [],
        "text_too_short": [],
        "suspicious_truncation": []
    }
    
    seen_ids = set()
    
    for i, chunk in enumerate(chunks):
        chunk_id = chunk.get('id', f'MISSING_ID_{i}')
        
        # Check 1: Zero tokens
        if chunk.get('token_count', 0) == 0:
            issues["zero_token"].append(chunk_id)
        
        # Check 2: Empty text
        if not chunk.get('text', '').strip():
            issues["empty_text"].append(chunk_id)
        
        # Check 3: Missing critical metadata
        required_fields = ['id', 'document_id', 'text', 'token_count', 'chunk_index', 
                          'authority_family', 'tier', 'drug_names']
        missing = [f for f in required_fields if f not in chunk]
        if missing:
            issues["missing_metadata"].append(f"{chunk_id}: missing {missing}")
        
        # Check 4: Invalid ID format (should be {document_id}_chunk_{index:04d})
        if '_chunk_' not in chunk_id:
            issues["invalid_id_format"].append(chunk_id)
        
        # Check 5: Chunk index matches ID
        if '_chunk_' in chunk_id:
            try:
                id_index = int(chunk_id.split('_chunk_')[1])
                actual_index = chunk.get('chunk_index', -1)
                if id_index != actual_index:
                    issues["chunk_index_mismatch"].append(
                        f"{chunk_id}: ID says {id_index}, field says {actual_index}"
                    )
            except (ValueError, IndexError):
                issues["invalid_id_format"].append(chunk_id)
        
        # Check 6: Duplicate IDs
        if chunk_id in seen_ids:
            issues["duplicate_ids"].append(chunk_id)
        seen_ids.add(chunk_id)
        
        # Check 7: Text suspiciously short compared to token count
        text_len = len(chunk.get('text', ''))
        token_count = chunk.get('token_count', 0)
        if token_count > 100 and text_len < 100:
            issues["text_too_short"].append(
                f"{chunk_id}: {token_count} tokens but only {text_len} chars"
            )
        
        # Check 8: Suspicious truncation (ends mid-word)
        # Check 8: Suspicious truncation (ends mid-word)
        text = chunk.get('text', '')
        if text and len(text) > 50:
            last_line = text.strip().split('\n')[-1]
            # Only flag if ends mid-word AND not a heading/table/citation
            if not any(c in text[-10:] for c in ['.', '\n', ')', ']', '"', '>', '#', '|', ':']):
                if not text[-1].isspace() and not last_line.isupper():
                    issues["suspicious_truncation"].append(chunk_id)

    
    return issues


def semantic_validation(chunks: List[dict], sample_size: int = 10) -> Dict:
    """
    Perform semantic validation on a sample of chunks.
    
    Checks for:
    - Incomplete sentences
    - Table fragmentation
    - Metadata consistency
    """
    results = {
        "incomplete_sentences": [],
        "table_fragments": [],
        "metadata_issues": []
    }
    
    # Sample chunks
    random.seed(42)
    samples = random.sample(chunks, min(sample_size, len(chunks)))
    
    for chunk in samples:
        text = chunk.get('text', '')
        chunk_id = chunk.get('id', 'UNKNOWN')
        
        # Check for incomplete sentences (starts mid-sentence)
        first_line = text.strip().split('\n')[0] if text.strip() else ''
        if first_line and not first_line[0].isupper() and not first_line.startswith('#'):
            # Starts lowercase and not a markdown heading
            if not first_line.startswith('|'):  # Not a table row
                results["incomplete_sentences"].append(chunk_id)
        
        # Check for table fragments (contains | but very few rows)
        if '|' in text:
            table_rows = [line for line in text.split('\n') if line.strip().startswith('|')]
            if 1 <= len(table_rows) <= 2:  # Only 1-2 table rows = likely fragment
                results["table_fragments"].append(f"{chunk_id}: only {len(table_rows)} table rows")
        
        # Check metadata consistency (year should match document)
        doc_id = chunk.get('document_id', '')
        chunk_year = chunk.get('year')
        if chunk_year and str(chunk_year) not in doc_id:
            # Year in metadata doesn't appear in document ID
            # This might be intentional (publication year != filename year)
            # So just flag for review, not necessarily an error
            results["metadata_issues"].append(
                f"{chunk_id}: year {chunk_year} not in doc_id '{doc_id}'"
            )
    
    return results


def select_strategic_samples(chunks: List[dict], warnings_data: dict) -> List[dict]:
    """
    Select 10 strategic samples for human review.
    
    Strategy:
    - 3 from FDA documents (table-heavy)
    - 3 from NICE documents (text-heavy)
    - 4 from documents with warnings (edge cases)
    """
    random.seed(42)
    
    # Group by authority
    fda_chunks = [c for c in chunks if c.get('authority_family') == 'FDA']
    nice_chunks = [c for c in chunks if c.get('authority_family') == 'NICE']
    
    # Get documents with warnings
    warning_doc_ids = set()
    for warning in warnings_data.get('warnings', []):
        warning_doc_ids.add(warning['document_id'])
    
    warning_chunks = [c for c in chunks if c.get('document_id') in warning_doc_ids]
    
    # Sample selection
    samples = []
    
    # 3 from FDA
    if len(fda_chunks) >= 3:
        samples.extend(random.sample(fda_chunks, 3))
    else:
        samples.extend(fda_chunks)
    
    # 3 from NICE
    if len(nice_chunks) >= 3:
        samples.extend(random.sample(nice_chunks, 3))
    else:
        samples.extend(nice_chunks)
    
    # 4 from warning documents (avoid duplicates)
    remaining_warning_chunks = [c for c in warning_chunks if c not in samples]
    if len(remaining_warning_chunks) >= 4:
        samples.extend(random.sample(remaining_warning_chunks, 4))
    else:
        samples.extend(remaining_warning_chunks)
        # Fill remaining with random chunks
        remaining = [c for c in chunks if c not in samples]
        needed = 10 - len(samples)
        if needed > 0 and remaining:
            samples.extend(random.sample(remaining, min(needed, len(remaining))))
    
    return samples[:10]  # Ensure exactly 10


def print_validation_report(issues: Dict, semantic_results: Dict):
    """Print validation report."""
    print("\n" + "="*60)
    print("AUTOMATED VALIDATION REPORT")
    print("="*60)
    
    total_issues = sum(len(v) for v in issues.values())
    
    if total_issues == 0:
        print("\n✅ ALL AUTOMATED CHECKS PASSED")
        print("   No critical issues detected in chunks")
    else:
        print(f"\n⚠️  FOUND {total_issues} POTENTIAL ISSUES\n")
        
        for check_name, issue_list in issues.items():
            if issue_list:
                print(f"\n{check_name.upper().replace('_', ' ')} ({len(issue_list)}):")
                for issue in issue_list[:5]:  # Show first 5
                    print(f"  - {issue}")
                if len(issue_list) > 5:
                    print(f"  ... and {len(issue_list) - 5} more")
    
    # Semantic validation
    print("\n" + "="*60)
    print("SEMANTIC VALIDATION (Sample of 10 chunks)")
    print("="*60)
    
    semantic_issues = sum(len(v) for v in semantic_results.values())
    
    if semantic_issues == 0:
        print("\n✅ ALL SEMANTIC CHECKS PASSED")
    else:
        print(f"\n⚠️  FOUND {semantic_issues} SEMANTIC ISSUES\n")
        
        for check_name, issue_list in semantic_results.items():
            if issue_list:
                print(f"\n{check_name.upper().replace('_', ' ')} ({len(issue_list)}):")
                for issue in issue_list:
                    print(f"  - {issue}")


def display_sample(chunk: dict, index: int, total: int):
    """Display a chunk in readable format."""
    print(f"\n{'='*60}")
    print(f"SAMPLE {index}/{total}")
    print(f"{'='*60}")
    
    print(f"\n📄 Chunk ID: {chunk.get('id', 'MISSING')}")
    print(f"📁 Document: {chunk.get('document_id', 'MISSING')}")
    print(f"📍 Index: {chunk.get('chunk_index', 'MISSING')}")
    print(f"🔢 Tokens: {chunk.get('token_count', 0)}")
    print(f"🏛️  Authority: {chunk.get('authority_family', 'MISSING')} (Tier {chunk.get('tier', '?')})")
    print(f"📅 Year: {chunk.get('year', 'MISSING')}")
    print(f"💊 Drugs: {', '.join(chunk.get('drug_names', [])) or 'None'}")
    
    # Quality indicators
    text = chunk.get('text', '')
    print(f"\n📊 QUALITY INDICATORS:")
    print(f"   Character count: {len(text)}")
    print(f"   Line count: {len(text.split(chr(10)))}")
    print(f"   Has tables: {'Yes' if '|' in text else 'No'}")
    print(f"   Starts with heading: {'Yes' if text.strip().startswith('#') else 'No'}")
    print(f"   Ends with punctuation: {'Yes' if text.strip() and text.strip()[-1] in '.!?)>]' else 'No'}")
    
    # Text preview
    print(f"\n📝 TEXT PREVIEW (first 400 chars):")
    print("-" * 60)
    print(text[:400])
    if len(text) > 400:
        print("...")
    print("-" * 60)
    
    # Text ending preview
    if len(text) > 400:
        print(f"\n📝 TEXT ENDING (last 200 chars):")
        print("-" * 60)
        print("..." + text[-200:])
        print("-" * 60)


def main():
    print("="*60)
    print("Task 8: Semi-Automated Chunk Inspection")
    print("="*60)
    
    # Load data
    print("\n[1] Loading chunks and warnings...")
    chunks, warnings_data = load_data()
    print(f"✅ Loaded {len(chunks)} chunks")
    print(f"✅ Loaded {warnings_data['metadata']['total_warnings']} warnings")
    
    # Automated validation
    print("\n[2] Running automated validation checks...")
    issues = automated_validation(chunks)
    
    # Semantic validation
    print("\n[3] Running semantic validation on sample...")
    semantic_results = semantic_validation(chunks, sample_size=10)
    
    # Print validation report
    print_validation_report(issues, semantic_results)
    
    # Select strategic samples
    print("\n[4] Selecting 10 strategic samples for human review...")
    samples = select_strategic_samples(chunks, warnings_data)
    print(f"✅ Selected {len(samples)} samples")
    
    # Display samples
    print("\n" + "="*60)
    print("STRATEGIC SAMPLE CHUNKS FOR HUMAN REVIEW")
    print("="*60)
    
    for i, chunk in enumerate(samples, 1):
        display_sample(chunk, i, len(samples))
    
    # Final summary
    print("\n" + "="*60)
    print("INSPECTION SUMMARY")
    print("="*60)
    
    total_automated_issues = sum(len(v) for v in issues.values())
    total_semantic_issues = sum(len(v) for v in semantic_results.values())
    
    print(f"\nAutomated validation: {total_automated_issues} issues")
    print(f"Semantic validation: {total_semantic_issues} issues")
    
    if total_automated_issues == 0 and total_semantic_issues == 0:
        print("\n✅ ALL CHECKS PASSED")
        print("   Chunks are high quality and ready for Day 5 (vector store)")
        print("\n🚦 STATUS: GREEN - No blockers detected")
    elif total_automated_issues == 0 and total_semantic_issues <= 3:
        print("\n⚠️  MINOR ISSUES DETECTED")
        print("   Automated checks passed, minor semantic issues found")
        print("   Review samples above to confirm acceptability")
        print("\n🚦 STATUS: YELLOW - Proceed with caution")
    else:
        print("\n❌ SIGNIFICANT ISSUES DETECTED")
        print("   Review issues above before proceeding to Day 5")
        print("\n🚦 STATUS: RED - Fix issues before proceeding")
    
    print("\n" + "="*60)
    print("Task 8 Complete")
    print("="*60)


if __name__ == "__main__":
    main()
