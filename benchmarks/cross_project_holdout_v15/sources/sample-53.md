
======================================================
   STAGE 1: READ BENCHMARK (Monolith Catalog)         
======================================================

--- Concurrency: 10 | Duration: 10s ---
Throughput: 375.10 req/sec
Latency:    26.15 ms (Mean) | 53.00 ms (p99)
Total Req:  3751 | Errors: 0

--- Concurrency: 25 | Duration: 10s ---
Throughput: 479.40 req/sec
Latency:    51.52 ms (Mean) | 115.00 ms (p99)
Total Req:  4794 | Errors: 0

--- Concurrency: 50 | Duration: 10s ---
Throughput: 386.80 req/sec
Latency:    129.41 ms (Mean) | 404.00 ms (p99)
Total Req:  3868 | Errors: 0

--- Concurrency: 75 | Duration: 10s ---
Throughput: 629.30 req/sec
Latency:    118.95 ms (Mean) | 220.00 ms (p99)
Total Req:  6293 | Errors: 0

--- Concurrency: 100 | Duration: 10s ---
Throughput: 420.70 req/sec
Latency:    237.55 ms (Mean) | 548.00 ms (p99)
Total Req:  4207 | Errors: 0

======================================================
   STAGE 2: WRITE BENCHMARK (Monolithic Orders)       
======================================================
Targeting Merchandise ID: 69e46ad3c35a0919002b8d7a | Price: 1100

--- Concurrency: 10 | Duration: 10s ---
Throughput: 386.30 req/sec
Latency:    25.38 ms (Mean) | 56.00 ms (p99)
Total Req:  3863 | Errors: 0

--- Concurrency: 25 | Duration: 10s ---
Throughput: 582.82 req/sec
Latency:    42.47 ms (Mean) | 89.00 ms (p99)
Total Req:  6411 | Errors: 0

[✓] Monolithic Autocannon Benchmarking Suite Complete.
