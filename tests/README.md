# AAFR Backend Test Suite

Comprehensive test suite for the AAFR (Andrew's Automated Futures Routine) backend system.

## Overview

This test suite covers all backend modules:
- **ICC Module**: Indication-Correction-Continuation pattern detection
- **CVD Module**: Cumulative Volume Delta calculations
- **Risk Engine**: Position sizing and risk management
- **Tradovate API**: Market data integration and fallback behavior
- **Backtester**: Performance metrics and trade simulation
- **Utils**: Helper functions (ATR, displacement, logging)
- **Integration**: End-to-end system flows

## Running Tests

### Run All Tests

```bash
# From project root
python tests/test_runner.py

# Or using unittest discovery
python -m unittest discover tests

# Or run specific module
python tests/test_runner.py --module test_icc_module
```

### Run Individual Test Modules

```bash
# ICC Module tests
python -m unittest tests.test_icc_module

# CVD Module tests
python -m unittest tests.test_cvd_module

# Risk Engine tests
python -m unittest tests.test_risk_engine

# Tradovate API tests
python -m unittest tests.test_tradovate_api

# Backtester tests
python -m unittest tests.test_backtester

# Utils tests
python -m unittest tests.test_utils

# Integration tests
python -m unittest tests.test_integration
```

### Run Specific Test Cases

```bash
# Run specific test class
python -m unittest tests.test_icc_module.TestICCModule

# Run specific test method
python -m unittest tests.test_icc_module.TestICCModule.test_detect_icc_structure_complete
```

## Test Coverage

### ICC Module (`test_icc_module.py`)
- ✅ Detector initialization
- ✅ ICC structure detection (complete and partial)
- ✅ Indication phase detection
- ✅ Correction phase detection
- ✅ Continuation phase detection
- ✅ Trade level calculation (entry, stop, TP, R multiple)
- ✅ Full setup validation
- ✅ Detector reset

### CVD Module (`test_cvd_module.py`)
- ✅ Calculator initialization
- ✅ CVD calculation from candles
- ✅ Volume delta calculation
- ✅ Divergence detection
- ✅ Phase analysis (indication, correction, continuation)
- ✅ CVD slope calculation
- ✅ Calculator reset

### Risk Engine (`test_risk_engine.py`)
- ✅ Engine initialization
- ✅ Position size calculation
- ✅ ATR-based stop calculation
- ✅ Take profit calculation
- ✅ Trade setup validation
- ✅ Restricted event detection
- ✅ Daily P&L tracking
- ✅ Daily trade counter
- ✅ Daily limits enforcement

### Tradovate API (`test_tradovate_api.py`)
- ✅ API client initialization
- ✅ Account list retrieval
- ✅ Historical data fetching
- ✅ Mock data fallback behavior
- ✅ Instrument specifications
- ✅ Live data subscription (mock)
- ✅ Order placement (mock)
- ✅ Authentication fallback

### Backtester (`test_backtester.py`)
- ✅ Backtester initialization
- ✅ Backtest execution
- ✅ Trade level calculation
- ✅ Trade outcome simulation (win/loss)
- ✅ Performance metrics calculation
- ✅ Results printing

### Utils (`test_utils.py`)
- ✅ Config file loading
- ✅ ATR calculation
- ✅ Displacement detection
- ✅ Trade signal logging
- ✅ Trade output formatting
- ✅ Mock candle generation
- ✅ Mock volume data generation

### Integration (`test_integration.py`)
- ✅ System initialization
- ✅ End-to-end ICC detection flow
- ✅ ICC-CVD integration
- ✅ Risk engine integration
- ✅ API fallback behavior
- ✅ Backtest integration
- ✅ Trade signal processing flow
- ✅ Daily limit enforcement

## Test Statistics

- **Total Test Cases**: ~80+ test methods
- **Modules Tested**: 7
- **Coverage**: Core functionality across all modules
- **Edge Cases**: Boundary conditions, error handling, invalid inputs

## Test Data

Tests use:
- **Mock candles**: Generated via `generate_mock_candles()`
- **ICC test patterns**: Realistic ICC structure generation
- **Config files**: Uses `aafr/config.json` (must exist)
- **Temporary directories**: For logging tests (auto-cleaned)

## Notes

1. **Config File Required**: Some tests require `aafr/config.json` to exist
2. **Mock Data**: API tests use mock data fallback (doesn't require real API credentials)
3. **Temporary Files**: Utils tests create temporary directories that are auto-cleaned
4. **Test Isolation**: Each test is independent and can be run standalone

## Continuous Integration

Tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run Tests
  run: python tests/test_runner.py
```

## Contributing

When adding new features:
1. Add corresponding test cases
2. Follow existing test structure
3. Use descriptive test method names (test_<feature>_<condition>)
4. Include edge case tests
5. Update this README

## Troubleshooting

### Import Errors
- Ensure you're running from project root
- Check that `aafr/` module is in Python path

### Config Errors
- Ensure `aafr/config.json` exists
- Check JSON format is valid

### Mock Data Issues
- API tests should work without real credentials
- If issues occur, check mock data generation functions

