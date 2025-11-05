"""
Test suite for multi-instrument functionality.
Tests that each instrument generates independent signals and maintains independent state.
"""

import unittest
from datetime import datetime, timedelta

from aafr.backtester import Backtester
from aafr.icc_module import ICCDetector
from aafr.cvd_module import CVDCalculator
from aafr.utils import generate_mock_candles, generate_mock_candles_for_period


class TestMultiInstrument(unittest.TestCase):
    """Test multi-instrument functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.instruments = ["MNQ", "MES", "MGC", "MCL", "MYM"]
        self.backtester = Backtester()
    
    def test_independent_icc_detection(self):
        """Test that ICC detection works independently for each instrument."""
        for symbol in self.instruments:
            with self.subTest(symbol=symbol):
                # Generate mock candles for this instrument
                candles = generate_mock_candles(100, symbol)
                
                # Create independent ICC detector
                icc_detector = ICCDetector()
                
                # Detect ICC structure
                icc_structure = icc_detector.detect_icc_structure(candles, require_all_phases=False)
                
                # Should not raise error and should return valid structure or None
                self.assertIsInstance(icc_structure, (dict, type(None)))
                
                if icc_structure:
                    self.assertIn('indication', icc_structure)
    
    def test_independent_cvd_calculation(self):
        """Test that CVD calculation works independently for each instrument."""
        for symbol in self.instruments:
            with self.subTest(symbol=symbol):
                # Generate mock candles for this instrument
                candles = generate_mock_candles(50, symbol)
                
                # Create independent CVD calculator
                cvd_calculator = CVDCalculator()
                
                # Calculate CVD
                cvd_values = cvd_calculator.calculate_cvd(candles)
                
                # Should return list of same length as candles
                self.assertEqual(len(cvd_values), len(candles))
                self.assertIsInstance(cvd_values, list)
    
    def test_backtest_batch_independence(self):
        """Test that batch backtests maintain independent state per instrument."""
        # Generate candles for multiple instruments
        candles_by_symbol = {}
        for symbol in ["MNQ", "MES", "MGC"]:
            candles_by_symbol[symbol] = generate_mock_candles(200, symbol)
        
        # Run batch backtest
        results = self.backtester.run_backtest_batch(candles_by_symbol, start_equity=150000)
        
        # Verify results for each instrument
        self.assertEqual(len(results), len(candles_by_symbol))
        
        for symbol, result in results.items():
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, candles_by_symbol)
                self.assertIsInstance(result, dict)
                self.assertIn('total_trades', result)
                self.assertIn('win_rate', result)
                self.assertIn('net_pnl', result)
                self.assertIn('final_equity', result)
    
    def test_multi_instrument_backtest(self):
        """Test multi-instrument backtest method."""
        instruments = ["MNQ", "MES"]
        
        # Generate candles
        candles_by_symbol = {}
        for symbol in instruments:
            candles_by_symbol[symbol] = generate_mock_candles(200, symbol)
        
        # Run multi-instrument backtest
        results = self.backtester.run_multi_instrument_backtest(
            instruments, candles_by_symbol, start_equity=150000
        )
        
        # Verify results
        self.assertEqual(len(results), len(instruments))
        
        for symbol in instruments:
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, results)
                result = results[symbol]
                self.assertIsInstance(result, dict)
                self.assertIn('total_trades', result)
    
    def test_instrument_specific_metrics(self):
        """Test that metrics are calculated correctly for each instrument."""
        # Generate candles for different instruments
        mnq_candles = generate_mock_candles(200, "MNQ")
        mes_candles = generate_mock_candles(200, "MES")
        
        # Run backtests
        mnq_results = self.backtester.run_backtest(mnq_candles, "MNQ", start_equity=150000)
        mes_results = self.backtester.run_backtest(mes_candles, "MES", start_equity=150000)
        
        # Verify metrics are present
        for results, symbol in [(mnq_results, "MNQ"), (mes_results, "MES")]:
            with self.subTest(symbol=symbol):
                self.assertIn('total_trades', results)
                self.assertIn('win_rate', results)
                self.assertIn('avg_r', results)
                self.assertIn('profit_factor', results)
                self.assertIn('sharpe_ratio', results)
                self.assertIn('equity_curve_summary', results)
    
    def test_date_based_mock_data(self):
        """Test date-based mock data generation for different instruments."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)  # 1 month
        
        for symbol in ["MNQ", "MES", "MGC"]:
            with self.subTest(symbol=symbol):
                candles = generate_mock_candles_for_period(
                    start_date, end_date, symbol, interval_minutes=5
                )
                
                # Verify candles
                self.assertGreater(len(candles), 0)
                self.assertEqual(len(candles[0]), 7)  # timestamp, open, high, low, close, volume, symbol
                self.assertEqual(candles[0]['symbol'], symbol)
                
                # Verify timestamps are within range
                first_ts = candles[0].get('timestamp', 0)
                last_ts = candles[-1].get('timestamp', 0)
                
                if isinstance(first_ts, (int, float)) and isinstance(last_ts, (int, float)):
                    first_dt = datetime.fromtimestamp(first_ts)
                    last_dt = datetime.fromtimestamp(last_ts)
                    # Allow for small time differences (within 1 second)
                    self.assertGreaterEqual(first_dt, start_date - timedelta(seconds=1))
                    self.assertLessEqual(last_dt, end_date + timedelta(seconds=1))
    
    def test_equity_curve_independence(self):
        """Test that equity curves are independent for each instrument."""
        instruments = ["MNQ", "MES"]
        candles_by_symbol = {}
        
        for symbol in instruments:
            candles_by_symbol[symbol] = generate_mock_candles(200, symbol)
        
        # Run batch backtest
        results = self.backtester.run_backtest_batch(candles_by_symbol, start_equity=150000)
        
        # Verify each instrument has its own equity curve
        for symbol, result in results.items():
            with self.subTest(symbol=symbol):
                self.assertIn('equity_curve', result)
                equity_curve = result['equity_curve']
                self.assertIsInstance(equity_curve, list)
                self.assertGreater(len(equity_curve), 0)
                
                # Check equity curve points have timestamps
                for point in equity_curve:
                    self.assertIn('timestamp', point)
                    self.assertIn('equity', point)
    
    def test_metrics_export_format(self):
        """Test that metrics can be exported for each instrument."""
        instruments = ["MNQ", "MES"]
        candles_by_symbol = {}
        
        for symbol in instruments:
            candles_by_symbol[symbol] = generate_mock_candles(200, symbol)
        
        # Run batch backtest
        results = self.backtester.run_backtest_batch(candles_by_symbol, start_equity=150000)
        
        # Verify exportable format
        for symbol, result in results.items():
            with self.subTest(symbol=symbol):
                # Check all required metrics are present
                required_metrics = [
                    'total_trades', 'win_rate', 'avg_r', 'net_pnl',
                    'final_equity', 'max_drawdown', 'max_drawdown_pct',
                    'profit_factor', 'sharpe_ratio', 'equity_curve_summary'
                ]
                
                for metric in required_metrics:
                    self.assertIn(metric, result, f"Missing metric: {metric}")


if __name__ == "__main__":
    unittest.main()

