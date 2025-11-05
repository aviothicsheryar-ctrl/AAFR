"""
Backtest demonstration with realistic ICC patterns.
This shows how the backtester would work with real historical data.
"""

import sys
sys.path.insert(0, '.')

from aafr.backtester import Backtester
from aafr.utils import generate_mock_candles

def create_backtest_data():
    """
    Create a more realistic backtest dataset with multiple ICC patterns.
    """
    candles = []
    base_price = 17800.0
    
    # Create several ICC patterns for backtesting
    
    # First ICC pattern (bullish)
    for i in range(14):
        candles.append({
            'timestamp': i,
            'open': base_price + i * 2,
            'high': base_price + i * 2 + 3,
            'low': base_price + i * 2 - 1,
            'close': base_price + i * 2 + 2,
            'volume': 5000,
            'symbol': 'MNQ'
        })
    
    # Indication
    candles.append({
        'timestamp': 14,
        'open': base_price + 28,
        'high': base_price + 100,
        'low': base_price + 27,
        'close': base_price + 90,
        'volume': 30000,
        'symbol': 'MNQ'
    })
    
    # Correction
    for i in range(15, 20):
        candles.append({
            'timestamp': i,
            'open': base_price + 85 - (i - 15) * 2,
            'high': base_price + 87 - (i - 15) * 2,
            'low': base_price + 83 - (i - 15) * 2,
            'close': base_price + 84 - (i - 15) * 2,
            'volume': 6000,
            'symbol': 'MNQ'
        })
    
    # Continuation
    candles.append({
        'timestamp': 20,
        'open': base_price + 70,
        'high': base_price + 85,
        'low': base_price + 68,
        'close': base_price + 80,
        'volume': 18000,
        'symbol': 'MNQ'
    })
    
    # Second ICC pattern (bearish)
    # Setup context
    for i in range(21, 35):
        candles.append({
            'timestamp': i,
            'open': base_price + 75 + (i - 21) * 1,
            'high': base_price + 77 + (i - 21) * 1,
            'low': base_price + 73 + (i - 21) * 1,
            'close': base_price + 76 + (i - 21) * 1,
            'volume': 5000,
            'symbol': 'MNQ'
        })
    
    # Bearish indication
    candles.append({
        'timestamp': 35,
        'open': base_price + 90,
        'high': base_price + 92,
        'low': base_price + 20,
        'close': base_price + 30,
        'volume': 30000,
        'symbol': 'MNQ'
    })
    
    # Bearish correction
    for i in range(36, 41):
        candles.append({
            'timestamp': i,
            'open': base_price + 32 + (i - 36) * 2,
            'high': base_price + 35 + (i - 36) * 2,
            'low': base_price + 30 + (i - 36) * 2,
            'close': base_price + 33 + (i - 36) * 2,
            'volume': 6000,
            'symbol': 'MNQ'
        })
    
    # Bearish continuation
    candles.append({
        'timestamp': 41,
        'open': base_price + 40,
        'high': base_price + 43,
        'low': base_price + 25,
        'close': base_price + 28,
        'volume': 18000,
        'symbol': 'MNQ'
    })
    
    # Add more data to simulate outcomes
    for i in range(42, 100):
        candles.append({
            'timestamp': i,
            'open': base_price + 25 + (i - 42) * 0.5,
            'high': base_price + 27 + (i - 42) * 0.5,
            'low': base_price + 23 + (i - 42) * 0.5,
            'close': base_price + 26 + (i - 42) * 0.5,
            'volume': 5000,
            'symbol': 'MNQ'
        })
    
    return candles

def main():
    print("="*70)
    print("BACKTEST DEMONSTRATION")
    print("="*70)
    print("\nThis shows how the backtester works with realistic ICC patterns.")
    print("Note: This uses simulated data. Real historical data would show")
    print("actual market ICC patterns.\n")
    
    # Create test data
    candles = create_backtest_data()
    print(f"Created {len(candles)} candles for backtesting\n")
    
    # Run backtest
    backtester = Backtester()
    results = backtester.run_backtest(candles, "MNQ", start_equity=150000)
    
    # Display results
    backtester.print_results(results)
    
    print("\nNOTE: With random mock data, ICC patterns may not form.")
    print("Use test_complete_system.py to see a guaranteed ICC pattern.")

if __name__ == "__main__":
    main()

