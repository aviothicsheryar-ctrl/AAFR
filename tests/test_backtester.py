"""
Test suite for Backtester module.
Tests backtest execution, trade simulation, and performance metrics.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from aafr.backtester import Backtester
from aafr.utils import generate_mock_candles


class TestBacktester(unittest.TestCase):
    """Test cases for Backtester module."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.backtester = Backtester()
        self.symbol = 'MNQ'
        self.start_equity = 150000
    
    def test_backtester_initialization(self):
        """Test backtester initialization."""
        self.assertIsNotNone(self.backtester)
        self.assertIsNotNone(self.backtester.icc_detector)
        self.assertIsNotNone(self.backtester.cvd_calculator)
        self.assertIsNotNone(self.backtester.risk_engine)
        self.assertEqual(self.backtester.trades, [])
        self.assertEqual(self.backtester.equity_curve, [])
    
    def test_run_backtest(self):
        """Test backtest execution."""
        candles = generate_mock_candles(200, self.symbol)
        
        results = self.backtester.run_backtest(candles, self.symbol, self.start_equity)
        
        self.assertIsNotNone(results)
        self.assertIsInstance(results, dict)
        
        # Check required metrics
        self.assertIn('total_trades', results)
        self.assertIn('win_rate', results)
        self.assertIn('avg_r', results)
        self.assertIn('net_pnl', results)
        self.assertIn('max_drawdown', results)
        self.assertIn('max_drawdown_pct', results)
        self.assertIn('longest_win_streak', results)
        self.assertIn('longest_loss_streak', results)
        self.assertIn('final_equity', results)
        self.assertIn('equity_curve', results)
        
        # Check data types
        self.assertIsInstance(results['total_trades'], int)
        self.assertIsInstance(results['win_rate'], float)
        self.assertIsInstance(results['avg_r'], float)
        self.assertIsInstance(results['net_pnl'], float)
        self.assertIsInstance(results['final_equity'], float)
        self.assertIsInstance(results['equity_curve'], list)
    
    def test_run_backtest_empty_data(self):
        """Test backtest with insufficient data."""
        candles = generate_mock_candles(10, self.symbol)  # Too few candles
        
        results = self.backtester.run_backtest(candles, self.symbol, self.start_equity)
        
        self.assertIsNotNone(results)
        self.assertEqual(results['total_trades'], 0)
        self.assertEqual(results['win_rate'], 0.0)
        self.assertEqual(results['final_equity'], self.start_equity)
    
    def test_calculate_trade_levels(self):
        """Test trade level calculation."""
        # Create ICC structure manually
        candles = self._create_icc_test_candles()
        
        icc_structure = self.backtester.icc_detector.detect_icc_structure(
            candles, require_all_phases=True
        )
        
        if icc_structure and icc_structure.get('complete'):
            entry, stop, tp, r_multiple = self.backtester._calculate_trade_levels(
                icc_structure, candles, self.symbol
            )
            
            self.assertIsNotNone(entry)
            self.assertIsNotNone(stop)
            self.assertIsNotNone(tp)
            self.assertIsNotNone(r_multiple)
            self.assertGreater(r_multiple, 0)
    
    def test_simulate_trade_outcome(self):
        """Test trade outcome simulation."""
        entry = 17800.0
        stop = 17750.0
        tp = 17950.0
        r_multiple = 3.0
        position_size = 2
        direction = 'LONG'
        
        # Create candles that hit TP
        candles = []
        base_price = 17800.0
        for i in range(10):
            candles.append({
                'timestamp': i,
                'open': base_price + i * 5,
                'high': base_price + i * 5 + 10,
                'low': base_price + i * 5 - 5,
                'close': base_price + i * 5 + 5,
                'volume': 5000,
                'symbol': self.symbol
            })
        
        result = self.backtester._simulate_trade_outcome(
            entry, stop, tp, r_multiple, position_size, direction, candles, 0
        )
        
        self.assertIsNotNone(result)
        self.assertIn('pnl', result)
        self.assertIn('r_achieved', result)
        
        # Check outcome direction
        if result['pnl'] > 0:
            self.assertGreater(result['r_achieved'], 0)
        elif result['pnl'] < 0:
            self.assertLess(result['r_achieved'], 0)
    
    def test_simulate_trade_outcome_stop_hit(self):
        """Test trade simulation with stop loss hit."""
        entry = 17800.0
        stop = 17750.0
        tp = 17950.0
        r_multiple = 3.0
        position_size = 2
        direction = 'LONG'
        
        # Create candles that hit stop
        candles = []
        base_price = 17800.0
        for i in range(10):
            candles.append({
                'timestamp': i,
                'open': base_price - i * 10,
                'high': base_price - i * 10 + 5,
                'low': base_price - i * 10 - 10,  # Will hit stop
                'close': base_price - i * 10 - 5,
                'volume': 5000,
                'symbol': self.symbol
            })
        
        result = self.backtester._simulate_trade_outcome(
            entry, stop, tp, r_multiple, position_size, direction, candles, 0
        )
        
        # Should hit stop (negative P&L)
        self.assertLessEqual(result['pnl'], 0)
        self.assertLess(result['r_achieved'], 0)
    
    def test_calculate_metrics_no_trades(self):
        """Test metrics calculation with no trades."""
        self.backtester.trades = []
        self.backtester.current_equity = self.start_equity
        
        metrics = self.backtester._calculate_metrics()
        
        self.assertEqual(metrics['total_trades'], 0)
        self.assertEqual(metrics['win_rate'], 0.0)
        self.assertEqual(metrics['avg_r'], 0.0)
        self.assertEqual(metrics['net_pnl'], 0.0)
        self.assertEqual(metrics['final_equity'], self.start_equity)
    
    def test_calculate_metrics_with_trades(self):
        """Test metrics calculation with trades."""
        # Add mock trades
        self.backtester.trades = [
            {'status': 'win', 'result': 300.0, 'r_achieved': 3.0},
            {'status': 'win', 'result': 200.0, 'r_achieved': 2.0},
            {'status': 'loss', 'result': -150.0, 'r_achieved': -1.0},
            {'status': 'win', 'result': 250.0, 'r_achieved': 2.5},
        ]
        
        self.backtester.current_equity = self.start_equity + 600.0
        self.backtester.max_equity = self.start_equity + 600.0
        self.backtester.max_drawdown = 150.0
        self.backtester.max_drawdown_pct = 1.0
        
        # Initialize equity curve for metrics calculation
        self.backtester.equity_curve = [
            {'timestamp': 0, 'time': 0, 'equity': self.start_equity},
            {'timestamp': 1, 'time': 1, 'equity': self.start_equity + 300.0},
            {'timestamp': 2, 'time': 2, 'equity': self.start_equity + 600.0}
        ]
        
        metrics = self.backtester._calculate_metrics()
        
        self.assertEqual(metrics['total_trades'], 4)
        self.assertAlmostEqual(metrics['win_rate'], 75.0, places=1)
        self.assertAlmostEqual(metrics['avg_r'], 1.625, places=1)  # (3+2-1+2.5)/4
        self.assertAlmostEqual(metrics['net_pnl'], 600.0, places=1)
        self.assertEqual(metrics['wins'], 3)
        self.assertEqual(metrics['losses'], 1)
    
    def test_print_results(self):
        """Test results printing (should not raise exceptions)."""
        results = {
            'total_trades': 10,
            'wins': 7,
            'losses': 3,
            'win_rate': 70.0,
            'avg_r': 2.5,
            'net_pnl': 1500.0,
            'final_equity': 151500.0,
            'max_drawdown': 500.0,
            'max_drawdown_pct': 0.33,
            'longest_win_streak': 5,
            'longest_loss_streak': 2,
            'equity_curve': []
        }
        
        # Should not raise exception
        try:
            self.backtester.print_results(results)
        except Exception as e:
            self.fail(f"print_results raised exception: {e}")
    
    def _create_icc_test_candles(self):
        """Create test candles with ICC pattern."""
        candles = []
        base_price = 17800.0
        
        # Background candles
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
        
        # INDICATION
        candles.append({
            'timestamp': 14,
            'open': base_price + 28,
            'high': base_price + 100,
            'low': base_price + 27,
            'close': base_price + 90,
            'volume': 30000,
            'symbol': self.symbol
        })
        
        # Context
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
        
        # CORRECTION
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
        
        # CONTINUATION
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

