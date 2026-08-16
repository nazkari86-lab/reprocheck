# Terminal Benchmark Suite

Comprehensive benchmarking tools for comparing BossTerm with iTerm2, Terminal.app, Alacritty, and other terminal emulators.

## BossTerm Performance Highlights

Based on comprehensive benchmarks (December 2025, **Latency Mode**), BossTerm demonstrates significant performance advantages:

### Where BossTerm Excels

| Benchmark | BossTerm Advantage | Use Case |
|-----------|-------------------|----------|
| **Raw Throughput (1MB)** | **+43% faster** than iTerm2 | Small file outputs |
| **Raw Throughput (5MB)** | **+24% faster** than iTerm2 | Medium file outputs |
| **Raw Throughput (25MB)** | **+7% faster** than iTerm2 | Large file outputs |
| **Raw Throughput (50MB)** | **+3% faster** than Alacritty | Very large outputs |
| **Variation Selectors** | **+12% faster** than iTerm2 | Emoji rendering |
| **Flags Emoji** | **+3% faster** than iTerm2 | Country flags |
| **CJK Characters** | **+10% faster** than iTerm2 | Asian text |
| **Powerline** | **+10% faster** than iTerm2 | Status lines |
| **htop Simulation** | **+13% faster** than iTerm2 | TUI applications |
| **Git Diff Simulation** | **+5% faster** than iTerm2 | Code review |

### Performance Comparison Charts

#### Raw Throughput @ 50MB (MB/s) - Higher is Better
```
BossTerm   ████████████████████████████████████████████████████ 1,645 MB/s ✓
Alacritty  ██████████████████████████████████████████████████   1,633 MB/s
iTerm2     █████████████████████████████████████████████████    1,599 MB/s
Terminal   ████████████████████████████████████████████████     1,491 MB/s
           └─────────────────────────────────────────────────────────────────┘
           0                    600                  1200               1800
```

#### Raw Throughput @ 1MB (MB/s) - Higher is Better
```
BossTerm   ████████████████████████████████████████████████████  364 MB/s ✓
iTerm2     ███████████████████████████████████                   255 MB/s
Terminal   ██████████████████████████████████                    249 MB/s
Alacritty  █████████████████████████████████                     233 MB/s
           └─────────────────────────────────────────────────────────────────┘
           0                    150                    300                450
```

#### Command Latency - 10 Sequential (ms) - Lower is Better
```
iTerm2     ████████████████████████████████████████████████████  29.3 ms ✓
BossTerm   ████████████████████████████████████████████████████  29.6 ms
Terminal   █████████████████████████████████████████████████████ 30.1 ms
Alacritty  ██████████████████████████████████████████████████████ 33.3 ms
           └─────────────────────────────────────────────────────────────────┘
           0                     15                    30                   45
```

#### Real-World Simulations (ms) - Lower is Better
```
Git Diff:
BossTerm   ████████████████████████████████████████████████      2.93 ms ✓
Terminal   █████████████████████████████████████████████████████ 3.06 ms
iTerm2     █████████████████████████████████████████████████████ 3.07 ms
Alacritty  ██████████████████████████████████████████████████████ 3.48 ms

htop-like TUI:
BossTerm   ████████████████████████████████████████████████      3.09 ms ✓
Terminal   █████████████████████████████████████████████████████ 3.21 ms
iTerm2     ██████████████████████████████████████████████████████ 3.55 ms
Alacritty  ███████████████████████████████████████████████████████ 3.72 ms
```

#### Unicode/Emoji Rendering (chars/sec) - Higher is Better
```
Variation Selectors:
BossTerm   ████████████████████████████████████████████████████  1.01M ✓
iTerm2     █████████████████████████████████████████████████     904K
Terminal   ████████████████████████████████████████████████      879K
Alacritty  █████████████████████████████████████████████         829K

CJK Characters (中文):
BossTerm   ████████████████████████████████████████████████████  2.99M ✓
Terminal   ██████████████████████████████████████████████████    2.86M
iTerm2     ███████████████████████████████████████████████       2.71M
Alacritty  ██████████████████████████████████████                2.14M
```

#### ANSI Color Processing (sequences/sec) - Higher is Better
```
256 Colors:
iTerm2     ████████████████████████████████████████████████████  3.45M ✓
BossTerm   █████████████████████████████████████████████████     3.15M
Terminal   ████████████████████████████████████████████████      3.01M
Alacritty  ███████████████████████████████████████████           2.82M

16 Colors:
iTerm2     ████████████████████████████████████████████████████  1.74M ✓
BossTerm   █████████████████████████████████████████████████     1.69M
Terminal   ████████████████████████████████████████████████      1.60M
Alacritty  ███████████████████████████████████████████           1.47M
```

#### Special Characters (ms) - Lower is Better
```
Powerline:
BossTerm   ████████████████████████████████████████████████      2.83 ms ✓
iTerm2     █████████████████████████████████████████████████████ 3.15 ms
Terminal   ██████████████████████████████████████████████████████ 3.34 ms
Alacritty  ██████████████████████████████████████████████████████ 3.35 ms

Block Elements:
iTerm2     ████████████████████████████████████████████████      2.95 ms
BossTerm   ████████████████████████████████████████████████      2.97 ms
Terminal   █████████████████████████████████████████████████████ 3.04 ms
Alacritty  ██████████████████████████████████████████████████████ 3.64 ms
```

> **Full benchmark results:** [../benchmark_results/BENCHMARK_SUMMARY.md](../benchmark_results/BENCHMARK_SUMMARY.md)

---

## Quick Start

### Basic Benchmarks

```bash
cd benchmark

# Run basic benchmarks on all detected terminals
python3 benchmark_suite.py --compare

# Run specific benchmarks
python3 benchmark_suite.py -t bossterm,iterm2 -b throughput,unicode -r 5
```

### Comprehensive Benchmarks (25 tests)

```bash
# Run full comprehensive suite with comparison
python3 benchmark_comprehensive.py -t bossterm,iterm2,terminal,alacritty --compare

# List all available benchmarks
python3 benchmark_comprehensive.py --list

# Run specific category
python3 benchmark_comprehensive.py -b simulation -r 3
```

## Benchmark Suites

### Basic Suite (`benchmark_suite.py`)
7 benchmark categories for quick performance comparison.

### Comprehensive Suite (`benchmark_comprehensive.py`)
25 benchmarks across 7 categories for thorough analysis.

| Category | Benchmarks |
|----------|------------|
| **Throughput** | Raw data (1-50MB), lines (1K-100K), varied content |
| **Latency** | Echo, printf (1-200 chars), sequential commands |
| **Unicode** | Basic emoji, ZWJ, skin tones, flags, surrogate pairs, CJK, combining chars |
| **ANSI** | 16/256/truecolor, attributes, cursor movements |
| **Special** | Box drawing, block elements, powerline, braille, math symbols |
| **Simulation** | Compiler output, logs, git diff, htop, vim, mixed workload |
| **Resources** | Memory usage, CPU usage |

## Complete Results

### Category Winners (December 2025, Latency Mode)

| Category | Winner | Margin |
|----------|--------|--------|
| Raw Throughput (1MB-25MB) | **BossTerm** | +7-43% vs iTerm2 |
| Raw Throughput (50MB) | **BossTerm** | +3% vs Alacritty |
| Variation Selectors | **BossTerm** | +12% vs iTerm2 |
| CJK Characters | **BossTerm** | +10% vs iTerm2 |
| htop/Git Diff Simulation | **BossTerm** | +5-13% vs iTerm2 |
| Powerline | **BossTerm** | +10% vs iTerm2 |
| 256 Colors | iTerm2 | +10% vs BossTerm |
| ZWJ Sequences | Terminal | +13% vs BossTerm |
| Surrogate Pairs | Terminal | +20% vs BossTerm |

> **Detailed analysis with charts and methodology:** [../benchmark_results/BENCHMARK_SUMMARY.md](../benchmark_results/BENCHMARK_SUMMARY.md)

## Output Files

Results saved to `../benchmark_results/`:
- [`BENCHMARK_SUMMARY.md`](../benchmark_results/BENCHMARK_SUMMARY.md) - Executive summary with analysis
- `{terminal}_comprehensive_{timestamp}.md` - Individual terminal results
- `comparison_comprehensive_{timestamp}.md` - Side-by-side comparison

## Requirements

```bash
pip3 install psutil --break-system-packages  # or use venv
```

## Shell Script (Alternative)

```bash
chmod +x terminal_benchmark.sh
./terminal_benchmark.sh -t all -b throughput,latency -r 5
```

## Notes

- Run in a clean terminal session for accurate results
- Close other applications to reduce interference
- Multiple runs (`-r`) improve statistical accuracy
- BossTerm memory includes JVM overhead (~1.5GB vs ~200MB for native apps)

---

## Performance Modes

BossTerm offers configurable performance optimization in Settings > Performance:

| Mode | Behavior | Best For |
|------|----------|----------|
| **Balanced** (default) | Middle ground between latency and throughput | General use |
| **Latency** | Instant wake on data arrival | SSH, vim, interactive commands |
| **Throughput** | Batched data processing | Build logs, large file output |

Latency mode achieved the benchmark results shown above. Users can switch modes based on their primary use case.

---

## Why BossTerm?

BossTerm (Latency Mode) is optimized for **developer workflows** with a focus on:

1. **Exceptional raw throughput** - Up to 43% faster than iTerm2 for small-medium files
2. **Fast large file output** - 3-7% faster for 25-50MB outputs
3. **Strong Unicode support** - +12% faster variation selectors, +10% faster CJK
4. **Great simulation performance** - 13% faster htop, 5% faster git diff
5. **Modern architecture** with Kotlin/Compose Desktop
6. **Extensible** with built-in debug tools and performance metrics

iTerm2 leads in ANSI colors, Terminal.app leads in ZWJ sequences and surrogate pairs - but BossTerm's exceptional raw throughput advantage and strong Unicode performance makes it ideal for developers who work with build systems, log files, and international text.
