"""
Diagnose Context Precision Issues
Analyzes which queries have low context precision and why.
"""
import json
from pathlib import Path
from collections import defaultdict

# Load results
with open('data/evaluation/ragas_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("=" * 80)
print("CONTEXT PRECISION DIAGNOSTIC REPORT")
print("=" * 80)

precision_scores = data['per_query_scores']['context_precision']
faithfulness_scores = data['per_query_scores']['faithfulness']
relevancy_scores = data['per_query_scores']['answer_relevancy']
metadata = data['metadata']

# Load test queries to get the actual question text
with open('data/evaluation/test_queries.json', 'r', encoding='utf-8') as f:
    queries_data = json.load(f)
    queries_map = {q['query_id']: q['query_text'] for q in queries_data['queries']}

print("\n" + "="*80)
print("QUERIES WITH LOW CONTEXT PRECISION (<0.7)")
print("="*80 + "\n")

low_precision = []
for i, (prec, faith, rel, meta) in enumerate(zip(precision_scores, faithfulness_scores, relevancy_scores, metadata)):
    if prec is not None and prec < 0.7:
        query_id = meta['query_id']
        low_precision.append({
            'id': query_id,
            'query': queries_map.get(query_id, 'Unknown'),
            'precision': prec,
            'faithfulness': faith,
            'relevancy': rel,
            'category': meta['category'],
            'expected_drug': meta['expected_drug'],
            'chunks_retrieved': meta['chunks_retrieved'],
            'cited_chunks': meta['cited_chunks'],
            'is_refusal': meta['is_refusal']
        })

print("Found {}/20 queries with low context precision\n".format(len(low_precision)))

for q in sorted(low_precision, key=lambda x: x['precision']):
    print("Query {}: {}".format(q['id'], q['query']))
    print("  Expected Drug: {}".format(q['expected_drug']))
    print("  Category: {}".format(q['category']))
    print("  Context Precision: {:.3f} ❌".format(q['precision']))
    
    # Fixed faithfulness display
    faith_display = '{:.3f}'.format(q['faithfulness']) if q['faithfulness'] is not None else 'N/A'
    print("  Faithfulness: {}".format(faith_display))
    
    # Fixed relevancy display
    rel_display = '{:.3f}'.format(q['relevancy']) if q['relevancy'] is not None else 'N/A'
    print("  Relevancy: {}".format(rel_display))
    
    print("  Retrieved: {} chunks".format(q['chunks_retrieved']))
    print("  Cited: {} chunks".format(q['cited_chunks']))
    print("  Refusal: {}".format(q['is_refusal']))
    print()

# Aggregate by category
category_precision = defaultdict(list)
for prec, meta in zip(precision_scores, metadata):
    if prec is not None:
        category_precision[meta['category']].append(prec)

print("="*80)
print("CONTEXT PRECISION BY CATEGORY")
print("="*80 + "\n")

for cat in sorted(category_precision.keys()):
    scores = category_precision[cat]
    avg = sum(scores) / len(scores)
    below_70 = sum(1 for s in scores if s < 0.7)
    print("{:20s}: {:.3f} (n={}, {} below 0.7)".format(cat, avg, len(scores), below_70))

print("\n" + "="*80)
print("ROOT CAUSE ANALYSIS")
print("="*80 + "\n")

# Analyze patterns
refusal_low_prec = sum(1 for q in low_precision if q['is_refusal'])
cited_but_low = [q for q in low_precision if not q['is_refusal'] and q['cited_chunks'] > 0]

print("1. Refusals with low precision: {}/{}".format(refusal_low_prec, len(low_precision)))
print("   → These are EXPECTED (no answer = no relevant context)")
print()
print("2. Answered queries with low precision: {}/{}".format(len(cited_but_low), len(low_precision)))
print("   → These need fixing (answered but context not ideal)")
print()

if cited_but_low:
    print("Queries that answered but had poor context:")
    for q in cited_but_low:
        print("   - Query {}: {}...".format(q['id'], q['query'][:60]))
        print("     Precision: {:.3f}, Cited: {}/{}".format(
            q['precision'], q['cited_chunks'], q['chunks_retrieved']))

print("\n" + "="*80)
print("RECOMMENDATIONS")
print("="*80 + "\n")

if refusal_low_prec >= len(low_precision) * 0.6:
    print("✅ Most low precision scores are from refusals (GOOD - expected behavior)")
else:
    print("⚠️  Many answered queries have low precision - retrieval needs improvement")

print("\nTo improve context precision:")
print("1. Increase top_k from 8 to 10-12 (more context options)")
print("2. Add reranking with cross-encoder")
print("3. Improve chunk quality (better semantic boundaries)")
print("4. Filter retrieved chunks by minimum similarity threshold")
