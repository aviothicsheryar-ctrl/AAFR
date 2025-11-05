"""
Test suite for extended backtest metrics.
Tests profit factor, Sharpe ratio, win/loss R multiples, and equity curve summary.
"""

import unittest
import math

from aafr.backtester import Backtester
from aafr.utils import generate_mock_candles


class TestBacktestMetrics(unittest.TestCase):
    """Test extended backtest metrics calculation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.backtester = Backtester()
    
    def test_profit_factor_calculation(self):
        """Test profit factor calculation."""
        candles = generate_mock_candles(200, "MNQ")
        results = self.backtester.run_backtest(candles, "MNQ", start_equity=150000)
        
        # Verify profit factor is present
        self.assertIn('profit_factor', results)
        self.assertIsInstance(results['profit_factor'], (int, float))
        self.assertGreaterEqual(results['profit_factor'], 0.0)
        
        # If there are trades, verify calculation
        if results['total_trades'] > 0:
            gross_profit = results.get('gross_profit', 0.0)
            gross_loss = results.get('gross_loss', 0.0)
            
            if gross_loss > 0:
                expected_pf = gross_profit / gross_loss
                self.assertAlmostEqual(results['profit_factor'], expected_pf, places=2)
    
    def test_sharpe_ratio_calculation(self):
        """Test Sharpe ratio calculation."""
        candles = generate_mock_candles(200, "MNQ")
        results = self.backtester.run_backtest(candles, "MNQ", start_equity=150000)
        
        # Verify Sharpe ratio is present
        self.assertIn('sharpe_ratio', results)
        self.assertIsInstance(results['sharpe_ratio'], (int, float))
        
        # Sharpe ratio should be a real number (can be negative)
        self.assertFalse(math.isnan(results['sharpe_ratio']))
        self.assertFalse(math.isinf(results['sharpe_ratio']))
    
    def test_win_loss_r_multiples(self):
        """Test win/loss R multiple calculations."""
        candles = generate_mock_candles(200, "MNQ")
        results = self.backtester.run_backtest(candles, "MNQ", start_equity=150000)
        
        # Verify win/loss R multiples are present
        self.assertIn('avg_win_r', results)
        self.assertIn('avg_loss_r', results)
        
        self.assertIsInstance(results['avg_win_r'], (int, float))
        self.assertIsInstance(results['avg_loss_r'], (int, float))
        
        # If there are trades, verify values make sense
        if results['total_trades'] > 0:
            # Win R should be positive (or zero if no wins)
            self.assertGreaterEqual(results['avg_win_r'], 0.0)
            # Loss R should be positive (abs value of negative R)
            self.assertGreaterEqual(results['avg_loss_r'], 0.0)
    
    def test_avg_win_loss_sizes(self):
        """Test average win/loss size calculations."""
        candles = generate_mock_candles(200, "MNQ")
        results = self.backtester.run_backtest(candles, "MNQ", start_equity=150000)
        
        # Verify avg win/loss are present
        self.assertIn('avg_win', results)
        self.assertIn('avg_loss', results)
        
        self.assertIsInstance(results['avg_win'], (int, float))
        self.assertIsInstance(results['avg_loss'], (int, float))
        
        # Avg win should be positive (or zero)
        self.assertGreaterEqual(results['avg_win'], 0.0)
        # Avg loss should be positive (abs value)
        self.assertGreaterEqual(results['avg_loss'], 0.0)
    
    def test_equity_curve_summary(self):
        """Test equity curve summary calculation."""
        candles = generate_mock_candles(200, "MNQ")
        results = self.backtester.run_backtest(candles, "MNQ", start_equity=150000)
        
        # Verify equity curve summary is present
        self.assertIn('equity_curve_summary', results)
        summary = results['equity_curve_summary']
        
        self.assertIsInstance(summary, dict)
        self.assertIn('min_equity', summary)
        self.assertIn('max_equity', summary)
        self.assertIn('peak_equity_date', summary)
        self.assertIn('peak_equity_value', summary)
        
        # Verify values
        self.assertIsInstance(summary['min_equity'], (int, float))
        self.assertIsInstance(summary['max_equity'], (int, float))
        self.assertGreaterEqual(summary['max_equity'], summary['min_equity'])
        self.assertEqual(summary['max_equity'], summary['peak_equity_value'])
    
    def test_gross_profit_loss(self):
        """Test gross profit and loss calculations."""
        candles = generate_mock_candles(200, "MNQ")
        results = self.backtester.run_backtest(candles, "MNQ", start_equity=150000)
        
        # Verify gross profit/loss are present
        self.assertIn('gross_profit', results)
        self.assertIn('gross_loss', results)
        
        self.assertIsInstance(results['gross_profit'], (int, float))
        self.assertIsInstance(results['gross_loss'], (int, float))
        
        # Both should be non-negative
        self.assertGreaterEqual(results['gross_profit'], 0.0)
        self.assertGreaterEqual(results['gross_loss'], 0.0)
        
        # Net P&L should equal gross profit - gross loss
        if results['total_trades'] > 0:
            expected_net = results['gross_profit'] - results['gross_loss']
            self.assertAlmostEqual(results['net_pnl'], expected_net, places=2)
    
    def test_metrics_consistency(self):
        """Test that all metrics are consistent with each other."""
        candles = generate_mock_candles(200, "MNQ")
        results = self.backtester.run_backtest(candles, "MNQ", start_equity=150000)
        
        # Verify win rate consistency
        if results['total_trades'] > 0:
            wins = results.get('wins', 0)
            losses = results.get('losses', 0)
            expected_wr = (wins / results['total_trades']) * 100.0
            self.assertAlmostEqual(results['win_rate'], expected_wr, places=2)
            
            # Verify win + loss equals total trades
            self.assertEqual(wins + losses, results['total_trades'])
    
    def test_empty_trades_metrics(self):
        """Test that metrics handle zero trades correctly."""
        # Generate candles that won't trigger trades
        candles = generate_mock_candles(50, "MNQ")  # Small sample
        results = self.backtester.run_backtest(candles, "MNQ", start_equity=150000)
        
        # Verify all metrics are present even with zero trades
        self.assertEqual(results['total_trades'], 0)
        self.assertEqual(results['win_rate'], 0.0)
        self.assertEqual(results['avg_r'], 0.0)
        self.assertEqual(results['profit_factor'], 0.0)
        self.assertEqual(results['sharpe_ratio'], 0.0)
        self.assertEqual(results['avg_win'], 0.0)
        self.assertEqual(results['avg_loss'], 0.0)
        self.assertEqual(results['final_equity'], 150000.0)


if __name__ == "__main__":
    unittest.main()

