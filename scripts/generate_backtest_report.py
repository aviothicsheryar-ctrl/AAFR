"""
Generate consolidated backtest report from all instrument results.
Consolidates metrics, generates comparison tables, and exports summary.
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aafr.utils import export_json, get_formatted_timestamp


def load_backtest_results(results_dir: Path) -> Dict[str, Dict]:
    """
    Load all backtest results from files.
    
    Args:
        results_dir: Directory containing backtest result files
    
    Returns:
        Dictionary mapping symbol to results
    """
    results = {}
    
    # Look for JSON metrics files
    for metrics_file in results_dir.glob("*_metrics_*.json"):
        try:
            with open(metrics_file, 'r') as f:
                data = json.load(f)
                
            # Extract symbol from filename or metadata
            symbol = None
            if 'backtest_metadata' in data:
                symbol = data['backtest_metadata'].get('symbol')
            else:
                # Try to extract from filename
                filename = metrics_file.stem
                for sym in ['MNQ', 'MES', 'MGC', 'MCL', 'MYM']:
                    if sym in filename:
                        symbol = sym
                        break
            
            if symbol:
                results[symbol] = data
        except Exception as e:
            print(f"[WARNING] Failed to load {metrics_file}: {e}")
    
    return results


def generate_summary_report(all_results: Dict[str, Dict], output_file: Path) -> None:
    """
    Generate markdown summary report.
    
    Args:
        all_results: Dictionary mapping symbol to results
        output_file: Path to output markdown file
    """
    with open(output_file, 'w') as f:
        f.write("# AAFR Backtest Summary Report\n\n")
        f.write(f"Generated: {get_formatted_timestamp()}\n\n")
        f.write("---\n\n")
        
        # Overview
        f.write("## Overview\n\n")
        f.write(f"Total Instruments Tested: {len(all_results)}\n")
        f.write(f"Instruments: {', '.join(sorted(all_results.keys()))}\n\n")
        
        # Summary Table
        f.write("## Summary Table\n\n")
        f.write("| Symbol | Trades | Win Rate | Net P&L | Avg R | Profit Factor | Max DD |\n")
        f.write("|--------|--------|----------|---------|-------|---------------|--------|\n")
        
        for symbol in sorted(all_results.keys()):
            r = all_results[symbol]
            f.write(f"| {symbol} | ")
            f.write(f"{r['total_trades']} | ")
            f.write(f"{r['win_rate']:.2f}% | ")
            f.write(f"${r['net_pnl']:.2f} | ")
            f.write(f"{r['avg_r']:.2f} | ")
            f.write(f"{r.get('profit_factor', 0.0):.2f} | ")
            f.write(f"{r['max_drawdown_pct']:.2f}% |\n")
        
        f.write("\n---\n\n")
        
        # Detailed Metrics per Instrument
        f.write("## Detailed Metrics\n\n")
        
        for symbol in sorted(all_results.keys()):
            r = all_results[symbol]
            f.write(f"### {symbol}\n\n")
            
            f.write("**Basic Metrics:**\n")
            f.write(f"- Total Trades: {r['total_trades']}\n")
            f.write(f"- Wins: {r.get('wins', 0)}\n")
            f.write(f"- Losses: {r.get('losses', 0)}\n")
            f.write(f"- Win Rate: {r['win_rate']:.2f}%\n")
            f.write(f"- Average R: {r['avg_r']:.2f}\n")
            f.write(f"- Net P&L: ${r['net_pnl']:.2f}\n")
            f.write(f"- Final Equity: ${r['final_equity']:.2f}\n")
            f.write(f"- Max Drawdown: ${r['max_drawdown']:.2f} ({r['max_drawdown_pct']:.2f}%)\n")
            f.write(f"- Longest Win Streak: {r['longest_win_streak']}\n")
            f.write(f"- Longest Loss Streak: {r['longest_loss_streak']}\n")
            
            if 'profit_factor' in r:
                f.write("\n**Extended Metrics:**\n")
                f.write(f"- Profit Factor: {r['profit_factor']:.2f}\n")
                f.write(f"- Sharpe Ratio: {r.get('sharpe_ratio', 0.0):.2f}\n")
                f.write(f"- Avg Win: ${r.get('avg_win', 0.0):.2f}\n")
                f.write(f"- Avg Loss: ${r.get('avg_loss', 0.0):.2f}\n")
                f.write(f"- Avg Win R: {r.get('avg_win_r', 0.0):.2f}\n")
                f.write(f"- Avg Loss R: {r.get('avg_loss_r', 0.0):.2f}\n")
                f.write(f"- Gross Profit: ${r.get('gross_profit', 0.0):.2f}\n")
                f.write(f"- Gross Loss: ${r.get('gross_loss', 0.0):.2f}\n")
            
            if 'equity_curve_summary' in r:
                summary = r['equity_curve_summary']
                f.write("\n**Equity Curve Summary:**\n")
                f.write(f"- Min Equity: ${summary['min_equity']:.2f}\n")
                f.write(f"- Max Equity: ${summary['max_equity']:.2f}\n")
                if summary.get('peak_equity_date'):
                    peak_date = summary['peak_equity_date']
                    f.write(f"- Peak Equity Date: {peak_date}\n")
            
            if 'backtest_metadata' in r:
                meta = r['backtest_metadata']
                f.write("\n**Backtest Metadata:**\n")
                f.write(f"- Candles Analyzed: {meta.get('candles_analyzed', 0)}\n")
                f.write(f"- Duration: {meta.get('duration_seconds', 0):.2f} seconds\n")
            
            f.write("\n")
        
        # Comparison Analysis
        f.write("---\n\n")
        f.write("## Comparison Analysis\n\n")
        
        # Win Rate Comparison
        f.write("### Win Rate Comparison\n\n")
        win_rates = {sym: r['win_rate'] for sym, r in all_results.items()}
        sorted_by_wr = sorted(win_rates.items(), key=lambda x: x[1], reverse=True)
        
        for symbol, wr in sorted_by_wr:
            f.write(f"- **{symbol}**: {wr:.2f}%\n")
        
        # R Multiple Comparison
        f.write("\n### Average R Multiple Comparison\n\n")
        avg_rs = {sym: r['avg_r'] for sym, r in all_results.items()}
        sorted_by_r = sorted(avg_rs.items(), key=lambda x: x[1], reverse=True)
        
        for symbol, avg_r in sorted_by_r:
            f.write(f"- **{symbol}**: {avg_r:.2f}\n")
        
        # Profit Factor Comparison
        if any('profit_factor' in r for r in all_results.values()):
            f.write("\n### Profit Factor Comparison\n\n")
            pfs = {sym: r.get('profit_factor', 0.0) for sym, r in all_results.items()}
            sorted_by_pf = sorted(pfs.items(), key=lambda x: x[1], reverse=True)
            
            for symbol, pf in sorted_by_pf:
                f.write(f"- **{symbol}**: {pf:.2f}\n")
        
        f.write("\n---\n\n")
        f.write(f"*Report generated by AAFR Backtest System*\n")


def generate_csv_summary(all_results: Dict[str, Dict], output_file: Path) -> None:
    """
    Generate CSV summary report.
    
    Args:
        all_results: Dictionary mapping symbol to results
        output_file: Path to output CSV file
    """
    import csv
    
    fieldnames = [
        'symbol', 'total_trades', 'wins', 'losses', 'win_rate', 
        'avg_r', 'net_pnl', 'final_equity', 'max_drawdown', 'max_drawdown_pct',
        'longest_win_streak', 'longest_loss_streak',
        'profit_factor', 'sharpe_ratio', 'avg_win', 'avg_loss',
        'avg_win_r', 'avg_loss_r', 'gross_profit', 'gross_loss'
    ]
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for symbol in sorted(all_results.keys()):
            r = all_results[symbol]
            row = {
                'symbol': symbol,
                'total_trades': r['total_trades'],
                'wins': r.get('wins', 0),
                'losses': r.get('losses', 0),
                'win_rate': r['win_rate'],
                'avg_r': r['avg_r'],
                'net_pnl': r['net_pnl'],
                'final_equity': r['final_equity'],
                'max_drawdown': r['max_drawdown'],
                'max_drawdown_pct': r['max_drawdown_pct'],
                'longest_win_streak': r['longest_win_streak'],
                'longest_loss_streak': r['longest_loss_streak'],
                'profit_factor': r.get('profit_factor', 0.0),
                'sharpe_ratio': r.get('sharpe_ratio', 0.0),
                'avg_win': r.get('avg_win', 0.0),
                'avg_loss': r.get('avg_loss', 0.0),
                'avg_win_r': r.get('avg_win_r', 0.0),
                'avg_loss_r': r.get('avg_loss_r', 0.0),
                'gross_profit': r.get('gross_profit', 0.0),
                'gross_loss': r.get('gross_loss', 0.0)
            }
            writer.writerow(row)


def main():
    """
    Generate consolidated backtest report.
    """
    print("="*70)
    print("GENERATING BACKTEST SUMMARY REPORT")
    print("="*70)
    
    # Load results from both directories
    nq_dir = Path("backtest_results/nq_full")
    spot_dir = Path("backtest_results/spot_checks")
    
    all_results = {}
    
    print("\n[1/3] Loading backtest results...")
    
    if nq_dir.exists():
        nq_results = load_backtest_results(nq_dir)
        all_results.update(nq_results)
        print(f"[OK] Loaded {len(nq_results)} results from nq_full")
    
    if spot_dir.exists():
        spot_results = load_backtest_results(spot_dir)
        all_results.update(spot_results)
        print(f"[OK] Loaded {len(spot_results)} results from spot_checks")
    
    if not all_results:
        print("[ERROR] No backtest results found")
        print("Run backtest_nq.py and backtest_spot_check.py first")
        return
    
    print(f"\n[OK] Total instruments: {len(all_results)}")
    print(f"Instruments: {', '.join(sorted(all_results.keys()))}")
    
    # Generate reports
    print(f"\n[2/3] Generating reports...")
    
    output_dir = Path("backtest_results/consolidated")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Markdown report
    md_file = output_dir / f"summary_report_{timestamp_str}.md"
    generate_summary_report(all_results, md_file)
    print(f"[OK] Markdown report: {md_file}")
    
    # CSV summary
    csv_file = output_dir / f"summary_{timestamp_str}.csv"
    generate_csv_summary(all_results, csv_file)
    print(f"[OK] CSV summary: {csv_file}")
    
    # JSON summary
    json_file = output_dir / f"summary_{timestamp_str}.json"
    export_json(all_results, str(json_file))
    print(f"[OK] JSON summary: {json_file}")
    
    print(f"\n[3/3] Report generation complete!")
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[ERROR] Report generation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

