"""
Day 4 Task 9: Distribution Analysis

Analyzes chunk distribution, warnings, and generates statistics for documentation.
"""

import json
import statistics
from pathlib import Path
from collections import defaultdict, Counter


def load_data():
    """Load chunks and warnings."""
    chunks_path = Path("data/processed/chunks.json")
    warnings_path = Path("data/failures/chunking_warnings.json")
    
    with open(chunks_path, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    
    with open(warnings_path, 'r', encoding='utf-8') as f:
        warnings_data = json.load(f)
    
    return chunks, warnings_data


def analyze_by_authority(chunks):
    """Analyze distribution by authority (FDA vs NICE)."""
    by_authority = defaultdict(list)
    
    for chunk in chunks:
        authority = chunk.get('authority_family', 'UNKNOWN')
        by_authority[authority].append(chunk['token_count'])
    
    results = {}
    for authority, token_counts in by_authority.items():
        results[authority] = {
            'count': len(token_counts),
            'avg': statistics.mean(token_counts),
            'median': statistics.median(token_counts),
            'min': min(token_counts),
            'max': max(token_counts),
            'std': statistics.stdev(token_counts) if len(token_counts) > 1 else 0
        }
    
    return results


def analyze_by_document(chunks):
    """Analyze distribution by document."""
    by_doc = defaultdict(list)
    
    for chunk in chunks:
        doc_id = chunk.get('document_id', 'UNKNOWN')
        by_doc[doc_id].append(chunk['token_count'])
    
    results = {}
    for doc_id, token_counts in by_doc.items():
        results[doc_id] = {
            'count': len(token_counts),
            'avg': statistics.mean(token_counts),
            'min': min(token_counts),
            'max': max(token_counts)
        }
    
    return results


def analyze_warnings(warnings_data, chunks):
    """Analyze warnings by category and document."""
    warnings = warnings_data.get('warnings', [])
    
    # By category
    by_category = Counter(w['warning_category'] for w in warnings)
    
    # By document
    by_doc = defaultdict(list)
    for warning in warnings:
        doc_id = warning['document_id']
        by_doc[doc_id].append(warning)
    
    # By severity
    by_severity = Counter(w['severity'] for w in warnings)
    
    # Get document chunk counts for comparison
    doc_chunk_counts = {}
    for chunk in chunks:
        doc_id = chunk['document_id']
        doc_chunk_counts[doc_id] = doc_chunk_counts.get(doc_id, 0) + 1
    
    # Calculate warning rate per document
    doc_warning_rates = {}
    for doc_id, doc_warnings in by_doc.items():
        chunk_count = doc_chunk_counts.get(doc_id, 1)
        doc_warning_rates[doc_id] = {
            'warning_count': len(doc_warnings),
            'chunk_count': chunk_count,
            'warning_rate': (len(doc_warnings) / chunk_count) * 100
        }
    
    return {
        'by_category': dict(by_category),
        'by_document': dict(by_doc),
        'by_severity': dict(by_severity),
        'warning_rates': doc_warning_rates
    }


def analyze_adaptive_overlap(warnings_data, chunks):
    """Analyze effectiveness of adaptive overlap."""
    adaptive_docs = warnings_data.get('adaptive_overlap_documents', [])
    
    # Separate chunks by overlap type
    adaptive_chunks = [c for c in chunks if c['document_id'] in adaptive_docs]
    standard_chunks = [c for c in chunks if c['document_id'] not in adaptive_docs]
    
    # Count table split warnings by overlap type
    warnings = warnings_data.get('warnings', [])
    table_split_warnings = [w for w in warnings if w['warning_category'] == 'table_split_detected']
    
    adaptive_table_splits = [w for w in table_split_warnings if w['document_id'] in adaptive_docs]
    standard_table_splits = [w for w in table_split_warnings if w['document_id'] not in adaptive_docs]
    
    # Calculate rates
    adaptive_rate = (len(adaptive_table_splits) / len(adaptive_chunks) * 100) if adaptive_chunks else 0
    standard_rate = (len(standard_table_splits) / len(standard_chunks) * 100) if standard_chunks else 0
    
    return {
        'adaptive_docs': len(adaptive_docs),
        'adaptive_chunks': len(adaptive_chunks),
        'standard_chunks': len(standard_chunks),
        'adaptive_table_splits': len(adaptive_table_splits),
        'standard_table_splits': len(standard_table_splits),
        'adaptive_split_rate': adaptive_rate,
        'standard_split_rate': standard_rate,
        'improvement': ((standard_rate - adaptive_rate) / standard_rate * 100) if standard_rate > 0 else 0
    }


def analyze_outliers(chunks, warnings_data):
    """Analyze outlier distribution."""
    outlier_stats = warnings_data.get('outlier_stats', {})
    
    # Find actual outlier chunks
    too_small = [c for c in chunks if c['token_count'] < 50]
    too_large = [c for c in chunks if c['token_count'] > 800]
    
    # Group by document
    small_by_doc = defaultdict(int)
    large_by_doc = defaultdict(int)
    
    for chunk in too_small:
        small_by_doc[chunk['document_id']] += 1
    
    for chunk in too_large:
        large_by_doc[chunk['document_id']] += 1
    
    return {
        'total_too_small': len(too_small),
        'total_too_large': len(too_large),
        'small_by_doc': dict(small_by_doc),
        'large_by_doc': dict(large_by_doc),
        'smallest_chunk': min((c['token_count'], c['id']) for c in chunks) if chunks else (0, 'NONE'),
        'largest_chunk': max((c['token_count'], c['id']) for c in chunks) if chunks else (0, 'NONE')
    }


def print_report(chunks, warnings_data):
    """Print comprehensive analysis report."""
    print("="*70)
    print("TASK 9: DISTRIBUTION ANALYSIS REPORT")
    print("="*70)
    
    # Global stats
    token_counts = [c['token_count'] for c in chunks]
    print("\n### GLOBAL STATISTICS")
    print(f"Total chunks: {len(chunks)}")
    print(f"Total documents: {len(set(c['document_id'] for c in chunks))}")
    print(f"Total warnings: {warnings_data['metadata']['total_warnings']}")
    print(f"Average tokens/chunk: {statistics.mean(token_counts):.1f}")
    print(f"Median tokens/chunk: {statistics.median(token_counts):.1f}")
    print(f"Min tokens: {min(token_counts)}")
    print(f"Max tokens: {max(token_counts)}")
    print(f"Std deviation: {statistics.stdev(token_counts):.1f}")
    
    if len(token_counts) > 20:
        quantiles = statistics.quantiles(token_counts, n=20)
        print(f"P25: {quantiles[4]:.1f}")
        print(f"P50: {quantiles[9]:.1f}")
        print(f"P75: {quantiles[14]:.1f}")
        print(f"P95: {quantiles[18]:.1f}")
    
    # By authority
    print("\n### DISTRIBUTION BY AUTHORITY")
    by_auth = analyze_by_authority(chunks)
    for authority, stats in sorted(by_auth.items()):
        print(f"\n{authority}:")
        print(f"  Chunks: {stats['count']}")
        print(f"  Avg tokens: {stats['avg']:.1f}")
        print(f"  Median tokens: {stats['median']:.1f}")
        print(f"  Range: {stats['min']}-{stats['max']}")
        print(f"  Std dev: {stats['std']:.1f}")
    
    # By document (top 10 by chunk count)
    print("\n### TOP 10 DOCUMENTS BY CHUNK COUNT")
    by_doc = analyze_by_document(chunks)
    sorted_docs = sorted(by_doc.items(), key=lambda x: x[1]['count'], reverse=True)[:10]
    for doc_id, stats in sorted_docs:
        print(f"\n{doc_id}:")
        print(f"  Chunks: {stats['count']}")
        print(f"  Avg tokens: {stats['avg']:.1f}")
        print(f"  Range: {stats['min']}-{stats['max']}")
    
    # Warning analysis
    print("\n### WARNING ANALYSIS")
    warning_analysis = analyze_warnings(warnings_data, chunks)
    
    print("\nBy Category:")
    for category, count in warning_analysis['by_category'].items():
        print(f"  {category}: {count}")
    
    print("\nBy Severity:")
    for severity, count in warning_analysis['by_severity'].items():
        print(f"  {severity}: {count}")
    
    print("\nDocuments with Warnings (sorted by rate):")
    sorted_rates = sorted(
        warning_analysis['warning_rates'].items(),
        key=lambda x: x[1]['warning_rate'],
        reverse=True
    )
    for doc_id, info in sorted_rates[:10]:
        print(f"  {doc_id}:")
        print(f"    Warnings: {info['warning_count']}/{info['chunk_count']} chunks ({info['warning_rate']:.1f}%)")
    
    # Adaptive overlap analysis
    print("\n### ADAPTIVE OVERLAP EFFECTIVENESS")
    overlap_analysis = analyze_adaptive_overlap(warnings_data, chunks)
    print(f"Adaptive overlap documents: {overlap_analysis['adaptive_docs']}")
    print(f"Adaptive overlap chunks: {overlap_analysis['adaptive_chunks']}")
    print(f"Standard overlap chunks: {overlap_analysis['standard_chunks']}")
    print(f"\nTable Split Warnings:")
    print(f"  Adaptive (100-token overlap): {overlap_analysis['adaptive_table_splits']} ({overlap_analysis['adaptive_split_rate']:.2f}%)")
    print(f"  Standard (50-token overlap): {overlap_analysis['standard_table_splits']} ({overlap_analysis['standard_split_rate']:.2f}%)")
    if overlap_analysis['standard_split_rate'] > 0:
        print(f"  Improvement: {overlap_analysis['improvement']:.1f}% reduction in split rate")
    else:
        print(f"  Note: No standard table splits for comparison")
    
    # Outlier analysis
    print("\n### OUTLIER ANALYSIS")
    outlier_analysis = analyze_outliers(chunks, warnings_data)
    print(f"Too small (<50 tokens): {outlier_analysis['total_too_small']}")
    print(f"Too large (>800 tokens): {outlier_analysis['total_too_large']}")
    print(f"Smallest chunk: {outlier_analysis['smallest_chunk'][0]} tokens ({outlier_analysis['smallest_chunk'][1]})")
    print(f"Largest chunk: {outlier_analysis['largest_chunk'][0]} tokens ({outlier_analysis['largest_chunk'][1]})")
    
    if outlier_analysis['small_by_doc']:
        print("\nToo Small by Document:")
        for doc_id, count in sorted(outlier_analysis['small_by_doc'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {doc_id}: {count}")
    
    if outlier_analysis['large_by_doc']:
        print("\nToo Large by Document:")
        for doc_id, count in sorted(outlier_analysis['large_by_doc'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {doc_id}: {count}")
    
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    print("\nUse this data to write docs/chunking_analysis.md")


def main():
    print("Loading data...")
    chunks, warnings_data = load_data()
    print(f"✅ Loaded {len(chunks)} chunks, {warnings_data['metadata']['total_warnings']} warnings\n")
    
    print_report(chunks, warnings_data)


if __name__ == "__main__":
    main()
