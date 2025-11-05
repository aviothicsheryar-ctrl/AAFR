# AAFR Trading System - Commands Reference

Complete command reference for running, testing, and using the AAFR Trading System.

## Table of Contents
- [Running Tests](#running-tests)
- [Running Backtests](#running-backtests)
- [Live Monitoring](#live-monitoring)
- [Data Analysis](#data-analysis)
- [Backtest Scripts](#backtest-scripts)
- [Report Generation](#report-generation)
- [Utility Commands](#utility-commands)

---

## Running Tests

### Run All Tests
```bash
python tests/test_runner.py
```

### Run Specific Test Module
```bash
# Using test runner
python tests/test_runner.py --module test_icc_module
python tests/test_runner.py --module test_cvd_module
python tests/test_runner.py --module test_backtester
python tests/test_runner.py --module test_multi_instrument
python tests/test_runner.py --module test_backtest_metrics

# Using unittest directly
python -m unittest tests.test_icc_module
python -m unittest tests.test_cvd_module
python -m unittest tests.test_risk_engine
python -m unittest tests.test_tradovate_api
python -m unittest tests.test_backtester
python -m unittest tests.test_utils
python -m unittest tests.test_integration
python -m unittest tests.test_edge_cases
python -m unittest tests.test_multi_instrument
python -m unittest tests.test_backtest_metrics
```

### Run Specific Test Class
```bash
python -m unittest tests.test_icc_module.TestICCModule
python -m unittest tests.test_cvd_module.TestCVDModule
python -m unittest tests.test_backtester.TestBacktester
```

### Run Specific Test Method
```bash
python -m unittest tests.test_icc_module.TestICCModule.test_detect_icc_structure_complete
python -m unittest tests.test_backtester.TestBacktester.test_run_backtest
```

### Run Tests with Verbose Output
```bash
python -m unittest discover tests -v
```

### Run Tests for Specific Feature
```bash
# Multi-instrument tests
python -m unittest tests.test_multi_instrument -v

# Extended metrics tests
python -m unittest tests.test_backtest_metrics -v

# Edge case tests
python -m unittest tests.test_edge_cases -v
```

---

## Running Backtests

### Single Instrument Backtest
```bash
# Using main module
python -m aafr.main --mode backtest --symbol MNQ

# With custom data file
python -m aafr.main --mode backtest --symbol MNQ --data-file data/my_data.csv
```

### Multi-Instrument Backtest
```bash
# Multiple instruments
python -m aafr.main --mode backtest --instruments MNQ MES MGC

# Or using --symbols flag
python -m aafr.main --mode backtest --symbols MNQ MES MGC

# All 5 instruments
python -m aafr.main --mode backtest --all-instruments
```

### Backtest with Custom Data
```bash
# CSV format
python -m aafr.main --mode backtest --symbol MNQ --data-file data/historical_data.csv

# JSON format
python -m aafr.main --mode backtest --symbol MNQ --data-file data/historical_data.json
```

---

## Live Monitoring

### Single Symbol Live Monitoring
```bash
python -m aafr.main --mode live --symbol MNQ
```

### Multiple Symbols Live Monitoring
```bash
python -m aafr.main --mode live --symbols MNQ MES MGC
```

### Stop Live Monitoring
Press `Ctrl+C` to gracefully stop the monitoring system.

---

## Data Analysis

### Analyze Custom Data File
```bash
# Analyze CSV file
python -m aafr.main --mode analyze --symbol MNQ --data-file data/my_data.csv

# Analyze JSON file
python -m aafr.main --mode analyze --symbol MNQ --data-file data/my_data.json
```

### Test Mode (Quick System Test)
```bash
python -m aafr.main --mode test --symbol MNQ
```

---

## Backtest Scripts

### Full MNQ Backtest (1-3 Months)
```bash
python scripts/backtest_nq.py
```

This script:
- Generates or fetches 1-3 months of historical data for MNQ
- Runs comprehensive backtest
- Exports results to `backtest_results/nq_full/`
- Creates metrics JSON and equity curve CSV files

### Spot Check Other Instruments (2-7 Days)
```bash
python scripts/backtest_spot_check.py
```

This script:
- Runs quick 5-day backtests on MES, MGC, MCL, MYM
- Exports results to `backtest_results/spot_checks/`
- Generates comparison report

### Generate Consolidated Report
```bash
python scripts/generate_backtest_report.py
```

This script:
- Consolidates all backtest results from `nq_full/` and `spot_checks/`
- Generates markdown summary report
- Creates CSV summary
- Exports JSON summary
- Outputs to `backtest_results/consolidated/`

---

## Report Generation

### View Backtest Results
```bash
# List all backtest results
ls backtest_results/nq_full/
ls backtest_results/spot_checks/
ls backtest_results/consolidated/

# View metrics JSON
cat backtest_results/nq_full/metrics_*.json

# View equity curve CSV
cat backtest_results/nq_full/equity_curve_*.csv

# View consolidated report (markdown)
cat backtest_results/consolidated/summary_report_*.md
```

### Export Results
Backtest results are automatically exported when running:
- `scripts/backtest_nq.py` → exports to `backtest_results/nq_full/`
- `scripts/backtest_spot_check.py` → exports to `backtest_results/spot_checks/`
- `scripts/generate_backtest_report.py` → exports to `backtest_results/consolidated/`

---

## Utility Commands

### Check System Status
```bash
# Test all modules
python -m aafr.main --mode test

# Check configuration
python -c "from aafr.utils import load_config; import json; print(json.dumps(load_config(), indent=2))"
```

### Generate Mock Data
```python
# Python interactive
from aafr.utils import generate_mock_candles, generate_mock_candles_for_period
from datetime import datetime, timedelta

# Generate 100 candles
candles = generate_mock_candles(100, "MNQ")

# Generate date-based candles (1 month)
end_date = datetime.now()
start_date = end_date - timedelta(days=30)
candles = generate_mock_candles_for_period(start_date, end_date, "MNQ", interval_minutes=5)
```

### View Trade Logs
```bash
# View today's trade logs
cat logs/trades/trades_$(date +%Y%m%d).csv

# View last 10 trades
tail -n 10 logs/trades/trades_*.csv

# List all trade log files
ls logs/trades/
```

### Check API Status
```python
# Python interactive
from aafr.tradovate_api import TradovateAPI

api = TradovateAPI()
api.authenticate()
print(f"Using mock data: {api.is_using_mock_data()}")
```

---

## Common Workflows

### Complete Backtest Workflow
```bash
# 1. Run full MNQ backtest
python scripts/backtest_nq.py

# 2. Run spot checks on other instruments
python scripts/backtest_spot_check.py

# 3. Generate consolidated report
python scripts/generate_backtest_report.py

# 4. View results
cat backtest_results/consolidated/summary_report_*.md
```

### Development/Testing Workflow
```bash
# 1. Run all tests
python tests/test_runner.py

# 2. Run specific module tests
python -m unittest tests.test_backtester -v

# 3. Test with mock data
python -m aafr.main --mode test --symbol MNQ

# 4. Run quick backtest
python -m aafr.main --mode backtest --symbol MNQ
```

### Verification Workflow
```bash
# 1. Verify all tests pass
python tests/test_runner.py

# 2. Verify multi-instrument functionality
python -m unittest tests.test_multi_instrument -v

# 3. Verify extended metrics
python -m unittest tests.test_backtest_metrics -v

# 4. Verify backtest scripts
python scripts/backtest_nq.py
```

---

## Command Line Arguments

### Main Module Arguments
```
--mode        Operating mode: live, backtest, test, analyze
--symbol      Trading symbol (default: MNQ)
--symbols     Multiple symbols for live mode or backtest
--instruments List of instruments to backtest (e.g., MNQ MES MGC)
--all-instruments  Run backtest on all 5 instruments
--data-file   Path to CSV or JSON file containing candle data
```

### Test Runner Arguments
```
--module, -m  Run specific test module (e.g., test_icc_module)
--all, -a     Run all tests (default)
```

### Examples
```bash
# Single symbol backtest
python -m aafr.main --mode backtest --symbol MNQ

# Multiple instruments
python -m aafr.main --mode backtest --instruments MNQ MES MGC

# All instruments
python -m aafr.main --mode backtest --all-instruments

# Live monitoring
python -m aafr.main --mode live --symbols MNQ MES

# Analyze custom data
python -m aafr.main --mode analyze --symbol MNQ --data-file data.csv
```

---

## Environment Variables

The system uses configuration from `aafr/config.json`. Key settings:
- `environment`: "demo" or "live"
- `account.size`: 150000 (TPT 150K account)
- `account.enabled_instruments`: ["MNQ", "MES", "MGC", "MCL", "MYM"]

---

## Troubleshooting

### Check if modules can be imported
```bash
python -c "from aafr.icc_module import ICCDetector; print('OK')"
python -c "from aafr.backtester import Backtester; print('OK')"
python -c "from aafr.utils import generate_mock_candles_for_period; print('OK')"
```

### Check for syntax errors
```bash
python -m py_compile aafr/backtester.py
python -m py_compile tests/test_multi_instrument.py
```

### Run with verbose error output
```bash
python tests/test_runner.py 2>&1 | tee test_output.txt
```

### Check Python path
```bash
python -c "import sys; print('\n'.join(sys.path))"
```

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `python tests/test_runner.py` | Run all tests |
| `python -m aafr.main --mode backtest --symbol MNQ` | Single instrument backtest |
| `python -m aafr.main --mode backtest --all-instruments` | All instruments backtest |
| `python -m aafr.main --mode live --symbols MNQ MES` | Live monitoring |
| `python scripts/backtest_nq.py` | Full MNQ backtest |
| `python scripts/backtest_spot_check.py` | Spot check other instruments |
| `python scripts/generate_backtest_report.py` | Generate consolidated report |
| `python -m unittest tests.test_multi_instrument -v` | Test multi-instrument |
| `python -m unittest tests.test_backtest_metrics -v` | Test extended metrics |

---

## Notes

- All commands should be run from the project root directory (`d:\office projects\trading`)
- Mock data is used when API credentials are not configured or API is unavailable
- Test results are displayed in the console
- Backtest results are automatically exported to CSV/JSON files
- Trade signals are logged to `logs/trades/trades_YYYYMMDD.csv`

