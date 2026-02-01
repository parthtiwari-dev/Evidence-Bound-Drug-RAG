# Test API Script
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Testing Evidence-Bound Drug RAG API" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# Test 1: Health Check
Write-Host "`n[1] Testing /health endpoint..." -ForegroundColor Yellow
$health = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get
$health | ConvertTo-Json -Depth 10
Write-Host "Status: $($health.status)" -ForegroundColor Green

# Test 2: Stats
Write-Host "`n[2] Testing /stats endpoint..." -ForegroundColor Yellow
$stats = Invoke-RestMethod -Uri "http://localhost:8000/stats" -Method Get
Write-Host "Total chunks: $($stats.total_chunks)" -ForegroundColor Green
Write-Host "Drugs covered: $($stats.drugs_covered.Count)" -ForegroundColor Green

# Test 3: Vector Retrieval
Write-Host "`n[3] Testing /retrieve (vector)..." -ForegroundColor Yellow
$body = @{
    query = "What are the side effects of warfarin?"
    top_k = 5
    retriever_type = "vector"
} | ConvertTo-Json

$result = Invoke-RestMethod -Uri "http://localhost:8000/retrieve" -Method Post -Body $body -ContentType "application/json"
Write-Host "Query: $($result.query)" -ForegroundColor Green
Write-Host "Latency: $($result.latency_ms)ms" -ForegroundColor Green
Write-Host "Results: $($result.results.Count)" -ForegroundColor Green
Write-Host "Top drugs: $($result.metadata.top_drugs_retrieved -join ', ')" -ForegroundColor Green

# Test 4: BM25 Retrieval
Write-Host "`n[4] Testing /retrieve (bm25)..." -ForegroundColor Yellow
$body = @{
    query = "warfarin side effects"
    top_k = 5
    retriever_type = "bm25"
} | ConvertTo-Json

$result = Invoke-RestMethod -Uri "http://localhost:8000/retrieve" -Method Post -Body $body -ContentType "application/json"
Write-Host "Latency: $($result.latency_ms)ms" -ForegroundColor Green
Write-Host "Top drugs: $($result.metadata.top_drugs_retrieved -join ', ')" -ForegroundColor Green

# Test 5: Hybrid Retrieval
Write-Host "`n[5] Testing /retrieve (hybrid)..." -ForegroundColor Yellow
$body = @{
    query = "warfarin side effects"
    top_k = 5
    retriever_type = "hybrid"
} | ConvertTo-Json

$result = Invoke-RestMethod -Uri "http://localhost:8000/retrieve" -Method Post -Body $body -ContentType "application/json"
Write-Host "Latency: $($result.latency_ms)ms" -ForegroundColor Green
Write-Host "Top drugs: $($result.metadata.top_drugs_retrieved -join ', ')" -ForegroundColor Green

Write-Host "`n================================" -ForegroundColor Cyan
Write-Host "All tests complete!" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
