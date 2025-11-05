# AAFR - Andrew's Automated Futures Routine

A modular algorithmic trading system for futures markets with ICC pattern detection, CVD order flow analysis, and comprehensive risk management.

## System Overview

AAFR implements a complete trading backend with:

- **ICC Detection**: Identifies Indication-Correction-Continuation structures
- **CVD Analysis**: Cumulative Volume Delta for order flow confirmation
- **Risk Management**: TPT 150K account rules (0.5-1% risk per trade)
- **Tradovate Integration**: Live and demo API support
- **Backtesting**: Performance metrics and equity curve analysis

## Project Structure

```
trading/
├── aafr/
│   ├── __init__.py          # Package initialization
│   ├── main.py              # Main system orchestrator
│   ├── icc_module.py        # ICC pattern detection
│   ├── cvd_module.py        # CVD calculations
│   ├── risk_engine.py       # Risk management
│   ├── tradovate_api.py     # API integration
│   ├── backtester.py        # Backtesting engine
│   ├── utils.py             # Helper functions
│   └── config.json          # Configuration
├── logs/
│   └── trades/              # Trade logs
└── README.md
```

## Quick Start

### 1. Configuration

Edit `aafr/config.json` with your Tradovate credentials:

```json
{
  "environment": "demo",
  "tradovate": {
    "demo": {
      "client_id": "YOUR_DEMO_CLIENT_ID",
      "client_secret": "YOUR_DEMO_CLIENT_SECRET",
      "username": "YOUR_DEMO_USERNAME",
      "password": "YOUR_DEMO_PASSWORD"
    }
  }
}
```

### 2. Test the System

```bash
# Test all modules with mock data
python -m aafr.main --mode test

# Run backtest on historical data
python -m aafr.main --mode backtest --symbol MNQ

# Start live monitoring (requires valid API credentials)
python -m aafr.main --mode live --symbol MNQ

# Analyze custom data from CSV file
python -m aafr.main --mode analyze --data-file your_data.csv --symbol MNQ

# Run backtest on custom CSV data
python -m aafr.main --mode backtest --data-file your_data.csv --symbol MNQ

# Analyze custom data from JSON file
python -m aafr.main --mode analyze --data-file your_data.json --symbol MNQ
```

### 3. Run Individual Modules

```bash
# Test ICC detection
python -m aafr.icc_module

# Test CVD calculation
python -m aafr.cvd_module

# Test risk engine
python -m aafr.risk_engine

# Test API connection
python -m aafr.tradovate_api
```

## Trading Logic

### ICC Framework

**Indication**: Impulsive displacement breaking structure or sweeping liquidity
- Sets directional bias
- Must show CVD alignment

**Correction**: Retracement into high-probability value zone
- CVD neutralizes
- Entry opportunity forms

**Continuation**: Confirmation candle resumes in indication direction
- CVD resumes in alignment
- Trade trigger

### CVD Logic

**CVD = Σ(Buy Volume – Sell Volume)**

- Indication: CVD increases with displacement
- Correction: CVD neutralizes
- Continuation: CVD resumes direction
- Divergence cancels signal

### Risk Rules

**TPT 150K Account Parameters**:
- Account size: $150,000
- Max risk: 0.5-1% per trade ($750-$1,500)
- Minimum R: 2.0 (preferred 3.0)
- Daily loss limit: $1,500
- Skip FOMC/NFP/CPI events

**Position Sizing**:
```
Position Size = (Max Risk) / (Stop Distance × Tick Value)
```

## Trade Output Format

Example signal output:

```
LONG MNQ @ 17893.50 | SL 17864.25 | TP1 17965.00 | R=3.1 | Size: 2 MNQ | Risk $480 (0.5% of 150K)
```

## Backtesting

Backtesting includes:
- Win rate (%)
- Average R multiple
- Net profit/loss
- Max drawdown
- Win/loss streaks
- Equity curve data

Logs saved to `logs/trades/trades_YYYYMMDD.csv`

## API Integration

### Tradovate Demo API

Base URL: `https://demo.tradovateapi.com`

**Endpoints**:
- `/auth/oauthtoken` - Authentication
- `/account/list` - Account information
- `/order/placeorder` - Order placement
- `/md/historicalBars` - Historical data

**Mock Data Fallback**: System automatically falls back to mock data if API is unavailable.

## Custom Data Input

The system supports loading candle data from CSV or JSON files when the API is not working.

### CSV Format

Create a CSV file with the following columns:
```csv
timestamp,open,high,low,close,volume,symbol
0,18000.0,18005.0,17995.0,18003.0,5000,MNQ
1,18003.0,18010.0,18000.0,18008.0,6000,MNQ
...
```

Required columns: `open`, `high`, `low`, `close`, `volume`  
Optional columns: `timestamp`, `symbol` (if not provided, will use defaults)

### JSON Format

Create a JSON file with an array of candle objects:
```json
[
  {
    "timestamp": 0,
    "open": 18000.0,
    "high": 18005.0,
    "low": 17995.0,
    "close": 18003.0,
    "volume": 5000,
    "symbol": "MNQ"
  },
  ...
]
```

### Usage Examples

```bash
# Analyze your data file for ICC patterns and trade signals
python -m aafr.main --mode analyze --data-file your_data.csv --symbol MNQ

# Run backtest on your data file
python -m aafr.main --mode backtest --data-file your_data.csv --symbol MNQ

# Use JSON file instead
python -m aafr.main --mode analyze --data-file your_data.json --symbol MNQ
```

The system will:
1. Load your data from the file
2. Detect ICC patterns
3. Validate with CVD analysis
4. Apply risk management rules
5. Generate trade signals if valid setups are found
6. Log results to CSV files

See `sample_data.csv` and `sample_data.json` for example formats.

## Environment Switching

```json
{
  "environment": "demo"  // or "live"
}
```

Automatically loads correct credentials from config.

## Module Documentation

### ICC Module (`icc_module.py`)

**ICCDetector** class:
- `detect_icc_structure()` - Find complete ICC patterns
- `calculate_trade_levels()` - Calculate entry/stop/TP
- `validate_full_setup()` - Validate all 5 conditions

### CVD Module (`cvd_module.py`)

**CVDCalculator** class:
- `calculate_cvd()` - Compute cumulative volume delta
- `check_divergence()` - Detect price/volume divergence
- `analyze_indication_phase()` - CVD during indication
- `analyze_correction_phase()` - CVD during correction
- `analyze_continuation_phase()` - CVD during continuation

### Risk Engine (`risk_engine.py`)

**RiskEngine** class:
- `calculate_position_size()` - Position sizing
- `calculate_atr_stop()` - ATR-based stops
- `validate_trade_setup()` - Risk validation
- `is_trading_restricted()` - Event restrictions

### Tradovate API (`tradovate_api.py`)

**TradovateAPI** class:
- `authenticate()` - OAuth authentication
- `get_historical_candles()` - Historical data
- `subscribe_live_data()` - Live streaming (TODO)
- `place_order()` - Order execution

### Backtester (`backtester.py`)

**Backtester** class:
- `run_backtest()` - Run full backtest
- `_simulate_trade_outcome()` - Simulate trade P&L
- `print_results()` - Display metrics

## Development

### Requirements

```bash
pip install requests
```

### Testing

```bash
# Run individual module tests
python -m aafr.utils
python -m aafr.icc_module
python -m aafr.cvd_module
python -m aafr.risk_engine
python -m aafr.tradovate_api

# Run full system test
python -m aafr.main --mode test
```

### Adding New Instruments

Edit `config.json`:

```json
{
  "instruments": {
    "SYMBOL": {
      "symbol": "SYMBOL",
      "name": "Full Name",
      "tick_size": 0.25,
      "tick_value": 0.50,
      "contract_size": 1
    }
  }
}
```

## TODOs

- [ ] Implement WebSocket live data streaming
- [ ] Add FVG (Fair Value Gap) detection
- [ ] Add breaker detection
- [ ] Add order block detection
- [ ] Dynamic event calendar loading
- [ ] Multi-timeframe analysis
- [ ] Advanced position management (scaling, trailing stops)
- [ ] Web GUI for monitoring

## Warnings

⚠️ **This is for educational and testing purposes only.**

- Uses mock data when API is unavailable
- Paper trading in demo environment only
- Not financial advice
- Test thoroughly before any live trading
- Monitor all trades manually

## License

MIT License - See LICENSE file for details.

## Support

For questions or issues, please refer to the code documentation or raise an issue in the repository.

