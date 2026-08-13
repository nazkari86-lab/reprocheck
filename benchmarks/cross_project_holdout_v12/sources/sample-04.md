# EMA Crossover Autoresearch

Autonomous EMA crossover strategy backtesting using [VectorBT](https://vectorbt.dev/) + [OpenAlgo](https://github.com/marketcalls/openalgo).

## Strategy

**Buy** when Fast EMA crosses above Slow EMA, **Sell** on cross below (long only).

- **Symbol:** SBIN (NSE)
- **Interval:** Daily
- **Period:** 10 years
- **Fast EMA:** 10 | **Slow EMA:** 30
- **Fees:** Indian delivery equity (0.111% + Rs 20/order)
- **Benchmark:** NIFTY 50 Index

## Features

- TA-Lib for indicator calculations
- OpenAlgo DuckDB (Historify) for fast local data loading
- Realistic Indian market transaction cost modeling
- Strategy vs NIFTY 50 benchmark comparison
- Plain-language backtest report explanation
- QuantStats HTML tearsheet generation
- Plotly equity curve + drawdown visualization
- Trade export to CSV

## Requirements

- Python 3.10+
- Virtual environment with dependencies:

```bash
pip install openalgo vectorbt plotly ta-lib pandas numpy python-dotenv quantstats
```

- TA-Lib C library (macOS: `brew install ta-lib`)
- OpenAlgo API key or Historify DuckDB database

## Setup

1. Create a `.env` file in the project root:

```env
OPENALGO_API_KEY=your_openalgo_api_key_here
OPENALGO_HOST=http://127.0.0.1:5000
HISTORIFY_DB_PATH=/path/to/historify.duckdb
```

2. Run the backtest:

```bash
python SBIN_ema_crossover_backtest.py
```

## Output

- Console: Full stats, strategy vs benchmark table, plain-language explanation
- `SBIN_ema_crossover_trades.csv` — All trade records
- `SBIN_tearsheet.html` — QuantStats tearsheet with detailed analytics
- Plotly chart — Equity curve + underwater (drawdown) plot

## License

MIT
