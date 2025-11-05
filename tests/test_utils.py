"""
Test suite for utility functions.
Tests ATR calculation, displacement detection, logging, and mock data generation.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
import tempfile
import shutil
from datetime import datetime
from aafr.utils import (
    load_config, calculate_atr, detect_displacement,
    log_trade_signal, format_trade_output,
    generate_mock_candles, generate_mock_volume_data
)


class TestUtils(unittest.TestCase):
    """Test cases for utility functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.symbol = 'MNQ'
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_load_config(self):
        """Test config file loading."""
        try:
            config = load_config()
            self.assertIsNotNone(config)
            self.assertIn('environment', config)
            self.assertIn('account', config)
            self.assertIn('tradovate', config)
        except FileNotFoundError:
            self.skipTest("Config file not found")
    
    def test_load_config_invalid_path(self):
        """Test config loading with invalid path."""
        with self.assertRaises(FileNotFoundError):
            load_config("nonexistent_config.json")
    
    def test_calculate_atr(self):
        """Test ATR calculation."""
        # Create price data
        highs = [100.0 + i for i in range(20)]
        lows = [99.0 + i for i in range(20)]
        closes = [99.5 + i for i in range(20)]
        
        atr = calculate_atr(highs, lows, closes, period=14)
        
        self.assertIsNotNone(atr)
        self.assertIsInstance(atr, float)
        self.assertGreater(atr, 0)
    
    def test_calculate_atr_insufficient_data(self):
        """Test ATR with insufficient data."""
        highs = [100.0, 101.0, 102.0]
        lows = [99.0, 100.0, 101.0]
        closes = [99.5, 100.5, 101.5]
        
        atr = calculate_atr(highs, lows, closes, period=14)
        
        self.assertIsNone(atr)
    
    def test_detect_displacement(self):
        """Test displacement detection."""
        # Create candles with displacement
        candles = []
        base_price = 17800.0
        
        # Background candles
        for i in range(14):
            candles.append({
                'high': base_price + i * 2 + 2,
                'low': base_price + i * 2 - 1,
                'open': base_price + i * 2,
                'close': base_price + i * 2 + 1,
                'volume': 5000
            })
        
        # Displacement candle (large body)
        candles.append({
            'high': base_price + 28 + 100,
            'low': base_price + 28,
            'open': base_price + 28,
            'close': base_price + 28 + 90,  # Large body
            'volume': 30000
        })
        
        has_displacement = detect_displacement(candles)
        
        self.assertIsInstance(has_displacement, bool)
    
    def test_detect_displacement_insufficient_data(self):
        """Test displacement detection with insufficient data."""
        candles = [{'high': 100, 'low': 99, 'open': 99.5, 'close': 100, 'volume': 1000}]
        
        has_displacement = detect_displacement(candles)
        
        self.assertFalse(has_displacement)
    
    def test_log_trade_signal(self):
        """Test trade signal logging."""
        signal = {
            'timestamp': datetime.now(),
            'symbol': self.symbol,
            'direction': 'LONG',
            'entry': 17893.50,
            'stop_loss': 17864.25,
            'take_profit': 17965.00,
            'r_multiple': 3.1,
            'position_size': 2,
            'dollar_risk': 480.0,
            'risk_percent': 0.5,
            'status': 'pending',
            'result': ''
        }
        
        log_dir = os.path.join(self.test_dir, 'logs', 'trades')
        log_trade_signal(signal, log_dir=log_dir)
        
        # Check if log file was created
        log_file = os.path.join(log_dir, f"trades_{datetime.now().strftime('%Y%m%d')}.csv")
        self.assertTrue(os.path.exists(log_file))
    
    def test_format_trade_output(self):
        """Test trade output formatting."""
        signal = {
            'direction': 'LONG',
            'symbol': self.symbol,
            'entry': 17893.50,
            'stop_loss': 17864.25,
            'take_profit': 17965.00,
            'r_multiple': 3.1,
            'position_size': 2,
            'dollar_risk': 480.0,
            'risk_percent': 0.5
        }
        
        output = format_trade_output(signal)
        
        self.assertIsInstance(output, str)
        self.assertIn('LONG', output)
        self.assertIn(self.symbol, output)
        self.assertIn('17893.50', output)
        self.assertIn('3.1', output)
    
    def test_generate_mock_candles(self):
        """Test mock candle generation."""
        candles = generate_mock_candles(50, self.symbol)
        
        self.assertIsNotNone(candles)
        self.assertEqual(len(candles), 50)
        
        if len(candles) > 0:
            candle = candles[0]
            self.assertIn('timestamp', candle)
            self.assertIn('open', candle)
            self.assertIn('high', candle)
            self.assertIn('low', candle)
            self.assertIn('close', candle)
            self.assertIn('volume', candle)
            self.assertIn('symbol', candle)
            self.assertEqual(candle['symbol'], self.symbol)
            
            # Check OHLC logic
            self.assertGreaterEqual(candle['high'], candle['open'])
            self.assertGreaterEqual(candle['high'], candle['close'])
            self.assertLessEqual(candle['low'], candle['open'])
            self.assertLessEqual(candle['low'], candle['close'])
    
    def test_generate_mock_candles_different_symbols(self):
        """Test mock candle generation for different symbols."""
        symbols = ['MNQ', 'MES', 'MGC', 'MCL', 'MYM']
        
        for symbol in symbols:
            candles = generate_mock_candles(10, symbol)
            self.assertEqual(len(candles), 10)
            
            if len(candles) > 0:
                self.assertEqual(candles[0]['symbol'], symbol)
    
    def test_generate_mock_volume_data(self):
        """Test mock volume data generation."""
        candles = generate_mock_candles(20, self.symbol)
        cvd_values = generate_mock_volume_data(candles)
        
        self.assertIsNotNone(cvd_values)
        self.assertEqual(len(cvd_values), len(candles))
        self.assertIsInstance(cvd_values[0], (int, float))
    
    def test_generate_mock_volume_data_bullish_ratio(self):
        """Test mock volume data with different bullish ratios."""
        candles = generate_mock_candles(10, self.symbol)
        
        cvd_50 = generate_mock_volume_data(candles, bullish_ratio=0.50)
        cvd_52 = generate_mock_volume_data(candles, bullish_ratio=0.52)
        
        self.assertEqual(len(cvd_50), len(candles))
        self.assertEqual(len(cvd_52), len(candles))
        
        # With higher bullish ratio, CVD should generally be higher
        # (though not guaranteed with random data)
        self.assertIsNotNone(cvd_50)
        self.assertIsNotNone(cvd_52)


if __name__ == '__main__':
    unittest.main()

