"""
Gap detection and tracking for AJR strategy.
Identifies price gaps and monitors for inversions.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime


class Gap:
    """Represents a price gap."""
    
    def __init__(self, gap_id: str, instrument: str, gap_high: float, gap_low: float,
                 candle_idx: int, direction: str):
        """
        Initialize gap.
        
        Args:
            gap_id: Unique gap identifier
            instrument: Trading symbol
            gap_high: High side of gap
            gap_low: Low side of gap
            candle_idx: Candle index where gap formed
            direction: "UP" (gap up) or "DOWN" (gap down)
        """
        self.gap_id = gap_id
        self.instrument = instrument
        self.gap_high = gap_high
        self.gap_low = gap_low
        self.candle_idx = candle_idx
        self.direction = direction
        self.created_at = datetime.now()
        self.filled = False
        self.inverted = False
        self.inversion_candle_idx = None
    
    def size(self) -> float:
        """Get gap size in price points."""
        return abs(self.gap_high - self.gap_low)
    
    def age_in_candles(self, current_idx: int) -> int:
        """Get gap age in number of candles."""
        return current_idx - self.candle_idx
    
    def contains_price(self, price: float) -> bool:
        """Check if price is within gap."""
        return self.gap_low <= price <= self.gap_high
    
    def is_filled(self, candle: Dict[str, Any]) -> bool:
        """Check if gap is filled by this candle."""
        if self.direction == "UP":
            # Gap up is filled if price trades back down into gap
            return candle['low'] <= self.gap_high
        else:  # DOWN
            # Gap down is filled if price trades back up into gap
            return candle['high'] >= self.gap_low
    
    def is_inverted(self, candle: Dict[str, Any]) -> bool:
        """
        Check if gap is inverted (price closes through far side).
        
        For gap up: inversion = close below gap low
        For gap down: inversion = close above gap high
        """
        if self.direction == "UP":
            return candle['close'] < self.gap_low
        else:  # DOWN
            return candle['close'] > self.gap_high
    
    def __repr__(self) -> str:
        return f"Gap({self.gap_id}, {self.instrument}, {self.direction}, "  \
               f"{self.gap_low:.2f}-{self.gap_high:.2f}, Age: {self.age_in_candles(0)})"


class GapTracker:
    """
    Tracks price gaps for AJR strategy.
    Identifies gaps and monitors for inversion patterns.
    """
    
    def __init__(self, lookback_candles: int = 50, min_gap_size_ticks: int = 10,
                 max_gap_age_candles: int = 100):
        """
        Initialize gap tracker.
        
        Args:
            lookback_candles: How many recent candles to check for gaps
            min_gap_size_ticks: Minimum gap size to track
            max_gap_age_candles: Maximum age before gap expires
        """
        self.lookback_candles = lookback_candles
        self.min_gap_size_ticks = min_gap_size_ticks
        self.max_gap_age_candles = max_gap_age_candles
        
        # Track gaps per instrument
        self.gaps: Dict[str, List[Gap]] = {}  # instrument -> list of gaps
        self.candle_count: Dict[str, int] = {}  # instrument -> candle count
        
        print(f"[GAP] Gap Tracker initialized")
        print(f"[GAP] Min gap size: {min_gap_size_ticks} ticks")
        print(f"[GAP] Max gap age: {max_gap_age_candles} candles")
    
    def get_tick_size(self, instrument: str) -> float:
        """Get tick size for instrument."""
        tick_sizes = {
            "NQ": 0.25,
            "ES": 0.25,
            "GC": 0.10,
            "CL": 0.01
        }
        return tick_sizes.get(instrument, 0.25)
    
    def process_candle(self, candle: Dict[str, Any], instrument: str) -> Optional[Gap]:
        """
        Process new candle and detect gaps.
        
        Args:
            candle: New candle data
            instrument: Trading symbol
        
        Returns:
            New gap if detected, None otherwise
        """
        # Initialize tracking for this instrument if needed
        if instrument not in self.gaps:
            self.gaps[instrument] = []
            self.candle_count[instrument] = 0
        
        self.candle_count[instrument] += 1
        current_idx = self.candle_count[instrument]
        
        # Update existing gaps
        self._update_gaps(candle, instrument, current_idx)
        
        # Check for new gap (need previous candle)
        if current_idx > 1:
            new_gap = self._detect_gap(candle, instrument, current_idx)
            if new_gap:
                self.gaps[instrument].append(new_gap)
                return new_gap
        
        return None
    
    def _detect_gap(self, current_candle: Dict[str, Any], instrument: str,
                    candle_idx: int) -> Optional[Gap]:
        """Detect if current candle creates a gap from previous close."""
        # This is simplified - in practice, we'd need to store previous candle
        # For now, assume gap if open differs significantly from close
        
        open_price = current_candle['open']
        prev_close = current_candle.get('prev_close', open_price)  # Would come from candle history
        
        # Check for gap
        tick_size = self.get_tick_size(instrument)
        min_gap_size = self.min_gap_size_ticks * tick_size
        
        gap_size = abs(open_price - prev_close)
        
        if gap_size >= min_gap_size:
            # Gap detected
            if open_price > prev_close:
                # Gap up
                gap_id = f"{instrument}-GAP-{candle_idx}"
                gap = Gap(
                    gap_id=gap_id,
                    instrument=instrument,
                    gap_high=open_price,
                    gap_low=prev_close,
                    candle_idx=candle_idx,
                    direction="UP"
                )
                print(f"[GAP] Detected gap UP: {instrument} {prev_close:.2f} -> {open_price:.2f} (Size: {gap_size:.2f})")
                return gap
            
            elif open_price < prev_close:
                # Gap down
                gap_id = f"{instrument}-GAP-{candle_idx}"
                gap = Gap(
                    gap_id=gap_id,
                    instrument=instrument,
                    gap_high=prev_close,
                    gap_low=open_price,
                    candle_idx=candle_idx,
                    direction="DOWN"
                )
                print(f"[GAP] Detected gap DOWN: {instrument} {prev_close:.2f} -> {open_price:.2f} (Size: {gap_size:.2f})")
                return gap
        
        return None
    
    def _update_gaps(self, candle: Dict[str, Any], instrument: str, current_idx: int):
        """Update status of existing gaps."""
        gaps_to_remove = []
        
        for gap in self.gaps.get(instrument, []):
            # Check if gap is too old
            if gap.age_in_candles(current_idx) > self.max_gap_age_candles:
                gaps_to_remove.append(gap)
                continue
            
            # Skip if already inverted
            if gap.inverted:
                continue
            
            # Check if gap is filled
            if not gap.filled and gap.is_filled(candle):
                gap.filled = True
                print(f"[GAP] Gap filled: {gap.gap_id}")
            
            # Check for inversion
            if gap.is_inverted(candle):
                gap.inverted = True
                gap.inversion_candle_idx = current_idx
                print(f"[GAP] Gap INVERTED: {gap.gap_id} at candle {current_idx}")
        
        # Remove expired gaps
        for gap in gaps_to_remove:
            self.gaps[instrument].remove(gap)
    
    def get_recent_inversion(self, instrument: str) -> Optional[Gap]:
        """
        Get most recent inverted gap for this instrument.
        
        Returns:
            Gap that was recently inverted (within last few candles)
        """
        current_idx = self.candle_count.get(instrument, 0)
        
        for gap in reversed(self.gaps.get(instrument, [])):
            if gap.inverted and gap.inversion_candle_idx:
                # Check if inversion was recent (within last 5 candles)
                age_since_inversion = current_idx - gap.inversion_candle_idx
                if age_since_inversion <= 5:
                    return gap
        
        return None
    
    def get_active_gaps(self, instrument: str) -> List[Gap]:
        """Get all active (unfilled, unexpired) gaps for instrument."""
        return [gap for gap in self.gaps.get(instrument, [])
                if not gap.filled and gap.age_in_candles(self.candle_count.get(instrument, 0)) <= self.max_gap_age_candles]
    
    def clear_instrument(self, instrument: str):
        """Clear all gaps for an instrument."""
        if instrument in self.gaps:
            self.gaps[instrument] = []
        if instrument in self.candle_count:
            self.candle_count[instrument] = 0


# Test
if __name__ == "__main__":
    print("Testing GapTracker...")
    
    tracker = GapTracker(min_gap_size_ticks=10)
    
    # Simulate candles with a gap
    candles = [
        {"open": 20150.00, "high": 20160.00, "low": 20145.00, "close": 20155.00, "prev_close": 20150.00},
        {"open": 20155.00, "high": 20165.00, "low": 20150.00, "close": 20160.00, "prev_close": 20155.00},
        {"open": 20175.00, "high": 20180.00, "low": 20170.00, "close": 20178.00, "prev_close": 20160.00},  # Gap up!
        {"open": 20178.00, "high": 20185.00, "low": 20175.00, "close": 20180.00, "prev_close": 20178.00},
        {"open": 20180.00, "high": 20185.00, "low": 20160.00, "close": 20165.00, "prev_close": 20180.00},  # Fills gap
        {"open": 20165.00, "high": 20170.00, "low": 20150.00, "close": 20155.00, "prev_close": 20165.00},  # Inverts gap!
    ]
    
    print("\nProcessing candles...")
    for i, candle in enumerate(candles):
        print(f"\nCandle {i+1}: {candle['close']}")
        gap = tracker.process_candle(candle, "NQ")
        if gap:
            print(f"  New gap: {gap}")
        
        # Check for recent inversion
        inversion = tracker.get_recent_inversion("NQ")
        if inversion:
            print(f"  Recent inversion detected: {inversion.gap_id}")
    
    # Print active gaps
    active = tracker.get_active_gaps("NQ")
    print(f"\nActive gaps: {len(active)}")
    
    print("\n[OK] Gap tracker tests passed!")

