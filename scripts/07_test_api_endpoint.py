"""
Test script for /ask API endpoint
Tests 5 different query types and validates responses
"""

import requests
import json
import time
from typing import Dict, List

# Configuration
API_URL = "http://localhost:8000/ask"
OUTPUT_FILE = "tests/api/automated_test_results.json"

# Test queries
TEST_CASES = [
    {
        "id": "test_1",
        "name": "Factual: Warfarin Side Effects",
        "query": "What are the side effects of warfarin?",
        "top_k": 5,
        "retriever_type": "hybrid",
        "expected_refusal": False,
        "expected_authorities": ["FDA"]
    },
    {
        "id": "test_2",
        "name": "Medical Advice: Best BP Medication (Should Refuse)",
        "query": "What is the best medication for high blood pressure?",
        "top_k": 5,
        "retriever_type": "hybrid",
        "expected_refusal": True,
        "expected_authorities": ["NICE", "FDA"]
    },
    {
        "id": "test_3",
        "name": "Factual: Lisinopril Interactions",
        "query": "What drugs interact with lisinopril?",
        "top_k": 5,
        "retriever_type": "hybrid",
        "expected_refusal": False,
        "expected_authorities": ["FDA"]
    },
    {
        "id": "test_4",
        "name": "Partial Info: Atorvastatin Contraindications",
        "query": "What are the contraindications for atorvastatin?",
        "top_k": 5,
        "retriever_type": "hybrid",
        "expected_refusal": True,  # Should refuse due to missing explicit info
        "expected_authorities": ["FDA", "NICE"]
    },
    {
        "id": "test_5",
        "name": "Mechanism: How Metformin Works",
        "query": "How does metformin work?",
        "top_k": 5,
        "retriever_type": "vector",  # Test vector-only retrieval
        "expected_refusal": True,  # Mechanism not in corpus
        "expected_authorities": ["FDA"]
    }
]

def run_test(test_case: Dict) -> Dict:
    """Run a single test case and return results"""
    print(f"\n{'='*80}")
    print(f"🔍 TEST: {test_case['name']}")
    print(f"Query: {test_case['query']}")
    print('='*80)
    
    start_time = time.time()
    
    try:
        # Make API request
        response = requests.post(
            API_URL,
            json={
                "query": test_case["query"],
                "top_k": test_case["top_k"],
                "retriever_type": test_case["retriever_type"]
            },
            timeout=30
        )
        
        request_time = (time.time() - start_time) * 1000
        
        # Parse response
        if response.status_code == 200:
            data = response.json()
            
            # Validate response
            validations = {
                "status_code": response.status_code == 200,
                "has_answer": "answer" in data and len(data["answer"]) > 0,
                "has_citations": "cited_chunks" in data and len(data["cited_chunks"]) > 0,
                "refusal_matches": data.get("is_refusal") == test_case["expected_refusal"],
                "has_authorities": "authorities_used" in data,
                "latency_ok": data.get("total_latency_ms", 0) < 10000  # Under 10s
            }
            
            all_passed = all(validations.values())
            
            # Print results
            print(f"\n✅ Status: {response.status_code}")
            print(f"✅ Is Refusal: {data.get('is_refusal')} (expected: {test_case['expected_refusal']})")
            print(f"✅ Chunks Cited: {len(data.get('cited_chunks', []))}")
            print(f"✅ Authorities: {data.get('authorities_used')}")
            print(f"✅ Latency: {data.get('total_latency_ms')}ms (request: {request_time:.1f}ms)")
            print(f"✅ Cost: ${data.get('cost_usd', 0)}")
            print(f"✅ Total Tokens: {data.get('total_tokens', 0)}")
            print(f"\n📝 Answer Preview: {data.get('answer')[:200]}...")
            
            print(f"\n{'─'*80}")
            print(f"VALIDATION RESULTS:")
            for check, passed in validations.items():
                status = "✅ PASS" if passed else "❌ FAIL"
                print(f"  {status} - {check}")
            print(f"{'─'*80}")
            
            if all_passed:
                print(f"✅ TEST PASSED")
            else:
                print(f"❌ TEST FAILED")
            
            return {
                "test_id": test_case["id"],
                "test_name": test_case["name"],
                "status": "PASS" if all_passed else "FAIL",
                "response": data,
                "validations": validations,
                "request_time_ms": request_time
            }
            
        else:
            print(f"❌ ERROR: Status {response.status_code}")
            print(f"Response: {response.text}")
            return {
                "test_id": test_case["id"],
                "test_name": test_case["name"],
                "status": "FAIL",
                "error": f"HTTP {response.status_code}: {response.text}",
                "request_time_ms": request_time
            }
            
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
        return {
            "test_id": test_case["id"],
            "test_name": test_case["name"],
            "status": "FAIL",
            "error": str(e),
            "request_time_ms": (time.time() - start_time) * 1000
        }

def main():
    """Run all tests and generate report"""
    print("\n" + "="*80)
    print("🚀 EVIDENCE-BOUND DRUG RAG API - AUTOMATED TEST SUITE")
    print("="*80)
    print(f"\nEndpoint: {API_URL}")
    print(f"Total tests: {len(TEST_CASES)}")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if API is running
    try:
        health_check = requests.get("http://localhost:8000/health", timeout=5)
        if health_check.status_code == 200:
            print(f"✅ API is running")
        else:
            print(f"⚠️ API health check returned: {health_check.status_code}")
    except:
        print(f"❌ ERROR: API is not running at http://localhost:8000")
        print(f"   Start the API with: python src/api/main.py")
        return
    
    # Run all tests
    results = []
    for test_case in TEST_CASES:
        result = run_test(test_case)
        results.append(result)
        time.sleep(0.5)  # Small delay between tests
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    
    print(f"\nTotal tests: {len(results)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Pass rate: {(passed/len(results)*100):.1f}%")
    
    # Performance stats
    if passed > 0:
        latencies = [
            r["response"]["total_latency_ms"] 
            for r in results 
            if r["status"] == "PASS" and "response" in r
        ]
        if latencies:
            print(f"\nPerformance:")
            print(f"  Average latency: {sum(latencies)/len(latencies):.1f}ms")
            print(f"  Min latency: {min(latencies):.1f}ms")
            print(f"  Max latency: {max(latencies):.1f}ms")
    
    # Save results
    output = {
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "pass_rate": passed/len(results)*100
        },
        "results": results
    }
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n📄 Results saved to: {OUTPUT_FILE}")
    print("\n" + "="*80)
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED!")
    else:
        print(f"⚠️ {failed} test(s) failed. Review the output above.")
    
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
