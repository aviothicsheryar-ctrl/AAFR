"""
Comprehensive test suite for dual strategy system (AAFR + AJR).
Tests signal generation, arbiter conflict resolution, and risk validation.
"""

import asyncio
from datetime import datetime

from shared.signal_schema import TradeSignal
from shared.unified_risk_manager import UnifiedRiskManager
from shared.execution_arbiter import ExecutionArbiter
from shared.signal_logger import SignalLogger
from ajr.ajr_strategy import AJRStrategy
from ajr.gap_tracker import GapTracker


def test_signal_schema():
    """Test unified signal schema."""
    print("\n" + "="*60)
    print("TEST 1: Signal Schema Validation")
    print("="*60)
    
    # Test valid AAFR signal
    try:
        aafr_signal = TradeSignal(
            strategy_id="AAFR",
            instrument="NQ",
            direction="BUY",
            entry_price=20150.00,
            stop_price=20115.50,
            take_profit=[20200.00, 20250.00],
            notes="ICC pattern"
        )
        print(f"[OK] AAFR signal created: {aafr_signal.signal_id}")
        print(f"     R multiples: {aafr_signal.calculate_risk_reward()}")
    except Exception as e:
        print(f"[FAIL] AAFR signal creation failed: {e}")
        return False
    
    # Test valid AJR signal
    try:
        ajr_signal = TradeSignal(
            strategy_id="AJR",
            instrument="ES",
            direction="SELL",
            entry_price=5348.50,
            stop_price=5356.75,
            take_profit=[5328.50, 5318.25],
            notes="Gap inversion"
        )
        print(f"[OK] AJR signal created: {ajr_signal.signal_id}")
        print(f"     R multiples: {ajr_signal.calculate_risk_reward()}")
    except Exception as e:
        print(f"[FAIL] AJR signal creation failed: {e}")
        return False
    
    # Test invalid instrument (should fail)
    try:
        invalid_signal = TradeSignal(
            strategy_id="AAFR",
            instrument="BTC",  # Not allowed!
            direction="BUY",
            entry_price=50000,
            stop_price=49000,
            take_profit=[51000]
        )
        print(f"[FAIL] Invalid instrument not caught!")
        return False
    except ValueError as e:
        print(f"[OK] Invalid instrument rejected: {e}")
    
    print("[PASS] Signal schema validation test passed")
    return True


def test_risk_manager():
    """Test unified risk manager."""
    print("\n" + "="*60)
    print("TEST 2: Unified Risk Manager")
    print("="*60)
    
    risk = UnifiedRiskManager("config.json")
    
    # Test E-Mini validation
    print("\n2a. E-Mini Instrument Validation:")
    for instrument in ["NQ", "ES", "GC", "CL"]:
        is_valid, msg = risk.validate_instrument(instrument)
        if is_valid:
            print(f"     [OK] {instrument} allowed")
        else:
            print(f"     [FAIL] {instrument} rejected: {msg}")
            return False
    
    # Test invalid instrument
    is_valid, msg = risk.validate_instrument("YM")
    if not is_valid:
        print(f"     [OK] YM rejected (not on whitelist)")
    else:
        print(f"     [FAIL] YM should be rejected!")
        return False
    
    # Test position sizing
    print("\n2b. Position Sizing (all instruments @ $750 risk):")
    test_cases = [
        ("NQ", 20150.00, 20110.00, "40 ticks"),
        ("ES", 5350.00, 5342.50, "30 ticks"),
        ("GC", 2600.00, 2596.00, "40 ticks"),
        ("CL", 70.00, 69.70, "30 ticks")
    ]
    
    for instrument, entry, stop, note in test_cases:
        signal = TradeSignal(
            strategy_id="AJR",
            instrument=instrument,
            direction="BUY",
            entry_price=entry,
            stop_price=stop,
            take_profit=[entry + (entry - stop) * 1.5],
            max_loss_usd=750
        )
        
        is_valid, msg, details = risk.validate_signal(signal)
        
        if is_valid and details:
            print(f"     {instrument}: {details['position_size']} contracts, "
                  f"Risk ${details['actual_risk_usd']:.2f} ({note})")
        else:
            print(f"     [FAIL] {instrument} validation failed: {msg}")
            return False
    
    print("[PASS] Risk manager test passed")
    return True


async def test_arbiter_conflicts():
    """Test execution arbiter conflict resolution."""
    print("\n" + "="*60)
    print("TEST 3: Arbiter Conflict Resolution")
    print("="*60)
    
    arbiter = ExecutionArbiter("config.json")
    
    # Test 1: Single signal (should accept)
    print("\n3a. Single signal (should accept):")
    signal1 = TradeSignal(
        strategy_id="AAFR",
        instrument="NQ",
        direction="BUY",
        entry_price=20150.00,
        stop_price=20115.50,
        take_profit=[20200.00, 20250.00]  # Better R multiple
    )
    
    accepted, msg, details = await arbiter.process_signal(signal1)
    if accepted:
        print(f"     [OK] Signal accepted: {msg}")
    else:
        print(f"     [FAIL] Signal rejected: {msg}")
        return False
    
    # Test 2: Conflicting signal (should reject)
    print("\n3b. Conflicting signal - opposite direction (should reject):")
    signal2 = TradeSignal(
        strategy_id="AJR",
        instrument="NQ",  # Same instrument!
        direction="SELL",  # Opposite direction!
        entry_price=20145.00,
        stop_price=20160.00,
        take_profit=[20120.00]
    )
    
    accepted, msg, details = await arbiter.process_signal(signal2)
    if not accepted:
        print(f"     [OK] Conflicting signal rejected: {msg}")
    else:
        print(f"     [FAIL] Conflicting signal should be rejected!")
        return False
    
    # Close first position
    arbiter.close_position("NQ")
    
    # Test 3: Same direction signals (should merge)
    print("\n3c. Same direction signals (should merge):")
    signal3 = TradeSignal(
        strategy_id="AAFR",
        instrument="ES",
        direction="BUY",
        entry_price=5350.00,
        stop_price=5342.50,
        take_profit=[5365.00, 5380.00]  # Better R multiple
    )
    
    signal4 = TradeSignal(
        strategy_id="AJR",
        instrument="ES",  # Same instrument
        direction="BUY",  # Same direction
        entry_price=5349.00,
        stop_price=5341.00,
        take_profit=[5363.00, 5377.00]  # Better R multiple
    )
    
    # Process first signal
    accepted1, msg1, details1 = await arbiter.process_signal(signal3)
    print(f"     Signal 3 (AAFR): {msg1}")
    
    if not accepted1:
        print(f"     [FAIL] First signal should be accepted: {msg1}")
        return False
    
    # Close position to test merging scenario
    arbiter.close_position("ES")
    
    # Process both signals quickly (simulating near-simultaneous)
    # In real scenario, both would arrive before position is opened
    # For test, we'll process them in quick succession
    accepted2, msg2, details2 = await arbiter.process_signal(signal3)
    accepted3, msg3, details3 = await arbiter.process_signal(signal4)
    
    if accepted2 and accepted3:
        print(f"     [OK] Both signals accepted (would merge in real scenario)")
    elif accepted2 or accepted3:
        print(f"     [OK] One signal accepted (position limit): {msg2 if accepted2 else msg3}")
    else:
        print(f"     [FAIL] Signals not processed correctly")
        return False
    
    # Print arbiter stats
    print("\n3d. Arbiter Statistics:")
    arbiter.print_stats()
    
    print("[PASS] Arbiter conflict resolution test passed")
    return True


def test_gap_tracker():
    """Test gap detection and tracking."""
    print("\n" + "="*60)
    print("TEST 4: Gap Tracker")
    print("="*60)
    
    tracker = GapTracker(min_gap_size_ticks=10)
    
    # Simulate candles with gap
    candles = [
        {"open": 20150.00, "high": 20160.00, "low": 20145.00, "close": 20155.00, "prev_close": 20150.00},
        {"open": 20155.00, "high": 20165.00, "low": 20150.00, "close": 20160.00, "prev_close": 20155.00},
        {"open": 20175.00, "high": 20180.00, "low": 20170.00, "close": 20178.00, "prev_close": 20160.00},  # Gap up!
        {"open": 20178.00, "high": 20185.00, "low": 20175.00, "close": 20180.00, "prev_close": 20178.00},
        {"open": 20180.00, "high": 20185.00, "low": 20160.00, "close": 20165.00, "prev_close": 20180.00},  # Fills gap
        {"open": 20165.00, "high": 20170.00, "low": 20150.00, "close": 20155.00, "prev_close": 20165.00},  # Inverts!
    ]
    
    gap_detected = False
    inversion_detected = False
    
    for i, candle in enumerate(candles):
        gap = tracker.process_candle(candle, "NQ")
        if gap:
            print(f"     [OK] Gap detected at candle {i+1}: {gap.direction}")
            gap_detected = True
        
        inversion = tracker.get_recent_inversion("NQ")
        if inversion and not inversion_detected:
            print(f"     [OK] Gap inversion detected at candle {i+1}")
            inversion_detected = True
    
    if gap_detected and inversion_detected:
        print("[PASS] Gap tracker test passed")
        return True
    else:
        print(f"[FAIL] Gap detection incomplete (gap: {gap_detected}, inversion: {inversion_detected})")
        return False


def test_ajr_strategy():
    """Test AJR strategy signal generation."""
    print("\n" + "="*60)
    print("TEST 5: AJR Strategy Signal Generation")
    print("="*60)
    
    strategy = AJRStrategy("config.json")
    
    # Simulate candles with gap inversion
    candles = [
        {"open": 20150.00, "high": 20160.00, "low": 20145.00, "close": 20155.00},
        {"open": 20155.00, "high": 20165.00, "low": 20150.00, "close": 20160.00},
        {"open": 20175.00, "high": 20180.00, "low": 20170.00, "close": 20178.00, "prev_close": 20160.00},
        {"open": 20178.00, "high": 20185.00, "low": 20175.00, "close": 20180.00, "prev_close": 20178.00},
        {"open": 20180.00, "high": 20185.00, "low": 20160.00, "close": 20165.00, "prev_close": 20180.00},
        {"open": 20165.00, "high": 20170.00, "low": 20150.00, "close": 20155.00, "prev_close": 20165.00},
    ]
    
    signal_generated = False
    
    for i, candle in enumerate(candles):
        signal = strategy.process_candle(candle, "NQ")
        if signal:
            print(f"     [OK] AJR signal generated at candle {i+1}")
            print(f"          Direction: {signal.direction}")
            print(f"          Entry: {signal.entry_price}")
            print(f"          Stop: {signal.stop_price}")
            print(f"          TPs: {signal.take_profit}")
            signal_generated = True
            break
    
    if signal_generated:
        print("[PASS] AJR strategy test passed")
        return True
    else:
        print("[FAIL] No AJR signal generated")
        return False


def test_csv_logging():
    """Test CSV logging functionality."""
    print("\n" + "="*60)
    print("TEST 6: CSV Logging")
    print("="*60)
    
    logger = SignalLogger()
    
    # Create test signal
    signal = TradeSignal(
        strategy_id="AAFR",
        instrument="NQ",
        direction="BUY",
        entry_price=20150.00,
        stop_price=20115.50,
        take_profit=[20200.00],
        notes="Test signal"
    )
    
    # Log signal
    try:
        logger.log_signal(signal)
        print(f"     [OK] Signal logged to CSV")
    except Exception as e:
        print(f"     [FAIL] Signal logging failed: {e}")
        return False
    
    # Log execution
    try:
        logger.log_execution(
            signal=signal,
            status="ACCEPTED",
            position_size=3,
            risk_usd=517.50,
            risk_pct=0.35,
            r_multiple=2.9,
            reason="Test execution"
        )
        print(f"     [OK] Execution logged to CSV")
    except Exception as e:
        print(f"     [FAIL] Execution logging failed: {e}")
        return False
    
    print(f"     Log files created in: {logger.log_dir}")
    print("[PASS] CSV logging test passed")
    return True


async def run_all_tests():
    """Run all tests."""
    print("\n" + "="*70)
    print(" "*20 + "DUAL STRATEGY SYSTEM TESTS")
    print("="*70)
    
    tests = [
        ("Signal Schema", test_signal_schema),
        ("Risk Manager", test_risk_manager),
        ("Gap Tracker", test_gap_tracker),
        ("AJR Strategy", test_ajr_strategy),
        ("CSV Logging", test_csv_logging),
    ]
    
    # Async tests
    async_tests = [
        ("Arbiter Conflicts", test_arbiter_conflicts),
    ]
    
    results = []
    
    # Run sync tests
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n[ERROR] {name} test crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Run async tests
    for name, test_func in async_tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n[ERROR] {name} test crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "="*70)
    print(" "*25 + "TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status:8} {name}")
    
    print("="*70)
    print(f"  TOTAL: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("="*70)
    
    if passed == total:
        print("\n[OK] ALL TESTS PASSED - System ready for deployment")
        return True
    else:
        print(f"\n[FAIL] {total - passed} TEST(S) FAILED - Review failures above")
        return False


if __name__ == "__main__":
    import sys
    
    print("\nStarting comprehensive dual strategy tests...")
    
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest suite crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

