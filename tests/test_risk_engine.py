"""
Test suite for Risk Management Engine.
Tests position sizing, trade validation, daily limits, and restricted events.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from datetime import date
from aafr.risk_engine import RiskEngine
from aafr.utils import generate_mock_candles


class TestRiskEngine(unittest.TestCase):
    """Test cases for Risk Engine module."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.risk_engine = RiskEngine()
        self.symbol = 'MNQ'
        self.entry = 17893.50
        self.stop = 17864.25
    
    def test_risk_engine_initialization(self):
        """Test risk engine initialization."""
        self.assertIsNotNone(self.risk_engine)
        self.assertEqual(self.risk_engine.account_size, 150000)
        self.assertEqual(self.risk_engine.max_risk_per_trade, 0.5)
        self.assertEqual(self.risk_engine.daily_loss_limit, 1500)
        self.assertEqual(self.risk_engine.min_r_multiple, 2.0)
    
    def test_calculate_position_size(self):
        """Test position size calculation."""
        position_size = self.risk_engine.calculate_position_size(
            self.entry, self.stop, self.symbol
        )
        
        self.assertIsNotNone(position_size)
        self.assertIsInstance(position_size, int)
        self.assertGreater(position_size, 0)
    
    def test_calculate_position_size_unknown_symbol(self):
        """Test position size calculation with unknown symbol."""
        position_size = self.risk_engine.calculate_position_size(
            self.entry, self.stop, 'UNKNOWN'
        )
        
        self.assertIsNone(position_size)
    
    def test_calculate_position_size_invalid_stop(self):
        """Test position size with invalid stop distance."""
        position_size = self.risk_engine.calculate_position_size(
            self.entry, self.entry, self.symbol  # Zero distance
        )
        
        self.assertIsNone(position_size)
    
    def test_calculate_atr_stop(self):
        """Test ATR-based stop calculation."""
        candles = generate_mock_candles(50, self.symbol)
        atr = 50.0
        
        # Test LONG stop
        stop_long = self.risk_engine.calculate_atr_stop(
            self.entry, 'LONG', atr, candles
        )
        self.assertLess(stop_long, self.entry)
        
        # Test SHORT stop
        stop_short = self.risk_engine.calculate_atr_stop(
            self.entry, 'SHORT', atr, candles
        )
        self.assertGreater(stop_short, self.entry)
    
    def test_calculate_take_profit(self):
        """Test take profit calculation."""
        r_multiple = 3.0
        
        # Test LONG take profit
        tp_long = self.risk_engine.calculate_take_profit(
            self.entry, self.stop, 'LONG', r_multiple
        )
        self.assertGreater(tp_long, self.entry)
        
        # Test SHORT take profit
        tp_short = self.risk_engine.calculate_take_profit(
            self.entry, self.stop, 'SHORT', r_multiple
        )
        self.assertLess(tp_short, self.entry)
    
    def test_validate_trade_setup_valid(self):
        """Test trade setup validation with valid parameters."""
        candles = generate_mock_candles(50, self.symbol)
        
        is_valid, msg, details = self.risk_engine.validate_trade_setup(
            self.entry, self.stop, 'LONG', self.symbol, candles
        )
        
        self.assertIsInstance(is_valid, bool)
        self.assertIsInstance(msg, str)
        
        if is_valid:
            self.assertIsInstance(details, dict)
            self.assertIn('position_size', details)
            self.assertIn('dollar_risk', details)
            self.assertIn('risk_percent', details)
            self.assertIn('r_multiple', details)
            self.assertLessEqual(details['risk_percent'], self.risk_engine.max_risk_per_trade)
    
    def test_validate_trade_setup_invalid_stop(self):
        """Test trade setup with invalid stop distance."""
        candles = generate_mock_candles(50, self.symbol)
        
        is_valid, msg, details = self.risk_engine.validate_trade_setup(
            self.entry, self.entry, 'LONG', self.symbol, candles  # Zero distance
        )
        
        self.assertFalse(is_valid)
    
    def test_is_trading_restricted(self):
        """Test restricted event detection."""
        # Test with today's date (might not be restricted)
        is_restricted = self.risk_engine.is_trading_restricted()
        self.assertIsInstance(is_restricted, bool)
        
        # Test with known restricted date
        is_restricted_known = self.risk_engine.is_trading_restricted("2025-01-31")
        self.assertTrue(is_restricted_known)
        
        # Test with non-restricted date
        is_restricted_normal = self.risk_engine.is_trading_restricted("2025-06-15")
        self.assertFalse(is_restricted_normal)
    
    def test_update_daily_pnl(self):
        """Test daily P&L update."""
        initial_pnl = self.risk_engine.daily_pnl
        
        self.risk_engine.update_daily_pnl(100.0)
        self.assertEqual(self.risk_engine.daily_pnl, initial_pnl + 100.0)
        
        self.risk_engine.update_daily_pnl(-50.0)
        self.assertEqual(self.risk_engine.daily_pnl, initial_pnl + 50.0)
    
    def test_increment_daily_trades(self):
        """Test daily trade counter increment."""
        initial_trades = self.risk_engine.daily_trades
        
        self.risk_engine.increment_daily_trades()
        self.assertEqual(self.risk_engine.daily_trades, initial_trades + 1)
        
        self.risk_engine.increment_daily_trades()
        self.assertEqual(self.risk_engine.daily_trades, initial_trades + 2)
    
    def test_reset_daily_tracking(self):
        """Test daily tracking reset."""
        # Set some values
        self.risk_engine.daily_pnl = -500.0
        self.risk_engine.daily_trades = 5
        
        self.risk_engine.reset_daily_tracking()
        
        self.assertEqual(self.risk_engine.daily_pnl, 0.0)
        self.assertEqual(self.risk_engine.daily_trades, 0)
    
    def test_get_daily_summary(self):
        """Test daily summary retrieval."""
        summary = self.risk_engine.get_daily_summary()
        
        self.assertIsInstance(summary, dict)
        self.assertIn('daily_pnl', summary)
        self.assertIn('daily_trades', summary)
        self.assertIn('remaining_risk', summary)
        self.assertIn('under_daily_limit', summary)
    
    def test_daily_loss_limit_enforcement(self):
        """Test daily loss limit enforcement."""
        candles = generate_mock_candles(50, self.symbol)
        
        # Set daily P&L to exceed loss limit
        self.risk_engine.daily_pnl = -1600.0
        
        is_valid, msg, details = self.risk_engine.validate_trade_setup(
            self.entry, self.stop, 'LONG', self.symbol, candles
        )
        
        self.assertFalse(is_valid)
        self.assertIn('Daily loss limit', msg)
        
        # Reset for other tests
        self.risk_engine.daily_pnl = 0.0
    
    def test_daily_trade_limit_enforcement(self):
        """Test daily trade limit enforcement."""
        candles = generate_mock_candles(50, self.symbol)
        
        # Set daily trades to max
        self.risk_engine.daily_trades = self.risk_engine.max_daily_trades
        
        is_valid, msg, details = self.risk_engine.validate_trade_setup(
            self.entry, self.stop, 'LONG', self.symbol, candles
        )
        
        self.assertFalse(is_valid)
        self.assertIn('Max daily trades', msg)
        
        # Reset for other tests
        self.risk_engine.daily_trades = 0


if __name__ == '__main__':
    unittest.main()

