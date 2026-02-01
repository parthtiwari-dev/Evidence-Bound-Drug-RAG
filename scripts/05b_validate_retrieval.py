#!/usr/bin/env python3
"""
Script: 05b_validate_retrieval.py
Purpose: Comprehensive validation of retrieval results from Task 6
Validates: metadata, table integrity, drug accuracy, retriever comparison

This automates Task 7.1, 7.2, 7.4 and prepares data for manual Task 7.3
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Any
import statistics

def load_retrieval_results(filepath: str = "data/retrieval_results.json") -> Dict:
    """Load retrieval results from Task 6."""
    print("="*80)
    print("LOADING RETRIEVAL RESULTS")
    print("="*80)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total_queries = len(data)
    print(f"\n✅ Loaded {total_queries} queries from {filepath}")
    
    return data


def validate_metadata(data: Dict, sample_size: int = 10) -> Dict[str, Any]:
    """
    Task 7.1: Metadata Propagation Check
    
    Validates that all chunks have required metadata fields.
    Samples random chunks across all queries and retrievers.
    
    Returns:
        dict: Validation results with pass/fail status
    """
    print("\n" + "="*80)
    print("TASK 7.1: METADATA PROPAGATION CHECK")
    print("="*80)
    
    required_fields = ['authority_family', 'tier', 'year', 'drug_names', 'chunk_id']
    
    # Collect all chunks
    all_chunks = []
    for query_key, query_data in data.items():
        for retriever in ['vector', 'bm25', 'hybrid']:
            for chunk in query_data[retriever]['results']:
                all_chunks.append(chunk)
    
    # Sample random chunks
    sampled_chunks = random.sample(all_chunks, min(sample_size, len(all_chunks)))
    
    print(f"\nInspecting {len(sampled_chunks)} random chunks:\n")
    
    validation_results = []
    for i, chunk in enumerate(sampled_chunks, 1):
        missing_fields = []
        for field in required_fields:
            if field not in chunk:
                missing_fields.append(field)
        
        validation_results.append({
            'chunk_id': chunk['chunk_id'],
            'all_fields_present': len(missing_fields) == 0,
            'missing_fields': missing_fields
        })
        
        status = "✅" if len(missing_fields) == 0 else "❌"
        print(f"Chunk {i}: {chunk['chunk_id'][:50]}... {status}")
    
    passed = sum(1 for r in validation_results if r['all_fields_present'])
    print(f"\nRESULT: {passed}/{len(sampled_chunks)} chunks have all required metadata")
    
    if passed == len(sampled_chunks):
        print("✅ PASS: All chunks have complete metadata")
        status = "PASS"
    else:
        print("❌ FAIL: Some chunks missing metadata")
        status = "FAIL"
    
    return {
        "status": status,
        "total_checked": len(sampled_chunks),
        "passed": passed,
        "failed": len(sampled_chunks) - passed,
        "required_fields": required_fields,
        "details": validation_results
    }


def extract_table_chunks(data: Dict, num_samples: int = 3) -> List[Dict]:
    """
    Task 7.2: Extract table chunks for manual inspection
    
    Identifies chunks containing markdown tables (with '|' character)
    and extracts samples for manual quality review.
    
    Returns:
        list: Table chunks for manual inspection
    """
    print("\n" + "="*80)
    print("TASK 7.2: TABLE INTEGRITY CHECK")
    print("="*80)
    
    # Find all chunks with tables
    table_chunks = []
    seen_docs = set()
    
    for query_key, query_data in data.items():
        for retriever in ['vector', 'bm25', 'hybrid']:
            for chunk in query_data[retriever]['results']:
                # Check for markdown table syntax
                if '|' in chunk['text_preview'] and chunk['document_id'] not in seen_docs:
                    table_chunks.append(chunk)
                    seen_docs.add(chunk['document_id'])
    
    # Select diverse samples
    selected_chunks = table_chunks[:num_samples] if len(table_chunks) >= num_samples else table_chunks
    
    print(f"\nFound {len(table_chunks)} chunks with table markers ('|')")
    print(f"Selected {len(selected_chunks)} for manual inspection:\n")
    
    for i, chunk in enumerate(selected_chunks, 1):
        print(f"\n{'='*80}")
        print(f"TABLE CHUNK {i}")
        print(f"{'='*80}")
        print(f"Chunk ID: {chunk['chunk_id']}")
        print(f"Document: {chunk['document_id']}")
        print(f"Drug: {chunk['drug_names']}")
        print(f"\nPREVIEW:")
        print("-" * 80)
        print(chunk['text_preview'][:400])
        print("-" * 80)
    
    print(f"\n\n{'='*80}")
    print("👉 MANUAL ACTION REQUIRED")
    print(f"{'='*80}")
    print("\nFor each table chunk above, rate the quality:")
    print("  GOOD  = Table is readable, columns aligned, no major issues")
    print("  FAIR  = Some formatting issues but still understandable")
    print("  POOR  = Catastrophic splits, unreadable, or major structural problems")
    
    return selected_chunks


def calculate_drug_accuracy(data: Dict) -> Dict[str, Any]:
    """
    Task 7.4: Retriever Comparison - Drug Accuracy
    
    For each query, checks if top-5 results are from the correct drug.
    Compares vector, BM25, and hybrid retrievers.
    
    Returns:
        dict: Drug accuracy statistics per retriever
    """
    print("\n" + "="*80)
    print("TASK 7.4: RETRIEVER COMPARISON - DRUG ACCURACY")
    print("="*80)
    
    comparison_data = []
    
    for query_key, query_data in data.items():
        query_text = query_data['query_text']
        expected_drug = query_data['drug']
        
        print(f"\n{query_key.upper()}: \"{query_text}\"")
        print(f"Expected Drug: {expected_drug}")
        print("-" * 80)
        
        query_results = {
            'query': query_text,
            'expected_drug': expected_drug
        }
        
        for retriever in ['vector', 'bm25', 'hybrid']:
            results = query_data[retriever]['results'][:5]
            
            # Count correct drug matches
            correct_count = sum(
                1 for r in results 
                if expected_drug in r['drug_names']
            )
            
            accuracy = correct_count / 5
            query_results[f'{retriever}_accuracy'] = correct_count
            
            print(f"{retriever.upper():8} {correct_count}/5 ({accuracy*100:.0f}%)", end="  ")
            
            # Show top-5 drugs
            drugs = [r['drug_names'][0] if r['drug_names'] else 'unknown' for r in results]
            drugs_str = ', '.join(drugs[:3])
            print(f"[{drugs_str}...]")
        
        comparison_data.append(query_results)
    
    # Calculate averages
    print("\n" + "="*80)
    print("OVERALL DRUG ACCURACY (TOP-5)")
    print("="*80)
    
    avg_results = {}
    for retriever in ['vector', 'bm25', 'hybrid']:
        total_correct = sum(q[f'{retriever}_accuracy'] for q in comparison_data)
        total_possible = len(comparison_data) * 5
        avg_accuracy = total_correct / total_possible
        
        avg_results[retriever] = {
            'total_correct': total_correct,
            'total_possible': total_possible,
            'accuracy': avg_accuracy
        }
        
        print(f"{retriever.upper():8} {total_correct}/{total_possible} ({avg_accuracy*100:.1f}%)")
    
    # Identify best performer
    best_retriever = max(avg_results.items(), key=lambda x: x[1]['accuracy'])
    print(f"\n🏆 Best Performer: {best_retriever[0].upper()} with {best_retriever[1]['accuracy']*100:.1f}% accuracy")
    
    return {
        'per_query': comparison_data,
        'overall': avg_results,
        'best_performer': best_retriever[0]
    }


def calculate_retriever_statistics(data: Dict) -> Dict[str, Any]:
    """
    Calculate latency and score statistics for each retriever.
    
    Returns:
        dict: Latency and score statistics
    """
    print("\n" + "="*80)
    print("RETRIEVER PERFORMANCE STATISTICS")
    print("="*80)
    
    stats = {
        'vector': {'latencies': [], 'scores': []},
        'bm25': {'latencies': [], 'scores': []},
        'hybrid': {'latencies': [], 'scores': []}
    }
    
    for query_key, query_data in data.items():
        for retriever in ['vector', 'bm25', 'hybrid']:
            stats[retriever]['latencies'].append(query_data[retriever]['latency_ms'])
            
            # Collect scores from results
            for result in query_data[retriever]['results']:
                stats[retriever]['scores'].append(result['score'])
    
    # Calculate statistics
    summary = {}
    for retriever in ['vector', 'bm25', 'hybrid']:
        latencies = stats[retriever]['latencies']
        scores = stats[retriever]['scores']
        
        summary[retriever] = {
            'latency': {
                'mean': round(statistics.mean(latencies), 2),
                'min': round(min(latencies), 2),
                'max': round(max(latencies), 2)
            },
            'score': {
                'mean': round(statistics.mean(scores), 4),
                'min': round(min(scores), 4),
                'max': round(max(scores), 4),
                'std_dev': round(statistics.stdev(scores), 4)
            }
        }
        
        print(f"\n{retriever.upper()}:")
        print(f"  Latency: {summary[retriever]['latency']['mean']}ms (range: {summary[retriever]['latency']['min']}-{summary[retriever]['latency']['max']}ms)")
        print(f"  Scores:  Mean={summary[retriever]['score']['mean']}, StdDev={summary[retriever]['score']['std_dev']}")
    
    return summary


def extract_relevance_chunks(data: Dict, query_id: str = 'query_1') -> List[Dict]:
    """
    Task 7.3: Extract chunks for manual relevance scoring
    
    Extracts top-5 hybrid results for specified query for manual
    relevance assessment (HIGH/MEDIUM/LOW).
    
    Args:
        data: Retrieval results
        query_id: Which query to extract (default: query_1 for baseline)
    
    Returns:
        list: Chunks for manual relevance scoring
    """
    print("\n" + "="*80)
    print(f"TASK 7.3: RELEVANCE SCORING PREPARATION ({query_id})")
    print("="*80)
    
    query_data = data[query_id]
    query_text = query_data['query_text']
    expected_drug = query_data['drug']
    
    print(f"\nQuery: \"{query_text}\"")
    print(f"Expected Drug: {expected_drug}")
    print("\nTOP-5 HYBRID RESULTS (for manual scoring):\n")
    
    hybrid_results = query_data['hybrid']['results'][:5]
    
    for i, chunk in enumerate(hybrid_results, 1):
        print(f"\n{'='*80}")
        print(f"CHUNK {i}/5")
        print(f"{'='*80}")
        print(f"Rank: {chunk['rank']}")
        print(f"Score: {chunk['score']:.4f}")
        print(f"Drug: {chunk['drug_names'][0] if chunk['drug_names'] else 'unknown'}")
        print(f"Document: {chunk['document_id']}")
        print(f"\nTEXT PREVIEW:")
        print("-" * 80)
        print(chunk['text_preview'][:400])
        print("-" * 80)
    
    print(f"\n\n{'='*80}")
    print("👉 MANUAL ACTION REQUIRED")
    print(f"{'='*80}")
    print(f"\nScore each chunk for relevance to: \"{query_text}\"")
    print("\nScoring criteria:")
    print("  HIGH   = Directly answers the question")
    print("  MEDIUM = Related but indirect")
    print("  LOW    = Off-topic or wrong drug")
    
    return hybrid_results


def generate_validation_report(
    metadata_results: Dict,
    drug_accuracy: Dict,
    performance_stats: Dict
) -> str:
    """Generate a comprehensive validation report."""
    
    report = []
    report.append("="*80)
    report.append("RETRIEVAL VALIDATION REPORT")
    report.append("="*80)
    
    # Metadata validation
    report.append("\n## TASK 7.1: METADATA VALIDATION")
    report.append(f"Status: {metadata_results['status']}")
    report.append(f"Checked: {metadata_results['total_checked']} chunks")
    report.append(f"Passed: {metadata_results['passed']}/{metadata_results['total_checked']}")
    
    # Drug accuracy
    report.append("\n## TASK 7.4: DRUG ACCURACY")
    for retriever, stats in drug_accuracy['overall'].items():
        report.append(f"{retriever.upper():8} {stats['total_correct']}/{stats['total_possible']} ({stats['accuracy']*100:.1f}%)")
    report.append(f"\nBest Performer: {drug_accuracy['best_performer'].upper()}")
    
    # Performance statistics
    report.append("\n## RETRIEVER PERFORMANCE")
    for retriever, stats in performance_stats.items():
        report.append(f"\n{retriever.upper()}:")
        report.append(f"  Avg Latency: {stats['latency']['mean']}ms")
        report.append(f"  Avg Score: {stats['score']['mean']}")
    
    report.append("\n" + "="*80)
    
    return "\n".join(report)


def main():
    """Main execution function."""
    print("\n" + "="*80)
    print("RETRIEVAL VALIDATION SUITE")
    print("Validates results from Task 6 (05a_test_retrieval.py)")
    print("="*80)
    
    try:
        # Load results
        data = load_retrieval_results("data/retrieval_results.json")
        
        # Task 7.1: Metadata validation
        metadata_results = validate_metadata(data, sample_size=10)
        
        # Task 7.2: Extract table chunks for manual inspection
        table_chunks = extract_table_chunks(data, num_samples=3)
        
        # Task 7.4: Calculate drug accuracy
        drug_accuracy = calculate_drug_accuracy(data)
        
        # Performance statistics
        performance_stats = calculate_retriever_statistics(data)
        
        # Task 7.3: Extract chunks for relevance scoring (baseline query only)
        relevance_chunks = extract_relevance_chunks(data, query_id='query_1')
        
        # Generate report
        print("\n" + "="*80)
        print("GENERATING VALIDATION REPORT")
        print("="*80)
        
        report = generate_validation_report(
            metadata_results,
            drug_accuracy,
            performance_stats
        )
        
        print("\n" + report)
        
        # Save results
        validation_output = {
            "metadata_validation": metadata_results,
            "drug_accuracy": drug_accuracy,
            "performance_stats": performance_stats,
            "table_chunks_count": len(table_chunks),
            "report": report
        }
        
        output_path = Path("data/validation_results.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(validation_output, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Validation results saved to: {output_path}")
        
        print("\n" + "="*80)
        print("✅ VALIDATION COMPLETE")
        print("="*80)
        print("\nNext steps:")
        print("  1. Review table chunks and rate quality (GOOD/FAIR/POOR)")
        print("  2. Review relevance chunks and score (HIGH/MEDIUM/LOW)")
        print("  3. Run edge case tests: python scripts/05c_edge_case_test.py")
        print("  4. Run weight tuning: python scripts/05d_tune_weights.py")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error during validation: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
