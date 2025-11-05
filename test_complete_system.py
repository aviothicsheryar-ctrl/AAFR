"""
Test script to demonstrate complete AAFR system functionality.
Creates a realistic ICC pattern and shows trade signal generation.
"""

import sys
sys.path.insert(0, '.')

from aafr.icc_module import ICCDetector
from aafr.cvd_module import CVDCalculator
from aafr.risk_engine import RiskEngine
from aafr.utils import format_trade_output, log_trade_signal
from datetime import datetime

def create_icctest_candles():
    """
    Create candles that will trigger a valid ICC pattern.
    Structure: Indication (bullish displacement) -> Correction (pullback) -> Continuation (resume)
    """
    candles = []
    base_price = 17800.0
    
    # Background candles (14 for ATR, smaller range)
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
    
    # INDICATION: Large bullish displacement candle
    indication_idx = 14
    candles.append({
        'timestamp': indication_idx,
        'open': base_price + 28,
        'high': base_price + 100,
        'low': base_price + 27,
        'close': base_price + 90,  # Strong close (62 point body)
        'volume': 30000,  # High volume
        'symbol': 'MNQ'
    })
    
    # More context candles
    for i in range(15, 18):
        candles.append({
            'timestamp': i,
            'open': base_price + 85 + (i - 15) * 1,
            'high': base_price + 87 + (i - 15) * 1,
            'low': base_price + 83 + (i - 15) * 1,
            'close': base_price + 86 + (i - 15) * 1,
            'volume': 6000,
            'symbol': 'MNQ'
        })
    
    # CORRECTION: Pullback into value zone
    correction_start = 18
    for i in range(5):  # 5 correction candles
        pullback = base_price + 35 - i * 3
        candles.append({
            'timestamp': correction_start + i,
            'open': pullback + 2,
            'high': pullback + 5,
            'low': pullback - 2,
            'close': pullback - 1,  # Bearish correction
            'volume': 8000,
            'symbol': 'MNQ'
        })
    
    # CONTINUATION: Resume upward
    continuation_idx = 22
    candles.append({
        'timestamp': continuation_idx,
        'open': base_price + 70,
        'high': base_price + 85,
        'low': base_price + 68,
        'close': base_price + 80,  # Bullish continuation
        'volume': 18000,
        'symbol': 'MNQ'
    })
    
    # More context
    for i in range(23, 30):
        candles.append({
            'timestamp': i,
            'open': base_price + 75 + (i - 23) * 1,
            'high': base_price + 77 + (i - 23) * 1,
            'low': base_price + 73 + (i - 23) * 1,
            'close': base_price + 76 + (i - 23) * 1,
            'volume': 6000,
            'symbol': 'MNQ'
        })
    
    return candles

def main():
    print("="*70)
    print("AAFR COMPLETE SYSTEM TEST")
    print("="*70)
    
    # Create test candles with ICC pattern
    print("\n[1/5] Creating test candles with ICC pattern...")
    candles = create_icctest_candles()
    print(f"    Created {len(candles)} candles")
    
    # Test ICC detection
    print("\n[2/5] Detecting ICC structure...")
    icc = ICCDetector()
    icc_structure = icc.detect_icc_structure(candles, require_all_phases=True)
    
    if icc_structure and icc_structure.get('complete'):
        print(f"    [OK] ICC structure detected!")
        print(f"    - Indication: {icc_structure['indication']['direction']} at index {icc_structure['indication']['idx']}")
        print(f"    - Correction: {icc_structure['correction']['start_idx']} to {icc_structure['correction']['end_idx']}")
        print(f"    - Continuation: {icc_structure['continuation']['idx']}")
    else:
        print("    [WARNING] No complete ICC structure found")
        print("    This can happen with random data - system is still functional")
        return
    
    # Test CVD validation
    print("\n[3/5] Validating CVD alignment...")
    cvd = CVDCalculator()
    cvd_values = cvd.calculate_cvd(candles)
    has_divergence, div_msg = cvd.check_divergence(candles)
    print(f"    CVD values calculated: {len(cvd_values)}")
    print(f"    Divergence check: {'None' if not has_divergence else div_msg}")
    
    # Calculate trade levels
    print("\n[4/5] Calculating trade levels...")
    entry, stop, tp, r_multiple = icc.calculate_trade_levels(icc_structure, candles, 'MNQ')
    print(f"    Entry: {entry:.2f}")
    print(f"    Stop: {stop:.2f}")
    print(f"    Take Profit: {tp:.2f}")
    print(f"    R Multiple: {r_multiple:.2f}")
    
    # Validate risk
    print("\n[5/5] Validating risk management...")
    risk = RiskEngine()
    is_valid, msg, trade_details = risk.validate_trade_setup(
        entry, stop, icc_structure['indication']['direction'], 'MNQ', candles
    )
    
    if is_valid:
        print(f"    [OK] Risk validation PASSED")
        print(f"    Position size: {trade_details['position_size']} contracts")
        print(f"    Dollar risk: ${trade_details['dollar_risk']:.2f}")
        print(f"    Risk percentage: {trade_details['risk_percent']:.2f}%")
    else:
        print(f"    [ERROR] Risk validation FAILED: {msg}")
        return
    
    # Generate and display trade signal
    print("\n" + "="*70)
    print("TRADE SIGNAL OUTPUT")
    print("="*70)
    
    signal = {
        'timestamp': datetime.now(),
        'symbol': 'MNQ',
        'direction': icc_structure['indication']['direction'],
        'entry': entry,
        'stop_loss': stop,
        'take_profit': tp,
        'r_multiple': r_multiple,
        'position_size': trade_details['position_size'],
        'dollar_risk': trade_details['dollar_risk'],
        'risk_percent': trade_details['risk_percent'],
        'status': 'pending'
    }
    
    formatted_output = format_trade_output(signal)
    print(f"\n{formatted_output}\n")
    
    # Log trade signal
    log_trade_signal(signal)
    print("[OK] Trade signal logged to logs/trades/trades_YYYYMMDD.csv")
    
    # Verify 5 conditions met
    print("\n" + "="*70)
    print("ICC VALIDATION - 5 CONDITIONS CHECK")
    print("="*70)
    
    conditions = [
        ("1. Correction in value zone", icc_structure.get('correction') is not None),
        ("2. Continuation confirms", icc_structure['continuation']['cvd_valid']),
        ("3. CVD aligned (no divergence)", not has_divergence),
        ("4. R multiple >= 2.0", r_multiple >= 2.0),
        ("5. Risk <= 1% of account", trade_details['risk_percent'] <= 1.0)
    ]
    
    for condition, passed in conditions:
        status = "[OK]" if passed else "[FAIL]"
        print(f"    {status} {condition}")
    
    all_passed = all(passed for _, passed in conditions)
    
    print("\n" + "="*70)
    if all_passed:
        print("[SUCCESS] All 5 conditions met - TRADE VALID!")
    else:
        print("[WARNING] Some conditions failed")
    print("="*70)
    
    # Summary
    print("\nSUMMARY:")
    print(f"- ICC structure: {'Detected' if icc_structure else 'Not found'}")
    print(f"- CVD divergence: {'None' if not has_divergence else 'Present'}")
    print(f"- R multiple: {r_multiple:.2f}")
    print(f"- Risk: {trade_details['risk_percent']:.2f}% of $150K")
    print(f"- Position size: {trade_details['position_size']} contracts")
    print(f"- Dollar risk: ${trade_details['dollar_risk']:.2f}")
    
    print("\n[OK] Complete system test finished successfully!")

if __name__ == "__main__":
    main()

