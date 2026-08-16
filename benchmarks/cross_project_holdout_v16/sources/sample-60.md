============================================
  Performance Metrics: Sequential vs Parallel
============================================

Configuration:
  Grid size: N = 100
  Gamma: 1.4
  Benchmark iterations: 5

Sequential Mode:
  Problem A: mean=2.93ms, median=2.91ms, min=2.89ms, max=2.98ms, stddev=0.04ms, cv=1.20%
  Problem B: mean=3.86ms, median=3.86ms, min=3.83ms, max=3.89ms, stddev=0.02ms, cv=0.51%

Parallel Mode (std::async, A+B together):
  Combined: mean=4.70ms, median=4.06ms, min=4.03ms, max=7.23ms, stddev=1.27ms, cv=27.03%

Summary:
  Sequential total (A+B): 6.79ms
  Parallel combined (A+B): 4.70ms
  Speedup: 1.45x
  Theoretical max speedup: 1.76x
  Efficiency: 82.15%

Key Observations:
  - Parallel execution overlaps A and B computation
  - Speedup is limited by the slower problem
  - Thread overhead reduces actual speedup below theoretical
  - CV < 5% indicates consistent timing across iterations
