"""
Script to generate 1-3 months of 1-minute mock data with ICC patterns for all 5 instruments.
Exports JSON files ready for deep backtesting.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aafr.utils import generate_mock_candles_with_icc, get_micro_symbol


def main():
    """
    Generate mock data for all 5 instruments.
    """
    print("="*70)
    print("DEEP BACKTEST DATA GENERATOR")
    print("="*70)
    
    # Configuration
    months = 2  # Default to 2 months (can be adjusted 1-3)
    interval_minutes = 1  # 1-minute candles
    icc_count = 5  # Number of ICC patterns per instrument
    
    # Instruments with their base prices
    instruments = {
        "NQ": 18000,  # Will be mapped to MNQ
        "ES": 4500,   # Will be mapped to MES
        "GC": 1900,   # Will be mapped to MGC
        "CL": 80,     # Will be mapped to MCL
        "YM": 35000   # Will be mapped to MYM
    }
    
    print(f"\nConfiguration:")
    print(f"  Months: {months}")
    print(f"  Interval: {interval_minutes} minute(s)")
    print(f"  ICC Patterns per instrument: {icc_count}")
    print(f"  Instruments: {', '.join(instruments.keys())}")
    
    # Create output directory
    output_dir = Path("data/deep_backtest")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n[1/2] Generating mock data...")
    
    all_data = {}
    
    for symbol, start_price in instruments.items():
        print(f"\n  Generating data for {symbol}...")
        
        # Generate mock candles with ICC patterns
        candles = generate_mock_candles_with_icc(
            symbol=symbol,
            months=months,
            interval_minutes=interval_minutes,
            icc_count=icc_count,
            start_price=start_price
        )
        
        # Map to micro contract for filename
        micro_symbol = get_micro_symbol(symbol)
        filename = f"mock_{micro_symbol}_1min.json"
        file_path = output_dir / filename
        
        # Save to JSON
        with open(file_path, 'w') as f:
            json.dump(candles, f, indent=2, default=str)
        
        all_data[symbol] = {
            'candles': len(candles),
            'file': str(file_path)
        }
        
        print(f"    [OK] Generated {len(candles)} candles -> {file_path}")
    
    print(f"\n[2/2] Summary:")
    print(f"  Total instruments: {len(instruments)}")
    for symbol, info in all_data.items():
        print(f"  {symbol}: {info['candles']} candles")
    
    print(f"\n{'='*70}")
    print("DATA GENERATION COMPLETE")
    print(f"{'='*70}")
    print(f"\nFiles saved to: {output_dir}")
    print(f"\nNext step: Run deep backtest with:")
    print(f"  python scripts/deep_backtest_all.py")
    print(f"\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nData generation interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Data generation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

