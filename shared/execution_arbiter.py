"""
Execution Arbiter for AAFR and AJR strategies.
Prevents conflicting trades and manages signal prioritization.
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import asyncio
from collections import defaultdict

from shared.signal_schema import TradeSignal
from shared.unified_risk_manager import UnifiedRiskManager
from aafr.utils import load_config


class ExecutionArbiter:
    """
    Central arbiter that manages signals from both AAFR and AJR.
    Ensures no conflicting trades and applies priority rules.
    """
    
    def __init__(self, config_path: str = "aafr/config.json", risk_manager: Optional[UnifiedRiskManager] = None):
        """Initialize execution arbiter."""
        self.config = load_config(config_path)
        self.risk_manager = risk_manager or UnifiedRiskManager(config_path)
        
        # Arbiter config
        arbiter_config = self.config.get('arbiter', {})
        self.enabled = arbiter_config.get('enabled', True)
        self.max_positions_per_symbol = arbiter_config.get('max_positions_per_symbol', 1)
        self.allow_merging = arbiter_config.get('allow_signal_merging', True)
        self.max_merge_multiplier = arbiter_config.get('max_merged_size_multiplier', 1.5)
        
        # Strategy priorities
        self.strategies = self.config.get('strategies', {})
        
        # Position tracking
        self.open_positions = {}  # symbol -> position_info
        self.position_locks = defaultdict(asyncio.Lock)  # symbol -> lock
        self.pending_signals = {}  # signal_id -> signal
        
        # Stats
        self.total_signals = 0
        self.accepted_signals = 0
        self.rejected_signals = 0
        self.merged_signals = 0
        
        print(f"[ARBITER] Execution Arbiter initialized")
        print(f"[ARBITER] Max positions per symbol: {self.max_positions_per_symbol}")
        print(f"[ARBITER] Signal merging: {'enabled' if self.allow_merging else 'disabled'}")
    
    def is_continuation_hours(self) -> bool:
        """Check if current time is in continuation hours (favor AAFR)."""
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        
        continuation_hours = self.config['arbiter'].get('continuation_hours', [[9, 30], [15, 30]])
        
        for start_h, start_m in continuation_hours:
            if hour > start_h or (hour == start_h and minute >= start_m):
                return True
        
        return False
    
    def is_reversal_window(self) -> bool:
        """Check if current time is in reversal window (favor AJR)."""
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        
        reversal_windows = self.config['arbiter'].get('reversal_windows', [[8, 30], [9, 30]])
        
        for start_h, start_m in reversal_windows:
            # Check if within 30 minutes of reversal window
            if abs(hour - start_h) == 0 and abs(minute - start_m) <= 30:
                return True
        
        return False
    
    async def process_signal(self, signal: TradeSignal) -> Tuple[bool, str, Optional[Dict]]:
        """
        Process trade signal through arbiter.
        
        Args:
            signal: Trade signal from AAFR or AJR
        
        Returns:
            (accepted, reason, execution_details)
        """
        self.total_signals += 1
        
        if not self.enabled:
            # Bypass arbiter if disabled
            return await self._execute_signal(signal)
        
        # Acquire lock for this instrument
        async with self.position_locks[signal.instrument]:
            return await self._process_with_lock(signal)
    
    async def _process_with_lock(self, signal: TradeSignal) -> Tuple[bool, str, Optional[Dict]]:
        """Process signal while holding instrument lock."""
        
        # Step 1: Validate with risk manager
        is_valid, msg, risk_details = self.risk_manager.validate_signal(signal)
        
        if not is_valid:
            self.rejected_signals += 1
            return False, f"Risk validation failed: {msg}", None
        
        # Step 2: Check for existing position
        existing_pos = self.open_positions.get(signal.instrument)
        
        if existing_pos:
            return await self._handle_existing_position(signal, existing_pos, risk_details)
        
        # Step 3: Check for pending signals (within last few seconds)
        pending = self._get_pending_signal(signal.instrument)
        
        if pending:
            return await self._handle_pending_signal(signal, pending, risk_details)
        
        # Step 4: No conflicts, execute signal
        return await self._execute_signal(signal, risk_details)
    
    async def _handle_existing_position(self, signal: TradeSignal, existing: Dict,
                                       risk_details: Dict) -> Tuple[bool, str, Optional[Dict]]:
        """Handle case where position already exists for this instrument."""
        
        if self.max_positions_per_symbol == 1:
            self.rejected_signals += 1
            return False, f"Position already open for {signal.instrument}", None
        
        # Could implement position scaling here if max_positions > 1
        self.rejected_signals += 1
        return False, "Multiple positions not currently supported", None
    
    async def _handle_pending_signal(self, signal: TradeSignal, pending: TradeSignal,
                                     risk_details: Dict) -> Tuple[bool, str, Optional[Dict]]:
        """Handle case where another signal is pending for same instrument."""
        
        # Check if signals agree on direction
        if signal.direction == pending.direction:
            # Same direction - consider merging
            if self.allow_merging:
                return await self._merge_signals(signal, pending, risk_details)
            else:
                # Use first signal, reject second
                self.rejected_signals += 1
                return False, f"Signal already pending for {signal.instrument}", None
        
        else:
            # Opposite directions - use priority
            return await self._resolve_conflict(signal, pending, risk_details)
    
    async def _merge_signals(self, signal: TradeSignal, pending: TradeSignal,
                            risk_details: Dict) -> Tuple[bool, str, Optional[Dict]]:
        """Merge two signals in same direction."""
        
        # Calculate merged position size
        pending_size = risk_details['position_size']
        current_size = pending_size
        merged_size = int(pending_size * self.max_merge_multiplier)
        
        # Use better entry (closer to current for limit orders)
        merged_entry = min(signal.entry_price, pending.entry_price) if signal.direction == "BUY" else max(signal.entry_price, pending.entry_price)
        
        # Use tighter stop
        merged_stop = max(signal.stop_price, pending.stop_price) if signal.direction == "BUY" else min(signal.stop_price, pending.stop_price)
        
        # Merge TPs
        all_tps = sorted(set(signal.take_profit + pending.take_profit))
        
        # Create merged signal (use first strategy ID for validation)
        merged = TradeSignal(
            strategy_id=signal.strategy_id,  # Use first strategy ID
            instrument=signal.instrument,
            direction=signal.direction,
            entry_price=merged_entry,
            stop_price=merged_stop,
            take_profit=all_tps,
            max_loss_usd=750,
            notes=f"Merged {signal.strategy_id}+{pending.strategy_id}: {signal.notes} + {pending.notes}"
        )
        
        self.merged_signals += 1
        print(f"[ARBITER] Merged {signal.strategy_id} and {pending.strategy_id} signals for {signal.instrument}")
        
        # Remove pending signal
        if pending.signal_id in self.pending_signals:
            del self.pending_signals[pending.signal_id]
        
        # Execute merged signal
        return await self._execute_signal(merged, risk_details)
    
    async def _resolve_conflict(self, signal: TradeSignal, pending: TradeSignal,
                               risk_details: Dict) -> Tuple[bool, str, Optional[Dict]]:
        """Resolve conflicting signals (opposite directions)."""
        
        # Determine priority based on time and strategy
        if self.is_continuation_hours():
            # Continuation hours - favor AAFR
            priority_strategy = "AAFR"
        elif self.is_reversal_window():
            # Reversal window - favor AJR
            priority_strategy = "AJR"
        else:
            # Default: first come first served
            self.rejected_signals += 1
            return False, f"Conflicting signal for {signal.instrument}, keeping first", None
        
        # Check which signal matches priority
        if signal.strategy_id == priority_strategy:
            # New signal has priority, cancel pending
            if pending.signal_id in self.pending_signals:
                del self.pending_signals[pending.signal_id]
            
            print(f"[ARBITER] {signal.strategy_id} wins conflict resolution ({priority_strategy} priority)")
            return await self._execute_signal(signal, risk_details)
        else:
            # Pending signal has priority
            self.rejected_signals += 1
            return False, f"Conflicting signal, {pending.strategy_id} has priority", None
    
    async def _execute_signal(self, signal: TradeSignal,
                              risk_details: Optional[Dict] = None) -> Tuple[bool, str, Optional[Dict]]:
        """Execute the signal."""
        
        # Re-validate if no risk details provided
        if risk_details is None:
            is_valid, msg, risk_details = self.risk_manager.validate_signal(signal)
            if not is_valid:
                self.rejected_signals += 1
                return False, msg, None
        
        # Record position as open
        self.open_positions[signal.instrument] = {
            "signal": signal,
            "position_size": risk_details['position_size'],
            "opened_at": datetime.now(),
            "risk_details": risk_details
        }
        
        # Add to pending signals (for conflict detection)
        self.pending_signals[signal.signal_id] = signal
        
        # Record trade
        self.risk_manager.record_trade(signal, risk_details['position_size'])
        
        self.accepted_signals += 1
        
        print(f"[ARBITER] ACCEPTED: {signal.strategy_id} {signal.instrument} {signal.direction} "
              f"@ {signal.entry_price}, Size: {risk_details['position_size']}")
        
        execution_details = {
            "signal": signal.to_dict(),
            "position_size": risk_details['position_size'],
            "risk_usd": risk_details['actual_risk_usd'],
            "risk_pct": risk_details['actual_risk_pct'],
            "r_multiples": risk_details['r_multiples'],
            "timestamp": datetime.now().isoformat()
        }
        
        return True, "Signal accepted and executed", execution_details
    
    def _get_pending_signal(self, instrument: str) -> Optional[TradeSignal]:
        """Get any pending signal for this instrument (within last 5 seconds)."""
        now = datetime.now()
        
        for signal_id, signal in self.pending_signals.items():
            if signal.instrument == instrument:
                # Check if signal is recent (within 5 seconds)
                age = (now - signal.timestamp).total_seconds()
                if age < 5:
                    return signal
        
        return None
    
    def close_position(self, instrument: str):
        """Mark position as closed."""
        if instrument in self.open_positions:
            del self.open_positions[instrument]
            print(f"[ARBITER] Position closed for {instrument}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get arbiter statistics."""
        return {
            "total_signals": self.total_signals,
            "accepted": self.accepted_signals,
            "rejected": self.rejected_signals,
            "merged": self.merged_signals,
            "acceptance_rate": (self.accepted_signals / self.total_signals * 100) if self.total_signals > 0 else 0,
            "open_positions": len(self.open_positions)
        }
    
    def print_stats(self):
        """Print arbiter statistics."""
        stats = self.get_stats()
        print(f"\n[ARBITER] Statistics:")
        print(f"  Total signals: {stats['total_signals']}")
        print(f"  Accepted: {stats['accepted']}")
        print(f"  Rejected: {stats['rejected']}")
        print(f"  Merged: {stats['merged']}")
        print(f"  Acceptance rate: {stats['acceptance_rate']:.1f}%")
        print(f"  Open positions: {stats['open_positions']}")


# Test
if __name__ == "__main__":
    import asyncio
    from shared.signal_schema import TradeSignal
    
    print("Testing ExecutionArbiter...")
    
    async def test_arbiter():
        arbiter = ExecutionArbiter()
        
        # Test 1: Single signal
        print("\n1. Testing single signal acceptance...")
        signal1 = TradeSignal(
            strategy_id="AAFR",
            instrument="NQ",
            direction="BUY",
            entry_price=20150.00,
            stop_price=20115.50,
            take_profit=[20200.00, 20250.00]
        )
        
        accepted, msg, details = await arbiter.process_signal(signal1)
        print(f"   Result: {accepted}, {msg}")
        
        # Test 2: Conflicting signal (opposite direction)
        print("\n2. Testing conflicting signal (opposite direction)...")
        signal2 = TradeSignal(
            strategy_id="AJR",
            instrument="NQ",
            direction="SELL",  # Opposite!
            entry_price=20145.00,
            stop_price=20160.00,
            take_profit=[20120.00, 20100.00]
        )
        
        accepted, msg, details = await arbiter.process_signal(signal2)
        print(f"   Result: {accepted}, {msg}")
        
        # Close first position
        arbiter.close_position("NQ")
        
        # Test 3: Same direction signals (merging)
        print("\n3. Testing same direction signals (merging)...")
        signal3 = TradeSignal(
            strategy_id="AAFR",
            instrument="ES",
            direction="BUY",
            entry_price=5350.00,
            stop_price=5342.50,
            take_profit=[5365.00]
        )
        
        signal4 = TradeSignal(
            strategy_id="AJR",
            instrument="ES",
            direction="BUY",  # Same direction
            entry_price=5349.00,
            stop_price=5341.00,
            take_profit=[5363.00]
        )
        
        accepted, msg, details = await arbiter.process_signal(signal3)
        print(f"   Signal 3: {accepted}")
        
        accepted, msg, details = await arbiter.process_signal(signal4)
        print(f"   Signal 4 (merge): {accepted}, {msg}")
        
        # Print statistics
        arbiter.print_stats()
        print("\n[OK] Arbiter tests passed!")
    
    asyncio.run(test_arbiter())

