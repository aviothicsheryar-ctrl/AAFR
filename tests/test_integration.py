"""
Integration tests for AAFR backend system.
Tests end-to-end flows and module interactions.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from aafr.main import AAFRTradingSystem
from aafr.icc_module import ICCDetector
from aafr.cvd_module import CVDCalculator
from aafr.risk_engine import RiskEngine
from aafr.tradovate_api import TradovateAPI
from aafr.utils import generate_mock_candles


class TestIntegration(unittest.TestCase):
    """Integration test cases for AAFR system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.system = AAFRTradingSystem()
        self.symbol = 'MNQ'
    
    def test_system_initialization(self):
        """Test AAFR system initialization."""
        self.assertIsNotNone(self.system)
        self.assertIsNotNone(self.system.api)
        self.assertIsNotNone(self.system.icc_detector)
        self.assertIsNotNone(self.system.cvd_calculator)
        self.assertIsNotNone(self.system.risk_engine)
        self.assertFalse(self.system.running)
        self.assertEqual(self.system.candle_buffers, {})
    
    def test_end_to_end_icc_detection(self):
        """Test end-to-end ICC detection flow."""
        candles = self._create_icc_test_candles()
        
        # Detect ICC structure
        icc_structure = self.system.icc_detector.detect_icc_structure(
            candles, require_all_phases=True
        )
        
        if icc_structure and icc_structure.get('complete'):
            # Calculate trade levels
            entry, stop, tp, r_multiple = self.system.icc_detector.calculate_trade_levels(
                icc_structure, candles, self.symbol
            )
            
            # Validate with risk engine
            is_valid, msg, trade_details = self.system.risk_engine.validate_trade_setup(
                entry, stop, icc_structure['indication']['direction'], self.symbol, candles
            )
            
            self.assertIsNotNone(entry)
            self.assertIsNotNone(stop)
            self.assertIsNotNone(tp)
            
            if is_valid:
                self.assertIn('position_size', trade_details)
                self.assertIn('dollar_risk', trade_details)
                self.assertIn('risk_percent', trade_details)
    
    def test_icc_cvd_integration(self):
        """Test ICC and CVD module integration."""
        candles = self._create_icc_test_candles()
        
        # Calculate CVD
        cvd_values = self.system.cvd_calculator.calculate_cvd(candles)
        self.assertEqual(len(cvd_values), len(candles))
        
        # Detect ICC structure (uses CVD internally)
        icc_structure = self.system.icc_detector.detect_icc_structure(
            candles, require_all_phases=True
        )
        
        if icc_structure and icc_structure.get('complete'):
            # Check CVD divergence
            has_divergence, div_msg = self.system.cvd_calculator.check_divergence(candles)
            
            # Validate setup
            is_valid, violations = self.system.icc_detector.validate_full_setup(
                icc_structure, candles
            )
            
            self.assertIsInstance(has_divergence, bool)
            self.assertIsInstance(is_valid, bool)
    
    def test_risk_engine_integration(self):
        """Test risk engine integration with trade setup."""
        candles = generate_mock_candles(100, self.symbol)
        
        # Create a mock trade setup
        entry = 17893.50
        stop = 17864.25
        direction = 'LONG'
        
        # Validate trade setup
        is_valid, msg, trade_details = self.system.risk_engine.validate_trade_setup(
            entry, stop, direction, self.symbol, candles
        )
        
        self.assertIsInstance(is_valid, bool)
        self.assertIsInstance(msg, str)
        
        if is_valid:
            self.assertIsInstance(trade_details, dict)
            
            # Check position sizing
            position_size = self.system.risk_engine.calculate_position_size(
                entry, stop, self.symbol
            )
            
            self.assertIsNotNone(position_size)
            self.assertGreater(position_size, 0)
            
            # Check risk percentage
            self.assertLessEqual(trade_details['risk_percent'], 
                               self.system.risk_engine.max_risk_per_trade)
    
    def test_api_fallback_behavior(self):
        """Test API fallback to mock data."""
        # Force API to use mock data
        self.system.api.use_mock_data = True
        
        # Get historical data (should use mock)
        candles = self.system.api.get_historical_candles(self.symbol, count=50)
        
        self.assertIsNotNone(candles)
        self.assertEqual(len(candles), 50)
        self.assertTrue(self.system.api.is_using_mock_data())
    
    def test_backtest_integration(self):
        """Test backtest integration with full system."""
        candles = self._create_icc_test_candles()
        
        # Extend candles for backtest
        extended = candles.copy()
        extended.extend(generate_mock_candles(100, self.symbol))
        
        # Run backtest
        results = self.system.run_backtest(self.symbol, candle_data=extended)
        
        self.assertIsNotNone(results)
        self.assertIn('total_trades', results)
        self.assertIn('win_rate', results)
        self.assertIn('net_pnl', results)
        self.assertIn('final_equity', results)
        
        # Equity should be set
        self.assertGreaterEqual(results['final_equity'], 0)
    
    def test_trade_signal_processing(self):
        """Test complete trade signal processing flow."""
        candles = self._create_icc_test_candles()
        
        # Detect ICC structure
        icc_structure = self.system.icc_detector.detect_icc_structure(
            candles, require_all_phases=True
        )
        
        if icc_structure and icc_structure.get('complete'):
            # Calculate levels
            entry, stop, tp, r_multiple = self.system.icc_detector.calculate_trade_levels(
                icc_structure, candles, self.symbol
            )
            
            # Validate with risk engine
            is_valid, msg, trade_details = self.system.risk_engine.validate_trade_setup(
                entry, stop, icc_structure['indication']['direction'], self.symbol, candles
            )
            
            if is_valid:
                # All conditions met - trade is valid
                signal = {
                    'timestamp': None,
                    'symbol': self.symbol,
                    'direction': icc_structure['indication']['direction'],
                    'entry': entry,
                    'stop_loss': stop,
                    'take_profit': tp,
                    'r_multiple': trade_details['r_multiple'],
                    'position_size': trade_details['position_size'],
                    'dollar_risk': trade_details['dollar_risk'],
                    'risk_percent': trade_details['risk_percent'],
                    'status': 'pending'
                }
                
                # Signal should have all required fields
                required_fields = ['symbol', 'direction', 'entry', 'stop_loss', 
                                 'take_profit', 'position_size', 'r_multiple']
                for field in required_fields:
                    self.assertIn(field, signal)
                    self.assertIsNotNone(signal[field])
    
    def test_daily_limit_enforcement(self):
        """Test daily limit enforcement in integration."""
        candles = generate_mock_candles(50, self.symbol)
        
        # Set daily loss limit exceeded
        self.system.risk_engine.daily_pnl = -1600.0
        
        entry = 17893.50
        stop = 17864.25
        
        is_valid, msg, details = self.system.risk_engine.validate_trade_setup(
            entry, stop, 'LONG', self.symbol, candles
        )
        
        # Should reject due to daily loss limit
        self.assertFalse(is_valid)
        
        # Reset for other tests
        self.system.risk_engine.daily_pnl = 0.0
    
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
            'close': base_price + 90,
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
                'close': pullback - 1,
                'volume': 8000,
                'symbol': self.symbol
            })
        
        # CONTINUATION: Resume upward
        candles.append({
            'timestamp': 23,
            'open': base_price + 70,
            'high': base_price + 85,
            'low': base_price + 68,
            'close': base_price + 80,
            'volume': 18000,
            'symbol': self.symbol
        })
        
        # More context
        for i in range(24, 50):
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

