"""
Script to run full 1-3 month backtest on MNQ.
Generates or loads historical data and exports comprehensive results.
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aafr.backtester import Backtester
from aafr.utils import generate_mock_candles_for_period, load_config, get_formatted_timestamp
from aafr.tradovate_api import TradovateAPI


def main():
    """
    Run full 1-3 month backtest on MNQ.
    """
    print("="*70)
    print("MNQ FULL BACKTEST (1-3 Months)")
    print("="*70)
    
    # Configuration
    symbol = "MNQ"
    months = 2  # Default to 2 months (can be adjusted 1-3)
    start_equity = 150000  # TPT 150K account
    interval_minutes = 5
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months * 30)
    
    print(f"\nBacktest Period:")
    print(f"  Start: {start_date.strftime('%Y-%m-%d')}")
    print(f"  End:   {end_date.strftime('%Y-%m-%d')}")
    print(f"  Duration: {months} months")
    print(f"  Symbol: {symbol}")
    print(f"  Interval: {interval_minutes} minutes")
    
    # Generate or fetch historical data
    print(f"\n[1/3] Preparing historical data...")
    
    api = TradovateAPI()
    api.authenticate()
    
    # Try to fetch from API first, fall back to mock data
    candles = api.get_historical_candles(symbol, count=10000)  # Request large amount
    
    if not candles or len(candles) < 1000:
        print(f"[INFO] Using mock data generation for {months} month period")
        candles = generate_mock_candles_for_period(
            start_date, end_date, symbol, interval_minutes
        )
        print(f"[OK] Generated {len(candles)} candles")
    else:
        print(f"[OK] Loaded {len(candles)} candles from API")
    
    if len(candles) < 100:
        print(f"[ERROR] Insufficient data: {len(candles)} candles")
        return
    
    # Run backtest
    print(f"\n[2/3] Running backtest...")
    backtester = Backtester()
    results = backtester.run_backtest(candles, symbol, start_equity)
    
    # Display results
    print(f"\n[3/3] Backtest Results:")
    backtester.print_results(results)
    
    # Export results
    print(f"\n[4/4] Exporting results...")
    output_dir = Path("backtest_results/nq_full")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Export metrics
    metrics_file = output_dir / f"metrics_{timestamp_str}.json"
    backtester.export_metrics(results, str(metrics_file))
    print(f"[OK] Metrics exported to: {metrics_file}")
    
    # Export equity curve
    equity_file = output_dir / f"equity_curve_{timestamp_str}.csv"
    backtester.export_equity_curve(results, str(equity_file))
    print(f"[OK] Equity curve exported to: {equity_file}")
    
    # Summary
    print(f"\n{'='*70}")
    print("BACKTEST COMPLETE")
    print(f"{'='*70}")
    print(f"Total Trades: {results['total_trades']}")
    print(f"Win Rate: {results['win_rate']:.2f}%")
    print(f"Net P&L: ${results['net_pnl']:.2f}")
    print(f"Final Equity: ${results['final_equity']:.2f}")
    print(f"Max Drawdown: {results['max_drawdown_pct']:.2f}%")
    if 'profit_factor' in results:
        print(f"Profit Factor: {results['profit_factor']:.2f}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nBacktest interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

