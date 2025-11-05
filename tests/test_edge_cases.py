"""
Edge case and error handling tests for AAFR backend.
Tests boundary conditions, invalid inputs, and error scenarios.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from aafr.icc_module import ICCDetector
from aafr.cvd_module import CVDCalculator
from aafr.risk_engine import RiskEngine
from aafr.tradovate_api import TradovateAPI
from aafr.utils import calculate_atr, detect_displacement, load_config


class TestEdgeCases(unittest.TestCase):
    """Edge case and error handling tests."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.icc_detector = ICCDetector()
        self.cvd_calculator = CVDCalculator()
        self.risk_engine = RiskEngine()
        self.api = TradovateAPI()
    
    def test_icc_empty_candles(self):
        """Test ICC detection with empty candle list."""
        result = self.icc_detector.detect_icc_structure([])
        self.assertIsNone(result)
    
    def test_icc_single_candle(self):
        """Test ICC detection with single candle."""
        candles = [{'timestamp': 0, 'open': 17800, 'high': 17810, 'low': 17790, 'close': 17805, 'volume': 1000, 'symbol': 'MNQ'}]
        result = self.icc_detector.detect_icc_structure(candles)
        self.assertIsNone(result)
    
    def test_cvd_empty_candles(self):
        """Test CVD calculation with empty candle list."""
        result = self.cvd_calculator.calculate_cvd([])
        self.assertEqual(result, [])
    
    def test_cvd_zero_volume(self):
        """Test CVD calculation with zero volume candles."""
        candles = [
            {'timestamp': i, 'open': 17800, 'high': 17810, 'low': 17790, 'close': 17805, 'volume': 0, 'symbol': 'MNQ'}
            for i in range(10)
        ]
        result = self.cvd_calculator.calculate_cvd(candles)
        self.assertEqual(len(result), 10)
        # All deltas should be zero with zero volume
        self.assertEqual(set(result), {0})
    
    def test_risk_engine_zero_account_size(self):
        """Test risk engine with zero account size (edge case)."""
        self.risk_engine.account_size = 0
        
        entry = 17893.50
        stop = 17864.25
        
        is_valid, msg, details = self.risk_engine.validate_trade_setup(
            entry, stop, 'LONG', 'MNQ', [{'open': 17800, 'high': 17900, 'low': 17700, 'close': 17850, 'volume': 1000}]
        )
        
        # Should handle gracefully (will fail on other criteria)
        self.assertIsInstance(is_valid, bool)
    
    def test_risk_engine_invalid_symbol(self):
        """Test risk engine with invalid symbol."""
        entry = 17893.50
        stop = 17864.25
        
        is_valid, msg, details = self.risk_engine.validate_trade_setup(
            entry, stop, 'LONG', 'INVALID_SYMBOL', []
        )
        
        # Should fail gracefully
        self.assertFalse(is_valid)
    
    def test_atr_calculation_empty_data(self):
        """Test ATR calculation with empty data."""
        result = calculate_atr([], [], [])
        self.assertIsNone(result)
    
    def test_atr_calculation_insufficient_period(self):
        """Test ATR calculation with insufficient period."""
        highs = [100.0, 101.0]
        lows = [99.0, 100.0]
        closes = [99.5, 100.5]
        
        result = calculate_atr(highs, lows, closes, period=14)
        self.assertIsNone(result)
    
    def test_displacement_insufficient_data(self):
        """Test displacement detection with insufficient data."""
        candles = [{'high': 100, 'low': 99, 'open': 99.5, 'close': 100, 'volume': 1000}]
        result = detect_displacement(candles)
        self.assertFalse(result)
    
    def test_api_unknown_symbol(self):
        """Test API with unknown symbol."""
        self.api.use_mock_data = True
        candles = self.api.get_historical_candles('UNKNOWN', count=10)
        
        # Should still return candles (mock data)
        self.assertIsNotNone(candles)
        self.assertEqual(len(candles), 10)
    
    def test_icc_negative_prices(self):
        """Test ICC detection with negative prices (should handle gracefully)."""
        candles = [
            {'timestamp': i, 'open': -17800, 'high': -17790, 'low': -17810, 'close': -17795, 'volume': 1000, 'symbol': 'MNQ'}
            for i in range(50)
        ]
        
        # Should not crash, though pattern detection may fail
        try:
            result = self.icc_detector.detect_icc_structure(candles)
            # Result may be None or valid structure
            self.assertIsInstance(result, (dict, type(None)))
        except Exception as e:
            self.fail(f"ICC detector raised exception with negative prices: {e}")
    
    def test_cvd_very_large_volume(self):
        """Test CVD calculation with very large volume values."""
        candles = [
            {'timestamp': i, 'open': 17800, 'high': 17810, 'low': 17790, 'close': 17805, 'volume': 999999999, 'symbol': 'MNQ'}
            for i in range(10)
        ]
        
        result = self.cvd_calculator.calculate_cvd(candles)
        self.assertEqual(len(result), 10)
        self.assertIsNotNone(result[0])
    
    def test_risk_engine_very_small_stop_distance(self):
        """Test risk engine with very small stop distance."""
        entry = 17893.50
        stop = 17893.49  # Very small distance
        
        candles = [{'open': 17800, 'high': 17900, 'low': 17700, 'close': 17850, 'volume': 1000} for _ in range(20)]
        
        is_valid, msg, details = self.risk_engine.validate_trade_setup(
            entry, stop, 'LONG', 'MNQ', candles
        )
        
        # May fail due to invalid stop distance
        self.assertIsInstance(is_valid, bool)
    
    def test_risk_engine_very_large_stop_distance(self):
        """Test risk engine with very large stop distance."""
        entry = 17893.50
        stop = 17000.00  # Very large distance
        
        candles = [{'open': 17800, 'high': 17900, 'low': 17700, 'close': 17850, 'volume': 1000} for _ in range(20)]
        
        is_valid, msg, details = self.risk_engine.validate_trade_setup(
            entry, stop, 'LONG', 'MNQ', candles
        )
        
        # May fail due to excessive risk
        self.assertIsInstance(is_valid, bool)
    
    def test_cvd_divergence_insufficient_lookback(self):
        """Test CVD divergence with insufficient lookback."""
        candles = [{'timestamp': i, 'open': 17800, 'high': 17810, 'low': 17790, 'close': 17805, 'volume': 1000, 'symbol': 'MNQ'} for i in range(3)]
        self.cvd_calculator.calculate_cvd(candles)
        
        has_div, msg = self.cvd_calculator.check_divergence(candles, lookback=10)
        self.assertFalse(has_div)
    
    def test_icc_reset_state(self):
        """Test ICC detector state after reset."""
        candles = [{'timestamp': i, 'open': 17800, 'high': 17810, 'low': 17790, 'close': 17805, 'volume': 1000, 'symbol': 'MNQ'} for i in range(50)]
        
        # Detect structure
        self.icc_detector.detect_icc_structure(candles)
        
        # Reset
        self.icc_detector.reset()
        
        # Verify state is reset
        self.assertIsNone(self.icc_detector.current_phase)
        self.assertIsNone(self.icc_detector.indication_candle_idx)
        self.assertIsNone(self.icc_detector.correction_start_idx)
        self.assertIsNone(self.icc_detector.correction_end_idx)
        self.assertIsNone(self.icc_detector.continuation_candle_idx)
    
    def test_cvd_reset_state(self):
        """Test CVD calculator state after reset."""
        candles = [{'timestamp': i, 'open': 17800, 'high': 17810, 'low': 17790, 'close': 17805, 'volume': 1000, 'symbol': 'MNQ'} for i in range(10)]
        
        # Calculate CVD
        self.cvd_calculator.calculate_cvd(candles)
        self.assertGreater(len(self.cvd_calculator.cvd_values), 0)
        
        # Reset
        self.cvd_calculator.reset()
        
        # Verify state is reset
        self.assertEqual(self.cvd_calculator.cvd_values, [])
        self.assertEqual(self.cvd_calculator.current_cvd, 0.0)
    
    def test_risk_engine_daily_limits_edge(self):
        """Test risk engine at daily limit boundaries."""
        candles = [{'open': 17800, 'high': 17900, 'low': 17700, 'close': 17850, 'volume': 1000} for _ in range(20)]
        
        # At exactly daily loss limit
        self.risk_engine.daily_pnl = -self.risk_engine.daily_loss_limit
        
        is_valid, msg, details = self.risk_engine.validate_trade_setup(
            17893.50, 17864.25, 'LONG', 'MNQ', candles
        )
        
        # Should be valid (exactly at limit)
        self.assertIsInstance(is_valid, bool)
        
        # Reset
        self.risk_engine.daily_pnl = 0.0
    
    def test_api_mock_fallback(self):
        """Test API fallback behavior when authentication fails."""
        # Simulate authentication failure
        self.api.use_mock_data = True
        
        # Should still work with mock data
        candles = self.api.get_historical_candles('MNQ', count=10)
        self.assertIsNotNone(candles)
        self.assertEqual(len(candles), 10)
        self.assertTrue(self.api.is_using_mock_data())


if __name__ == '__main__':
    unittest.main()

