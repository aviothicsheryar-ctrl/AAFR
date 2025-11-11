"""
Script to run deep backtests on all 5 instruments using 1-minute mock data.
Generates comprehensive reports including equity curve visualizations.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aafr.backtester import Backtester
from aafr.utils import load_candles_from_json, get_micro_symbol


def main():
    """
    Run deep backtests on all 5 instruments.
    """
    print("="*70)
    print("DEEP BACKTEST - ALL INSTRUMENTS")
    print("="*70)
    
    # Configuration
    start_equity = 150000  # TPT 150K account
    data_dir = Path("data/deep_backtest")
    
    # Instruments to test (will be mapped to micro contracts)
    instruments = ["NQ", "ES", "GC", "CL", "YM"]
    
    print(f"\nConfiguration:")
    print(f"  Start Equity: ${start_equity:,.2f}")
    print(f"  Data Directory: {data_dir}")
    print(f"  Instruments: {', '.join(instruments)}")
    
    if not data_dir.exists():
        print(f"\n[ERROR] Data directory not found: {data_dir}")
        print(f"  Run scripts/generate_deep_backtest_data.py first to generate mock data")
        return
    
    # Load data and run backtests
    print(f"\n[1/3] Loading data and running backtests...")
    
    all_results = {}
    backtester = Backtester()
    
    for symbol in instruments:
        micro_symbol = get_micro_symbol(symbol)
        data_file = data_dir / f"mock_{micro_symbol}_1min.json"
        
        if not data_file.exists():
            print(f"\n  [WARNING] Data file not found: {data_file}")
            print(f"    Skipping {symbol}")
            continue
        
        print(f"\n  {'='*60}")
        print(f"  Backtesting: {symbol} ({micro_symbol})")
        print(f"  {'='*60}")
        
        try:
            # Load candle data
            candles = load_candles_from_json(str(data_file))
            print(f"  [OK] Loaded {len(candles)} candles")
            
            # Run backtest
            results = backtester.run_backtest(candles, micro_symbol, start_equity)
            
            # Store results
            all_results[symbol] = {
                'micro_symbol': micro_symbol,
                'results': results
            }
            
            # Print results
            backtester.print_results(results)
            
        except Exception as e:
            print(f"  [ERROR] Failed to backtest {symbol}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    if not all_results:
        print("\n[ERROR] No successful backtests completed")
        return
    
    # Export results
    print(f"\n[2/3] Exporting results...")
    
    output_dir = Path("backtest_results/deep_backtest")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    for symbol, data in all_results.items():
        micro_symbol = data['micro_symbol']
        results = data['results']
        
        # Export metrics
        metrics_file = output_dir / f"{micro_symbol}_metrics_{timestamp_str}.json"
        backtester.export_metrics(results, str(metrics_file))
        print(f"  [OK] {micro_symbol} metrics: {metrics_file}")
        
        # Export equity curve CSV
        equity_csv_file = output_dir / f"{micro_symbol}_equity_curve_{timestamp_str}.csv"
        backtester.export_equity_curve(results, str(equity_csv_file))
        print(f"  [OK] {micro_symbol} equity curve CSV: {equity_csv_file}")
        
        # Export equity curve PNG
        equity_png_file = output_dir / f"{micro_symbol}_equity_curve_{timestamp_str}.png"
        backtester.plot_equity_curve(results, str(equity_png_file), micro_symbol)
        print(f"  [OK] {micro_symbol} equity curve PNG: {equity_png_file}")
    
    # Generate consolidated summary
    print(f"\n[3/3] Generating consolidated summary...")
    
    summary_file = output_dir / f"summary_{timestamp_str}.json"
    summary_data = {}
    for symbol, data in all_results.items():
        micro_symbol = data['micro_symbol']
        results = data['results']
        summary_data[micro_symbol] = {
            'symbol': symbol,
            'micro_symbol': micro_symbol,
            'total_trades': results['total_trades'],
            'win_rate': results['win_rate'],
            'avg_r': results['avg_r'],
            'net_pnl': results['net_pnl'],
            'final_equity': results['final_equity'],
            'max_drawdown_pct': results['max_drawdown_pct'],
            'profit_factor': results.get('profit_factor', 0.0),
            'expectancy': results.get('expectancy', 0.0),
            'avg_trade_duration': results.get('avg_trade_duration', 0.0),
            'sharpe_ratio': results.get('sharpe_ratio', 0.0)
        }
    
    with open(summary_file, 'w') as f:
        json.dump(summary_data, f, indent=2, default=str)
    print(f"  [OK] Summary: {summary_file}")
    
    # Print comparison table
    print(f"\n{'='*70}")
    print("BACKTEST COMPARISON")
    print(f"{'='*70}")
    print(f"\n{'Symbol':<8} {'Trades':<8} {'Win Rate':<12} {'Net P&L':<12} {'Avg R':<8} {'PF':<8} {'Expectancy':<12}")
    print("-" * 80)
    
    for symbol, data in all_results.items():
        micro_symbol = data['micro_symbol']
        results = data['results']
        trades = results['total_trades']
        win_rate = results['win_rate']
        pnl = results['net_pnl']
        avg_r = results['avg_r']
        pf = results.get('profit_factor', 0.0)
        exp = results.get('expectancy', 0.0)
        
        print(f"{micro_symbol:<8} {trades:<8} {win_rate:>10.2f}%  ${pnl:>10.2f}  {avg_r:>6.2f}  {pf:>6.2f}  ${exp:>10.2f}")
    
    print(f"\n{'='*70}")
    print("DEEP BACKTEST COMPLETE")
    print(f"{'='*70}")
    print(f"\nResults exported to: {output_dir}")
    print(f"\nNext step: Generate consolidated report with:")
    print(f"  python scripts/generate_backtest_report.py")
    print(f"\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDeep backtest interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Deep backtest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

