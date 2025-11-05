"""
Test suite for ICC (Indication-Correction-Continuation) detection module.
Tests pattern detection, validation, and trade level calculations.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from aafr.icc_module import ICCDetector
from aafr.utils import generate_mock_candles


class TestICCModule(unittest.TestCase):
    """Test cases for ICC detection module."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = ICCDetector()
        self.symbol = 'MNQ'
    
    def test_detector_initialization(self):
        """Test ICC detector initialization."""
        self.assertIsNotNone(self.detector)
        self.assertEqual(self.detector.min_atr_for_displacement, 1.5)
        self.assertIsNone(self.detector.current_phase)
    
    def test_detect_icc_structure_insufficient_data(self):
        """Test ICC detection with insufficient data."""
        candles = generate_mock_candles(10, self.symbol)
        result = self.detector.detect_icc_structure(candles)
        self.assertIsNone(result)
    
    def test_detect_icc_structure_complete(self):
        """Test complete ICC structure detection."""
        candles = self._create_icc_test_candles()
        result = self.detector.detect_icc_structure(candles, require_all_phases=True)
        
        self.assertIsNotNone(result)
        self.assertTrue(result.get('complete', False))
        self.assertIn('indication', result)
        self.assertIn('correction', result)
        self.assertIn('continuation', result)
    
    def test_detect_indication_phase(self):
        """Test indication phase detection."""
        candles = self._create_icc_test_candles()
        # Ensure CVD is calculated first (required for indication phase detection)
        self.detector.cvd_calculator.calculate_cvd(candles)
        indication = self.detector._detect_indication(candles)
        
        if indication:
            self.assertIn('idx', indication)
            self.assertIn('direction', indication)
            self.assertIn(indication['direction'], ['LONG', 'SHORT'])
    
    def test_detect_correction_phase(self):
        """Test correction phase detection."""
        candles = self._create_icc_test_candles()
        # Ensure CVD is calculated first
        self.detector.cvd_calculator.calculate_cvd(candles)
        indication = self.detector._detect_indication(candles)
        
        if indication:
            correction = self.detector._detect_correction(candles, indication['idx'])
            if correction:
                self.assertIn('start_idx', correction)
                self.assertIn('end_idx', correction)
    
    def test_detect_continuation_phase(self):
        """Test continuation phase detection."""
        candles = self._create_icc_test_candles()
        # Ensure CVD is calculated first
        self.detector.cvd_calculator.calculate_cvd(candles)
        indication = self.detector._detect_indication(candles)
        
        if indication:
            correction = self.detector._detect_correction(candles, indication['idx'])
            if correction:
                continuation = self.detector._detect_continuation(candles, correction['end_idx'])
                if continuation:
                    self.assertIn('idx', continuation)
                    self.assertIn('candle', continuation)
    
    def test_calculate_trade_levels(self):
        """Test trade level calculation."""
        candles = self._create_icc_test_candles()
        icc_structure = self.detector.detect_icc_structure(candles, require_all_phases=True)
        
        if icc_structure and icc_structure.get('complete'):
            entry, stop, tp, r_multiple = self.detector.calculate_trade_levels(
                icc_structure, candles, self.symbol
            )
            
            self.assertIsNotNone(entry)
            self.assertIsNotNone(stop)
            self.assertIsNotNone(tp)
            self.assertIsNotNone(r_multiple)
            self.assertGreater(r_multiple, 0)
            
            # For LONG trades, TP should be above entry, stop below
            direction = icc_structure['indication']['direction']
            if direction == 'LONG':
                self.assertGreater(tp, entry)
                self.assertLess(stop, entry)
            else:  # SHORT
                self.assertLess(tp, entry)
                self.assertGreater(stop, entry)
    
    def test_calculate_r_multiple(self):
        """Test R multiple calculation."""
        candles = generate_mock_candles(50, self.symbol)
        entry = 17800.0
        stop = 17750.0
        
        r_multiple = self.detector.calculate_r_multiple(entry, stop, candles, preferred_r=3.0)
        
        self.assertIsNotNone(r_multiple)
        self.assertGreater(r_multiple, 0)
        self.assertGreaterEqual(r_multiple, 3.0)  # Should be at least preferred R
    
    def test_validate_full_setup(self):
        """Test full setup validation."""
        candles = self._create_icc_test_candles()
        icc_structure = self.detector.detect_icc_structure(candles, require_all_phases=True)
        
        if icc_structure and icc_structure.get('complete'):
            is_valid, violations = self.detector.validate_full_setup(icc_structure, candles)
            
            self.assertIsInstance(is_valid, bool)
            self.assertIsInstance(violations, list)
            
            if not is_valid:
                self.assertGreater(len(violations), 0)
    
    def test_reset(self):
        """Test detector reset."""
        candles = self._create_icc_test_candles()
        self.detector.detect_icc_structure(candles)
        
        # Set some state
        self.detector.current_phase = 'indication'
        self.detector.indication_candle_idx = 5
        
        self.detector.reset()
        
        self.assertIsNone(self.detector.current_phase)
        self.assertIsNone(self.detector.indication_candle_idx)
    
    def _create_icc_test_candles(self):
        """Create test candles with ICC pattern."""
        candles = []
        base_price = 17800.0
        
        # Background candles (14 for ATR)
        for i in range(14):
            candles.append({
                'timestamp': i,
                'open': base_price + i * 2,
                'high': base_price + i * 2 + 3,
                'low': base_price + i * 2 - 1,
                'close': base_price + i * 2 + 2,
                'volume': 5000,
                'symbol': self.symbol
            })
        
        # INDICATION: Large bullish displacement
        candles.append({
            'timestamp': 14,
            'open': base_price + 28,
            'high': base_price + 100,
            'low': base_price + 27,
            'close': base_price + 90,  # Strong close
            'volume': 30000,
            'symbol': self.symbol
        })
        
        # Context candles
        for i in range(15, 18):
            candles.append({
                'timestamp': i,
                'open': base_price + 85 + (i - 15) * 1,
                'high': base_price + 87 + (i - 15) * 1,
                'low': base_price + 83 + (i - 15) * 1,
                'close': base_price + 86 + (i - 15) * 1,
                'volume': 6000,
                'symbol': self.symbol
            })
        
        # CORRECTION: Pullback
        for i in range(5):
            pullback = base_price + 35 - i * 3
            candles.append({
                'timestamp': 18 + i,
                'open': pullback + 2,
                'high': pullback + 5,
                'low': pullback - 2,
                'close': pullback - 1,  # Bearish
                'volume': 8000,
                'symbol': self.symbol
            })
        
        # CONTINUATION: Resume upward
        candles.append({
            'timestamp': 23,
            'open': base_price + 70,
            'high': base_price + 85,
            'low': base_price + 68,
            'close': base_price + 80,  # Bullish
            'volume': 18000,
            'symbol': self.symbol
        })
        
        # More context
        for i in range(24, 30):
            candles.append({
                'timestamp': i,
                'open': base_price + 75 + (i - 24) * 1,
                'high': base_price + 77 + (i - 24) * 1,
                'low': base_price + 73 + (i - 24) * 1,
                'close': base_price + 76 + (i - 24) * 1,
                'volume': 6000,
                'symbol': self.symbol
            })
        
        return candles


if __name__ == '__main__':
    unittest.main()

