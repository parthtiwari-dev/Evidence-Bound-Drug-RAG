"""
Day 4 Script: Chunk all parsed documents and analyze distribution.

Steps:
1. Load parsed documents
2. Initialize SemanticChunker
3. Chunk all documents with adaptive overlap
4. Compute distribution statistics
5. Validate data integrity
6. Write outputs (chunks.json, chunking_warnings.json)
7. Print summary and random samples
"""

import json
import random
import statistics
from pathlib import Path
from datetime import datetime
from dataclasses import asdict

from src.models.schemas import ParsedDocument
from src.ingestion.chunker import SemanticChunker


def main():
    print("="*60)
    print("Day 4: Semantic Chunking + Distribution Analysis")
    print("="*60)
    
    # Step 1: Load parsed documents
    print("\n[Step 1] Loading parsed documents...")
    parsed_docs_path = Path("data/processed/parsed_docs.json")
    
    with open(parsed_docs_path, 'r', encoding='utf-8') as f:
        parsed_docs_data = json.load(f)
    
    parsed_docs = [ParsedDocument(**doc) for doc in parsed_docs_data]
    print(f"✅ Loaded {len(parsed_docs)} parsed documents")
    
    # Step 2: Initialize chunker
    print("\n[Step 2] Initializing SemanticChunker...")
    chunker = SemanticChunker(
        base_chunk_size=512,
        base_overlap=50,
        adaptive_overlap=True,
        table_heavy_threshold=200
    )
    print("✅ Initialized (512 tokens, adaptive overlap enabled, threshold=200)")
    
    # Step 3: Chunk all documents
    print("\n[Step 3] Chunking documents...")
    all_chunks = []
    all_warnings = []
    adaptive_overlap_docs = []
    
    for parsed_doc in parsed_docs:
        # Determine if adaptive overlap will be used
        overlap = chunker._determine_overlap(parsed_doc)
        if overlap == 100:
            adaptive_overlap_docs.append(parsed_doc.document_id)
        
        # Chunk document
        chunks, warnings = chunker.chunk_document(parsed_doc)
        
        all_chunks.extend(chunks)
        all_warnings.extend(warnings)
        
        print(f"  {parsed_doc.document_id}: {len(chunks)} chunks, {len(warnings)} warnings (overlap={overlap})")
    
    print(f"\n✅ Chunking complete")
    print(f"   Total chunks: {len(all_chunks)}")
    print(f"   Total warnings: {len(all_warnings)}")
    print(f"   Adaptive overlap used: {len(adaptive_overlap_docs)} documents")
    
    # Step 4: Compute distribution statistics
    print("\n[Step 4] Computing distribution statistics...")
    token_counts = [chunk.token_count for chunk in all_chunks]
    
    stats = {
        "total_chunks": len(all_chunks),
        "avg_tokens": statistics.mean(token_counts),
        "median_tokens": statistics.median(token_counts),
        "min_tokens": min(token_counts),
        "max_tokens": max(token_counts),
        "p50_tokens": statistics.median(token_counts),
        "p95_tokens": statistics.quantiles(token_counts, n=20)[18] if len(token_counts) > 20 else max(token_counts)
    }
    
    outliers = {
        "too_small": sum(1 for t in token_counts if t < 50),
        "too_large": sum(1 for t in token_counts if t > 800)
    }
    
    print("\n=== Distribution Statistics ===")
    print(f"Total chunks: {stats['total_chunks']}")
    print(f"Average: {stats['avg_tokens']:.1f} tokens")
    print(f"Median: {stats['median_tokens']:.1f} tokens")
    print(f"Min: {stats['min_tokens']} tokens")
    print(f"Max: {stats['max_tokens']} tokens")
    print(f"P50: {stats['p50_tokens']:.1f} tokens")
    print(f"P95: {stats['p95_tokens']:.1f} tokens")
    print(f"\nOutliers:")
    print(f"  Too small (<50): {outliers['too_small']}")
    print(f"  Too large (>800): {outliers['too_large']}")
    
    # Step 5: Validate data integrity
    print("\n[Step 5] Validating data integrity...")
    
    # Validation 1: No zero-token chunks
    zero_token_chunks = [c for c in all_chunks if c.token_count == 0]
    if zero_token_chunks:
        print(f"⚠️  WARNING: {len(zero_token_chunks)} chunks have 0 tokens")
    else:
        print("✅ No zero-token chunks")
    
    # Validation 2: No empty text
    empty_text_chunks = [c for c in all_chunks if not c.text.strip()]
    if empty_text_chunks:
        print(f"⚠️  WARNING: {len(empty_text_chunks)} chunks have empty text")
    else:
        print("✅ No empty-text chunks")
    
    # Validation 3: Token count sanity check (±10%)
    source_total_tokens = sum(
        chunker._count_tokens(doc.parsed_markdown) for doc in parsed_docs
    )
    chunk_total_tokens = sum(c.token_count for c in all_chunks)
    ratio = chunk_total_tokens / source_total_tokens
    
    print(f"\n=== Token Count Validation ===")
    print(f"Source documents: {source_total_tokens:,} tokens")
    print(f"Chunks (with overlap): {chunk_total_tokens:,} tokens")
    print(f"Ratio: {ratio:.2f}x")
    
    if ratio < 0.90 or ratio > 1.20:
        print(f"⚠️  WARNING: Ratio outside expected range (0.90-1.20)")
    else:
        print("✅ Token count validation passed")
    
    # Step 6: Write outputs
    print("\n[Step 6] Writing outputs...")
    
    # 6a. Write chunks.json
    chunks_path = Path("data/processed/chunks.json")
    chunks_data = [asdict(chunk) for chunk in all_chunks]
    
    with open(chunks_path, 'w', encoding='utf-8') as f:
        json.dump(chunks_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Wrote {len(all_chunks)} chunks to {chunks_path}")
    
    # 6b. Write chunking_warnings.json
    outlier_stats = {
        "too_small_count": sum(1 for w in all_warnings if w["warning_category"] == "outlier_too_small"),
        "too_large_count": sum(1 for w in all_warnings if w["warning_category"] == "outlier_too_large"),
        "table_split_count": sum(1 for w in all_warnings if w["warning_category"] == "table_split_detected")
    }
    
    warnings_output = {
        "metadata": {
            "total_documents": len(parsed_docs),
            "total_chunks": len(all_chunks),
            "total_warnings": len(all_warnings),
            "timestamp": datetime.now().isoformat()
        },
        "warnings": all_warnings,
        "outlier_stats": outlier_stats,
        "adaptive_overlap_documents": sorted(adaptive_overlap_docs)
    }
    
    warnings_path = Path("data/failures/chunking_warnings.json")
    with open(warnings_path, 'w', encoding='utf-8') as f:
        json.dump(warnings_output, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Wrote {len(all_warnings)} warnings to {warnings_path}")
    
    # Step 7: Print summary
    print("\n" + "="*60)
    print("CHUNKING COMPLETE")
    print("="*60)
    print(f"\nDocuments processed: {len(parsed_docs)}")
    print(f"Total chunks: {len(all_chunks)}")
    print(f"Avg tokens/chunk: {stats['avg_tokens']:.1f}")
    print(f"Warnings logged: {len(all_warnings)}")
    print(f"Adaptive overlap: {len(adaptive_overlap_docs)} documents")
    print(f"\nOutputs:")
    print(f"  - {chunks_path}")
    print(f"  - {warnings_path}")
    
    # Step 8: Print random sample chunks
    print("\n" + "="*60)
    print(f"RANDOM SAMPLE CHUNKS (n=10, seed=42)")
    print("="*60)
    
    random.seed(42)
    sample_size = min(10, len(all_chunks))
    samples = random.sample(all_chunks, sample_size)
    
    for i, chunk in enumerate(samples, 1):
        print(f"\n--- Sample {i}/{sample_size} ---")
        print(f"ID: {chunk.id}")
        print(f"Document: {chunk.document_id}")
        print(f"Index: {chunk.chunk_index}")
        print(f"Tokens: {chunk.token_count}")
        print(f"Authority: {chunk.authority_family} (Tier {chunk.tier})")
        print(f"Year: {chunk.year}")
        print(f"Drugs: {', '.join(chunk.drug_names) if chunk.drug_names else 'None'}")
        print(f"Text preview: {chunk.text[:200]}...")
    
    print("\n" + "="*60)
    print("Day 4 Complete — Proceed to manual inspection (Task 8)")
    print("="*60)


if __name__ == "__main__":
    main()
