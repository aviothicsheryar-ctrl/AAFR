"""
Script to run 2-7 day spot checks on other instruments (MES, MGC, MCL, MYM).
Generates quick backtests and comparison report.
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aafr.backtester import Backtester
from aafr.utils import generate_mock_candles_for_period, load_config
from aafr.tradovate_api import TradovateAPI


def run_spot_check(symbol: str, days: int = 5) -> dict:
    """
    Run spot check backtest for a single instrument.
    
    Args:
        symbol: Trading symbol
        days: Number of days to backtest (2-7)
    
    Returns:
        Backtest results dictionary
    """
    print(f"\n{'='*60}")
    print(f"Spot Check: {symbol} ({days} days)")
    print(f"{'='*60}")
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    print(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Generate or fetch data
    api = TradovateAPI()
    api.authenticate()
    
    candles = api.get_historical_candles(symbol, count=1000)
    
    if not candles or len(candles) < 100:
        print(f"[INFO] Using mock data for {symbol}")
        candles = generate_mock_candles_for_period(
            start_date, end_date, symbol, interval_minutes=5
        )
        print(f"[OK] Generated {len(candles)} candles")
    else:
        # Use only recent candles matching the period
        candles = candles[-len(candles):] if len(candles) < 1000 else candles[-1000:]
        print(f"[OK] Using {len(candles)} candles from API")
    
    if len(candles) < 50:
        print(f"[ERROR] Insufficient data: {len(candles)} candles")
        return {}
    
    # Run backtest
    backtester = Backtester()
    results = backtester.run_backtest(candles, symbol, start_equity=150000)
    
    # Display results
    backtester.print_results(results)
    
    return results


def main():
    """
    Run spot checks on all instruments except MNQ.
    """
    print("="*70)
    print("SPOT CHECK BACKTESTS (2-7 Days)")
    print("="*70)
    
    # Instruments to test (excluding MNQ which gets full backtest)
    instruments = ["MES", "MGC", "MCL", "MYM"]
    days = 5  # Default to 5 days (can be adjusted 2-7)
    
    print(f"\nInstruments: {', '.join(instruments)}")
    print(f"Duration: {days} days per instrument")
    
    all_results = {}
    
    # Run spot check for each instrument
    for symbol in instruments:
        try:
            results = run_spot_check(symbol, days)
            if results:
                all_results[symbol] = results
        except Exception as e:
            print(f"[ERROR] Failed to run spot check for {symbol}: {e}")
            continue
    
    if not all_results:
        print("\n[ERROR] No successful spot checks completed")
        return
    
    # Export results
    print(f"\n{'='*70}")
    print("EXPORTING RESULTS")
    print(f"{'='*70}")
    
    output_dir = Path("backtest_results/spot_checks")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Export individual results
    for symbol, results in all_results.items():
        backtester = Backtester()
        
        # Export metrics
        metrics_file = output_dir / f"{symbol}_metrics_{timestamp_str}.json"
        backtester.export_metrics(results, str(metrics_file))
        print(f"[OK] {symbol} metrics: {metrics_file}")
        
        # Export equity curve
        equity_file = output_dir / f"{symbol}_equity_curve_{timestamp_str}.csv"
        backtester.export_equity_curve(results, str(equity_file))
        print(f"[OK] {symbol} equity curve: {equity_file}")
    
    # Generate comparison report
    print(f"\n{'='*70}")
    print("SPOT CHECK COMPARISON")
    print(f"{'='*70}")
    
    print(f"\n{'Symbol':<8} {'Trades':<8} {'Win Rate':<12} {'Net P&L':<12} {'Avg R':<8} {'PF':<8}")
    print("-" * 70)
    
    for symbol, results in all_results.items():
        trades = results['total_trades']
        win_rate = results['win_rate']
        pnl = results['net_pnl']
        avg_r = results['avg_r']
        pf = results.get('profit_factor', 0.0)
        
        print(f"{symbol:<8} {trades:<8} {win_rate:>10.2f}%  ${pnl:>10.2f}  {avg_r:>6.2f}  {pf:>6.2f}")
    
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSpot checks interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Spot checks failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

