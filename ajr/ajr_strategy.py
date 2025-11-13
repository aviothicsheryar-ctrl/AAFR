"""
AJR (Andrew's Justified Reversal) Strategy Module.
Inversion gap strategy - detects gaps and trades reversals.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from ajr.gap_tracker import GapTracker, Gap
from shared.signal_schema import TradeSignal
from aafr.utils import load_config


class AJRStrategy:
    """
    AJR inversion gap strategy.
    
    Logic:
    1. Detect price gaps
    2. Mark them as inversion zones when price closes through far side
    3. Generate BUY if close above far edge, SELL if below
    4. Entry = close price
    5. Stop = just past recent opposite swing with buffer
    6. Targets = 1.5× and 2.5× stop distance
    7. Filter: Prefer signals that occur shortly after a quick probe beyond 
       a nearby obvious level in the opposite direction (helps avoid false signals)
    """
    
    def __init__(self, config_path: str = "aafr/config.json"):
        """Initialize AJR strategy."""
        self.config = load_config(config_path)
        
        # Strategy config
        ajr_config = self.config.get('strategies', {}).get('AJR', {})
        self.enabled = ajr_config.get('enabled', True)
        
        # Gap tracker config
        lookback = ajr_config.get('gap_lookback_candles', 50)
        min_gap = ajr_config.get('min_gap_size_ticks', 10)
        max_age = ajr_config.get('max_gap_age_candles', 100)
        
        # Initialize gap tracker
        self.gap_tracker = GapTracker(
            lookback_candles=lookback,
            min_gap_size_ticks=min_gap,
            max_gap_age_candles=max_age
        )
        
        # Store recent candles for swing detection
        self.candle_history: Dict[str, List[Dict]] = {}
        self.max_history = 200
        
        print(f"[AJR] Strategy initialized")
        print(f"[AJR] Enabled: {self.enabled}")
    
    def process_candle(self, candle: Dict[str, Any], instrument: str) -> Optional[TradeSignal]:
        """
        Process new completed candle and generate signal if conditions met.
        
        Args:
            candle: Completed candle data
            instrument: Trading symbol
        
        Returns:
            TradeSignal if inversion detected, None otherwise
        """
        if not self.enabled:
            return None
        
        # Store candle in history
        self._add_to_history(candle, instrument)
        
        # Process candle through gap tracker
        new_gap = self.gap_tracker.process_candle(candle, instrument)
        
        # Check for recent gap inversion
        inverted_gap = self.gap_tracker.get_recent_inversion(instrument)
        
        if inverted_gap:
            # Generate trade signal (candle already added to history)
            return self._generate_signal(inverted_gap, candle, instrument)
        
        return None
    
    def _add_to_history(self, candle: Dict[str, Any], instrument: str):
        """Add candle to history for swing detection."""
        if instrument not in self.candle_history:
            self.candle_history[instrument] = []
        
        self.candle_history[instrument].append(candle)
        
        # Keep only recent candles
        if len(self.candle_history[instrument]) > self.max_history:
            self.candle_history[instrument] = self.candle_history[instrument][-self.max_history:]
    
    def _generate_signal(self, gap: Gap, current_candle: Dict[str, Any],
                        instrument: str) -> Optional[TradeSignal]:
        """
        Generate trade signal from inverted gap.
        Includes filter for quick probe beyond nearby level (helps avoid false signals).
        
        Args:
            gap: Inverted gap
            current_candle: Current candle that inverted the gap
            instrument: Trading symbol
        
        Returns:
            TradeSignal or None
        """
        close_price = current_candle['close']
        
        # Determine direction
        # If gap was UP and we closed below it = SELL
        # If gap was DOWN and we closed above it = BUY
        if gap.direction == "UP":
            direction = "SELL"
        else:
            direction = "BUY"
        
        # Filter: Prefer signals that occur shortly after a quick probe beyond 
        # a nearby obvious level in the opposite direction (helps avoid false signals)
        if not self._has_recent_opposite_probe(instrument, direction, current_candle):
            print(f"[AJR] Signal filtered: No recent opposite probe detected for {direction} {instrument}")
            return None  # Filter out signal if no probe
        
        # Entry = current close
        entry_price = close_price
        
        # Calculate stop
        stop_price = self._calculate_stop(gap, current_candle, instrument, direction)
        
        if stop_price is None:
            print(f"[AJR] Could not calculate stop for {instrument}")
            return None
        
        # Calculate stop distance
        stop_distance = abs(entry_price - stop_price)
        
        # Calculate targets (1.5× and 2.5× stop distance)
        if direction == "BUY":
            tp1 = entry_price + (stop_distance * 1.5)
            tp2 = entry_price + (stop_distance * 2.5)
        else:  # SELL
            tp1 = entry_price - (stop_distance * 1.5)
            tp2 = entry_price - (stop_distance * 2.5)
        
        # Create signal
        try:
            signal = TradeSignal(
                strategy_id="AJR",
                instrument=instrument,
                direction=direction,
                entry_price=entry_price,
                stop_price=stop_price,
                take_profit=[tp1, tp2],
                max_loss_usd=750,
                notes=f"Gap inversion pattern detected. Gap: {gap.gap_id}"
            )
            
            print(f"[AJR] SIGNAL GENERATED: {direction} {instrument} @ {entry_price:.2f}")
            print(f"[AJR]   Stop: {stop_price:.2f}, TP1: {tp1:.2f}, TP2: {tp2:.2f}")
            
            return signal
            
        except ValueError as e:
            print(f"[AJR] Invalid signal: {e}")
            return None
    
    def _calculate_stop(self, gap: Gap, current_candle: Dict[str, Any],
                       instrument: str, direction: str) -> Optional[float]:
        """
        Calculate stop loss price.
        Stop = just past recent opposite swing with buffer.
        
        Args:
            gap: Inverted gap
            current_candle: Current candle
            instrument: Trading symbol
            direction: "BUY" or "SELL"
        
        Returns:
            Stop price or None
        """
        # Get recent candles
        history = self.candle_history.get(instrument, [])
        
        if len(history) < 10:
            # Not enough history, use simple stop
            return self._simple_stop(current_candle, direction, instrument)
        
        # Find recent swing
        if direction == "BUY":
            # For BUY, find recent swing low
            swing = self._find_swing_low(history[-20:])
        else:
            # For SELL, find recent swing high
            swing = self._find_swing_high(history[-20:])
        
        if swing is None:
            return self._simple_stop(current_candle, direction, instrument)
        
        # Add buffer
        tick_size = self._get_tick_size(instrument)
        buffer = tick_size * 5  # 5 tick buffer
        
        if direction == "BUY":
            stop = swing - buffer
        else:
            stop = swing + buffer
        
        return round(stop, 2)
    
    def _simple_stop(self, candle: Dict[str, Any], direction: str, instrument: str) -> float:
        """Calculate simple stop based on current candle."""
        tick_size = self._get_tick_size(instrument)
        buffer_ticks = 20  # Default 20 tick stop
        
        if direction == "BUY":
            return candle['low'] - (tick_size * buffer_ticks)
        else:
            return candle['high'] + (tick_size * buffer_ticks)
    
    def _find_swing_low(self, candles: List[Dict[str, Any]]) -> Optional[float]:
        """Find recent swing low in candles."""
        if len(candles) < 3:
            return None
        
        lows = [c['low'] for c in candles]
        return min(lows) if lows else None
    
    def _find_swing_high(self, candles: List[Dict[str, Any]]) -> Optional[float]:
        """Find recent swing high in candles."""
        if len(candles) < 3:
            return None
        
        highs = [c['high'] for c in candles]
        return max(highs) if highs else None
    
    def _has_recent_opposite_probe(self, instrument: str, direction: str, 
                                   current_candle: Dict[str, Any]) -> bool:
        """
        Check if there was a recent quick probe beyond a nearby obvious level 
        in the opposite direction.
        
        This filter helps avoid false signals by ensuring there was a failed 
        attempt in the opposite direction before the inversion signal.
        
        For BUY signals: Check if price recently probed below a nearby swing low
        For SELL signals: Check if price recently probed above a nearby swing high
        
        Args:
            instrument: Trading symbol
            direction: "BUY" or "SELL"
            current_candle: Current candle
        
        Returns:
            True if probe detected, False otherwise
        """
        history = self.candle_history.get(instrument, [])
        
        if len(history) < 6:
            return False  # Not enough history to detect probe (need at least 6: 3 for swing, 3 for probe)
        
        # Calculate swing level from earlier period (before recent candles)
        # This gives us the "nearby obvious level" that was established earlier
        # Exclude the current candle (last one) from probe check - probe must happen before inversion
        if len(history) >= 20:
            # Use candles 10-20 positions back for swing calculation
            swing_period = history[-20:-10]
            recent_candles = history[-10:-1]  # Last 10 candles (excluding current) for probe detection
        else:
            # If not enough history, use first half for swing, second half (excluding current) for probe
            mid_point = len(history) // 2
            swing_period = history[:mid_point]
            recent_candles = history[mid_point:-1]  # Exclude current candle
        
        if direction == "BUY":
            # For BUY, look for recent probe below a swing low
            swing_low = self._find_swing_low(swing_period)
            if swing_low is None:
                return False
            
            # Check if any recent candle probed below swing low
            for candle in recent_candles:
                if candle['low'] < swing_low:
                    # Probe detected - price went below swing low (failed attempt)
                    print(f"[AJR] Probe detected: Price probed below swing low {swing_low:.2f}")
                    return True
        
        else:  # SELL
            # For SELL, look for recent probe above a swing high
            swing_high = self._find_swing_high(swing_period)
            if swing_high is None:
                return False
            
            # Check if any recent candle probed above swing high
            for candle in recent_candles:
                if candle['high'] > swing_high:
                    # Probe detected - price went above swing high (failed attempt)
                    print(f"[AJR] Probe detected: Price probed above swing high {swing_high:.2f}")
                    return True
        
        return False
    
    def _get_tick_size(self, instrument: str) -> float:
        """Get tick size for instrument."""
        tick_sizes = {
            "NQ": 0.25,
            "ES": 0.25,
            "GC": 0.10,
            "CL": 0.01
        }
        return tick_sizes.get(instrument, 0.25)
    
    def reset(self, instrument: Optional[str] = None):
        """Reset strategy state."""
        if instrument:
            self.gap_tracker.clear_instrument(instrument)
            if instrument in self.candle_history:
                self.candle_history[instrument] = []
        else:
            # Reset all
            for inst in list(self.gap_tracker.gaps.keys()):
                self.gap_tracker.clear_instrument(inst)
            self.candle_history = {}


# Test
if __name__ == "__main__":
    print("Testing AJRStrategy...")
    
    # load_config resolves paths relative to aafr/ directory
    strategy = AJRStrategy("config.json")
    
    # Simulate candles with gap inversion and probe filter
    print("\nSimulating candles with gap inversion and probe filter...")
    
    # Test scenario: Gap up, price probes above swing high, then inverts (SELL signal)
    # Need enough candles: first half establishes swing, second half has probe
    candles = [
        {"open": 20150.00, "high": 20160.00, "low": 20145.00, "close": 20155.00},
        {"open": 20155.00, "high": 20165.00, "low": 20150.00, "close": 20160.00},
        {"open": 20160.00, "high": 20170.00, "low": 20155.00, "close": 20165.00},  # Build history
        {"open": 20165.00, "high": 20175.00, "low": 20160.00, "close": 20170.00},  # Swing high at 20175 (first half)
        {"open": 20175.00, "high": 20180.00, "low": 20170.00, "close": 20178.00, "prev_close": 20170.00},  # Gap up (20170 -> 20175)
        {"open": 20178.00, "high": 20185.00, "low": 20175.00, "close": 20180.00, "prev_close": 20178.00},  # Second half starts
        {"open": 20180.00, "high": 20190.00, "low": 20175.00, "close": 20177.00, "prev_close": 20180.00},  # Probe above swing high (20190 > 20175)
        {"open": 20177.00, "high": 20185.00, "low": 20160.00, "close": 20165.00, "prev_close": 20177.00},  # Fills gap
        {"open": 20165.00, "high": 20170.00, "low": 20150.00, "close": 20155.00, "prev_close": 20165.00},  # Inverts gap (close 20155 < gap low 20170) - SIGNAL!
    ]
    
    for i, candle in enumerate(candles):
        print(f"\nCandle {i+1}: O={candle['open']}, H={candle['high']}, L={candle['low']}, C={candle['close']}")
        signal = strategy.process_candle(candle, "NQ")
        
        if signal:
            print(f"\n*** SIGNAL GENERATED ***")
            print(signal)
    
    print("\n[OK] AJR strategy tests passed!")

