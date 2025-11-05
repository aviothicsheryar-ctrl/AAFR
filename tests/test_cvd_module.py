"""
Test suite for CVD (Cumulative Volume Delta) calculation module.
Tests CVD calculation, divergence detection, and phase analysis.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from aafr.cvd_module import CVDCalculator
from aafr.utils import generate_mock_candles


class TestCVDModule(unittest.TestCase):
    """Test cases for CVD calculation module."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.calculator = CVDCalculator()
        self.symbol = 'MNQ'
    
    def test_calculator_initialization(self):
        """Test CVD calculator initialization."""
        self.assertIsNotNone(self.calculator)
        self.assertEqual(self.calculator.cvd_values, [])
        self.assertEqual(self.calculator.current_cvd, 0.0)
    
    def test_calculate_cvd(self):
        """Test CVD calculation from candles."""
        candles = generate_mock_candles(50, self.symbol)
        cvd_values = self.calculator.calculate_cvd(candles)
        
        self.assertIsNotNone(cvd_values)
        self.assertEqual(len(cvd_values), len(candles))
        self.assertEqual(len(self.calculator.cvd_values), len(candles))
        
        # CVD should be cumulative
        if len(cvd_values) > 1:
            # Check that values change (not all zeros)
            self.assertNotEqual(set(cvd_values), {0})
    
    def test_calculate_volume_deltas(self):
        """Test volume delta calculation."""
        candles = generate_mock_candles(20, self.symbol)
        deltas = self.calculator._calculate_volume_deltas(candles)
        
        self.assertIsNotNone(deltas)
        self.assertEqual(len(deltas), len(candles))
        
        # Deltas can be positive or negative
        for delta in deltas:
            self.assertIsInstance(delta, (int, float))
    
    def test_check_divergence(self):
        """Test CVD divergence detection."""
        candles = generate_mock_candles(50, self.symbol)
        self.calculator.calculate_cvd(candles)
        
        has_divergence, div_msg = self.calculator.check_divergence(candles, lookback=5)
        
        self.assertIsInstance(has_divergence, bool)
        self.assertIsInstance(div_msg, str)
        
        # Test with insufficient data
        short_candles = generate_mock_candles(3, self.symbol)
        has_div, msg = self.calculator.check_divergence(short_candles)
        self.assertFalse(has_div)
    
    def test_analyze_indication_phase(self):
        """Test indication phase CVD analysis."""
        candles = generate_mock_candles(50, self.symbol)
        self.calculator.calculate_cvd(candles)
        
        indication_idx = 25
        is_valid, msg = self.calculator.analyze_indication_phase(candles, indication_idx)
        
        self.assertIsInstance(is_valid, bool)
        self.assertIsInstance(msg, str)
        
        # Test invalid index
        is_valid_invalid, msg_invalid = self.calculator.analyze_indication_phase(candles, -1)
        self.assertFalse(is_valid_invalid)
    
    def test_analyze_correction_phase(self):
        """Test correction phase CVD analysis."""
        candles = generate_mock_candles(50, self.symbol)
        self.calculator.calculate_cvd(candles)
        
        correction_start = 20
        correction_end = 25
        is_valid, msg = self.calculator.analyze_correction_phase(candles, correction_start, correction_end)
        
        self.assertIsInstance(is_valid, bool)
        self.assertIsInstance(msg, str)
        
        # Test invalid range
        is_valid_invalid, msg_invalid = self.calculator.analyze_correction_phase(candles, 25, 20)
        self.assertFalse(is_valid_invalid)
    
    def test_analyze_continuation_phase(self):
        """Test continuation phase CVD analysis."""
        candles = generate_mock_candles(50, self.symbol)
        self.calculator.calculate_cvd(candles)
        
        continuation_idx = 30
        is_valid, msg = self.calculator.analyze_continuation_phase(candles, continuation_idx)
        
        self.assertIsInstance(is_valid, bool)
        self.assertIsInstance(msg, str)
        
        # Test invalid index
        is_valid_invalid, msg_invalid = self.calculator.analyze_continuation_phase(candles, 1000)
        self.assertFalse(is_valid_invalid)
    
    def test_get_cvd_slope(self):
        """Test CVD slope calculation."""
        candles = generate_mock_candles(50, self.symbol)
        self.calculator.calculate_cvd(candles)
        
        slope = self.calculator.get_cvd_slope(lookback=5)
        
        self.assertIsNotNone(slope)
        self.assertIsInstance(slope, (int, float))
        
        # Test with insufficient data
        new_calc = CVDCalculator()
        slope_short = new_calc.get_cvd_slope()
        self.assertEqual(slope_short, 0.0)
    
    def test_reset(self):
        """Test CVD calculator reset."""
        candles = generate_mock_candles(50, self.symbol)
        self.calculator.calculate_cvd(candles)
        
        self.assertGreater(len(self.calculator.cvd_values), 0)
        
        self.calculator.reset()
        
        self.assertEqual(self.calculator.cvd_values, [])
        self.assertEqual(self.calculator.current_cvd, 0.0)
    
    def test_cvd_cumulative_property(self):
        """Test that CVD values are cumulative."""
        candles = generate_mock_candles(10, self.symbol)
        cvd_values = self.calculator.calculate_cvd(candles)
        
        # CVD should generally trend (cumulative sum)
        # Not necessarily monotonic, but should change
        changes = [cvd_values[i] - cvd_values[i-1] for i in range(1, len(cvd_values))]
        
        # At least some changes should be non-zero
        non_zero_changes = [c for c in changes if c != 0]
        self.assertGreater(len(non_zero_changes), 0)


if __name__ == '__main__':
    unittest.main()

