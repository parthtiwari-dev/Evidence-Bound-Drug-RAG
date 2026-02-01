"""
Performance Benchmark Script for /ask API Endpoint
Measures latency consistency, throughput, and performance under load.

Different from test script:
- Focuses on performance metrics (not validation)
- Runs multiple iterations per query
- Measures consistency (stddev)
- Tests different configurations
"""

import requests
import time
import statistics
from typing import Dict, List
import json

# Configuration
API_URL = "http://localhost:8000/ask"
ITERATIONS_PER_QUERY = 3  # Run each query 3 times

# Test queries (representative sample)
BENCHMARK_QUERIES = [
    "What are the side effects of warfarin?",
    "What are the contraindications for atorvastatin?",
    "What drugs interact with lisinopril?",
    "How does metformin work?",
    "What is the recommended dosage of ciprofloxacin?"
]

def benchmark_single_query(query: str, top_k: int = 5, retriever_type: str = "hybrid") -> Dict:
    """
    Run a single query multiple times and collect latency statistics.
    """
    latencies = []
    retrieval_times = []
    generation_times = []
    costs = []
    chunks_cited = []
    refusals = []
    
    print(f"\n{'─'*80}")
    print(f"🔍 Benchmarking: {query[:60]}...")
    print(f"   Config: top_k={top_k}, retriever={retriever_type}")
    print(f"   Iterations: {ITERATIONS_PER_QUERY}")
    
    for i in range(ITERATIONS_PER_QUERY):
        try:
            start = time.time()
            response = requests.post(
                API_URL,
                json={
                    "query": query,
                    "top_k": top_k,
                    "retriever_type": retriever_type
                },
                timeout=30
            )
            request_time = (time.time() - start) * 1000
            
            if response.status_code == 200:
                data = response.json()
                
                # Collect metrics
                latencies.append(data.get("total_latency_ms", 0))
                retrieval_times.append(data.get("retrieval_time_ms", 0))
                generation_times.append(data.get("generation_time_ms", 0))
                costs.append(data.get("cost_usd", 0))
                chunks_cited.append(data.get("chunks_cited", 0))
                refusals.append(1 if data.get("is_refusal") else 0)
                
                print(f"   Iteration {i+1}: {data.get('total_latency_ms'):.1f}ms "
                      f"(retrieval: {data.get('retrieval_time_ms'):.1f}ms, "
                      f"generation: {data.get('generation_time_ms'):.1f}ms)")
            else:
                print(f"   ❌ Iteration {i+1} failed: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Iteration {i+1} error: {str(e)}")
    
    # Calculate statistics
    if not latencies:
        return None
    
    result = {
        "query": query,
        "config": {
            "top_k": top_k,
            "retriever_type": retriever_type,
            "iterations": ITERATIONS_PER_QUERY
        },
        "latency": {
            "avg_ms": statistics.mean(latencies),
            "min_ms": min(latencies),
            "max_ms": max(latencies),
            "stddev_ms": statistics.stdev(latencies) if len(latencies) > 1 else 0,
            "variance_pct": (statistics.stdev(latencies) / statistics.mean(latencies) * 100) if len(latencies) > 1 else 0
        },
        "retrieval": {
            "avg_ms": statistics.mean(retrieval_times),
            "pct_of_total": (statistics.mean(retrieval_times) / statistics.mean(latencies) * 100)
        },
        "generation": {
            "avg_ms": statistics.mean(generation_times),
            "pct_of_total": (statistics.mean(generation_times) / statistics.mean(latencies) * 100)
        },
        "results": {
            "avg_chunks_cited": statistics.mean(chunks_cited),
            "refusal_rate": statistics.mean(refusals) * 100,
            "avg_cost_usd": statistics.mean(costs)
        }
    }
    
    # Print summary
    print(f"\n   📊 Results:")
    print(f"      Latency: {result['latency']['avg_ms']:.1f}ms ± {result['latency']['stddev_ms']:.1f}ms")
    print(f"      Range: {result['latency']['min_ms']:.1f}ms - {result['latency']['max_ms']:.1f}ms")
    print(f"      Consistency: ±{result['latency']['variance_pct']:.1f}% variance")
    print(f"      Retrieval: {result['retrieval']['pct_of_total']:.1f}% of total time")
    print(f"      Generation: {result['generation']['pct_of_total']:.1f}% of total time")
    
    return result

def benchmark_configuration_comparison():
    """
    Test different retriever configurations on same query.
    """
    query = "What are the side effects of warfarin?"
    configs = [
        ("vector", 5),
        ("bm25", 5),
        ("hybrid", 5),
        ("hybrid", 10)  # Test with more chunks
    ]
    
    print("\n" + "="*80)
    print("🔬 CONFIGURATION COMPARISON")
    print("="*80)
    print(f"Query: {query}")
    
    results = []
    for retriever_type, top_k in configs:
        result = benchmark_single_query(query, top_k=top_k, retriever_type=retriever_type)
        if result:
            results.append(result)
        time.sleep(1)  # Small delay between configs
    
    # Compare results
    print("\n" + "─"*80)
    print("CONFIGURATION COMPARISON:")
    print(f"{'Config':<20} {'Latency (ms)':<15} {'Retrieval %':<15} {'Generation %':<15}")
    print("─"*80)
    
    for r in results:
        config_name = f"{r['config']['retriever_type']} (k={r['config']['top_k']})"
        print(f"{config_name:<20} "
              f"{r['latency']['avg_ms']:<15.1f} "
              f"{r['retrieval']['pct_of_total']:<15.1f} "
              f"{r['generation']['pct_of_total']:<15.1f}")

def main():
    print("\n" + "="*80)
    print("🚀 API PERFORMANCE BENCHMARK")
    print("="*80)
    print(f"\nEndpoint: {API_URL}")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check API health
    try:
        health = requests.get("http://localhost:8000/health", timeout=5)
        if health.status_code == 200:
            print("✅ API is running")
        else:
            print(f"⚠️ API health check returned {health.status_code}")
    except:
        print("❌ ERROR: API is not running at http://localhost:8000")
        print("   Start with: python src/api/main.py")
        return
    
    # Benchmark standard queries
    print("\n" + "="*80)
    print("📊 STANDARD QUERY BENCHMARKS")
    print("="*80)
    
    all_results = []
    for query in BENCHMARK_QUERIES:
        result = benchmark_single_query(query, top_k=5, retriever_type="hybrid")
        if result:
            all_results.append(result)
        time.sleep(0.5)  # Small delay between queries
    
    # Overall statistics
    if all_results:
        print("\n" + "="*80)
        print("📈 OVERALL STATISTICS")
        print("="*80)
        
        all_latencies = [r["latency"]["avg_ms"] for r in all_results]
        all_retrieval_times = [r["retrieval"]["avg_ms"] for r in all_results]
        all_generation_times = [r["generation"]["avg_ms"] for r in all_results]
        all_refusal_rates = [r["results"]["refusal_rate"] for r in all_results]
        
        print(f"\n📊 Latency:")
        print(f"   Average: {statistics.mean(all_latencies):.1f}ms")
        print(f"   Median: {statistics.median(all_latencies):.1f}ms")
        print(f"   Min: {min(all_latencies):.1f}ms")
        print(f"   Max: {max(all_latencies):.1f}ms")
        print(f"   Stddev: ±{statistics.stdev(all_latencies):.1f}ms")
        
        print(f"\n⚡ Component Breakdown:")
        print(f"   Avg Retrieval: {statistics.mean(all_retrieval_times):.1f}ms "
              f"({statistics.mean(all_retrieval_times)/statistics.mean(all_latencies)*100:.1f}%)")
        print(f"   Avg Generation: {statistics.mean(all_generation_times):.1f}ms "
              f"({statistics.mean(all_generation_times)/statistics.mean(all_latencies)*100:.1f}%)")
        
        print(f"\n🎯 Quality Metrics:")
        print(f"   Avg refusal rate: {statistics.mean(all_refusal_rates):.1f}%")
        print(f"   Avg chunks cited: {statistics.mean([r['results']['avg_chunks_cited'] for r in all_results]):.1f}")
        
        print(f"\n💰 Cost:")
        print(f"   Total queries: {len(BENCHMARK_QUERIES) * ITERATIONS_PER_QUERY}")
        print(f"   Total cost: $0.00 (Groq free tier)")
        print(f"   Cost per query: $0.00")
    
    # Configuration comparison
    benchmark_configuration_comparison()
    
    # Save results
    output_file = "tests/api/benchmark_results.json"
    with open(output_file, 'w') as f:
        json.dump({
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "total_queries": len(BENCHMARK_QUERIES) * ITERATIONS_PER_QUERY,
            "results": all_results,
            "summary": {
                "avg_latency_ms": statistics.mean(all_latencies),
                "median_latency_ms": statistics.median(all_latencies),
                "stddev_latency_ms": statistics.stdev(all_latencies),
                "avg_retrieval_ms": statistics.mean(all_retrieval_times),
                "avg_generation_ms": statistics.mean(all_generation_times),
                "refusal_rate_pct": statistics.mean(all_refusal_rates)
            }
        }, f, indent=2)
    
    print(f"\n📄 Results saved to: {output_file}")
    
    print("\n" + "="*80)
    print("✅ BENCHMARK COMPLETE")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
