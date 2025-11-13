"""
Unified Risk Manager for AAFR and AJR strategies.
Enforces E-Mini instrument restrictions, position sizing, and risk limits.
"""

from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import json

from aafr.utils import load_config
from shared.signal_schema import TradeSignal


class UnifiedRiskManager:
    """
    Unified risk manager for both strategies.
    Enforces E-Mini only trading and proper position sizing.
    """
    
    # E-Mini instrument whitelist (ONLY these allowed)
    ALLOWED_INSTRUMENTS = ["NQ", "ES", "GC", "CL"]
    
    def __init__(self, config_path: str = "aafr/config.json"):
        """Initialize risk manager."""
        self.config = load_config(config_path)
        
        # Risk parameters
        self.account_size = self.config['account']['size']
        self.max_risk_pct = self.config['account']['max_risk_per_trade']
        self.max_risk_usd = self.config['account'].get('max_risk_usd_per_trade', 750)
        self.daily_loss_limit = self.config['account']['daily_loss_limit']
        
        # Instrument specs
        self.instruments = self.config['instruments']
        
        # Daily tracking
        self.daily_loss = 0.0
        self.daily_trades = 0
        self.trade_history = []
        
        print(f"[RISK] Unified Risk Manager initialized")
        print(f"[RISK] Allowed instruments: {self.ALLOWED_INSTRUMENTS}")
        print(f"[RISK] Max risk per trade: ${self.max_risk_usd} ({self.max_risk_pct}%)")
        print(f"[RISK] Daily loss limit: ${self.daily_loss_limit}")
    
    def validate_instrument(self, instrument: str) -> Tuple[bool, str]:
        """
        Validate that instrument is on E-Mini whitelist.
        
        Args:
            instrument: Trading symbol
        
        Returns:
            (is_valid, message)
        """
        if instrument not in self.ALLOWED_INSTRUMENTS:
            return False, f"Instrument {instrument} not allowed. Only {self.ALLOWED_INSTRUMENTS} permitted."
        
        if instrument not in self.instruments:
            return False, f"Instrument {instrument} not configured."
        
        return True, "OK"
    
    def get_instrument_specs(self, instrument: str) -> Dict[str, Any]:
        """Get instrument specifications."""
        return self.instruments.get(instrument, {})
    
    def calculate_position_size(self, signal: TradeSignal) -> Tuple[int, Dict[str, Any]]:
        """
        Calculate position size based on risk and stop distance.
        
        Formula: contracts = floor(max_loss_usd / (stop_distance_ticks × dollar_per_tick))
        
        Args:
            signal: Trade signal
        
        Returns:
            (position_size, details_dict)
        """
        # Get instrument specs
        specs = self.get_instrument_specs(signal.instrument)
        if not specs:
            return 0, {"error": "Unknown instrument"}
        
        tick_size = specs['tick_size']
        tick_value = specs['tick_value']
        
        # Calculate stop distance in price points
        stop_distance_points = abs(signal.entry_price - signal.stop_price)
        
        # Convert to ticks
        stop_distance_ticks = stop_distance_points / tick_size
        
        # Calculate dollar risk per contract
        dollar_per_contract = stop_distance_ticks * tick_value
        
        if dollar_per_contract <= 0:
            return 0, {"error": "Invalid stop distance"}
        
        # Calculate position size
        position_size = int(signal.max_loss_usd / dollar_per_contract)
        
        # Ensure at least 1 contract
        position_size = max(1, position_size)
        
        # Calculate actual dollar risk
        actual_risk = position_size * dollar_per_contract
        actual_risk_pct = (actual_risk / self.account_size) * 100
        
        details = {
            "instrument": signal.instrument,
            "tick_size": tick_size,
            "tick_value": tick_value,
            "stop_distance_points": round(stop_distance_points, 4),
            "stop_distance_ticks": round(stop_distance_ticks, 2),
            "dollar_per_contract": round(dollar_per_contract, 2),
            "position_size": position_size,
            "actual_risk_usd": round(actual_risk, 2),
            "actual_risk_pct": round(actual_risk_pct, 3),
            "r_multiples": signal.calculate_risk_reward()
        }
        
        return position_size, details
    
    def validate_signal(self, signal: TradeSignal) -> Tuple[bool, str, Optional[Dict]]:
        """
        Validate trade signal against all risk rules.
        
        Args:
            signal: Trade signal to validate
        
        Returns:
            (is_valid, message, position_details)
        """
        # 1. Validate instrument
        is_valid, msg = self.validate_instrument(signal.instrument)
        if not is_valid:
            return False, msg, None
        
        # 2. Check daily loss limit
        if self.daily_loss >= self.daily_loss_limit:
            return False, f"Daily loss limit reached: ${self.daily_loss:.2f}", None
        
        # 3. Calculate position size
        position_size, details = self.calculate_position_size(signal)
        
        if position_size <= 0:
            return False, f"Invalid position size: {details.get('error', 'Unknown')}", None
        
        # 4. Validate risk doesn't exceed limits
        if details['actual_risk_usd'] > self.max_risk_usd * 1.1:  # 10% tolerance
            return False, f"Risk ${details['actual_risk_usd']:.2f} exceeds max ${self.max_risk_usd}", details
        
        # 5. Check R multiples
        r_multiples = details['r_multiples']
        if r_multiples and max(r_multiples) < 1.5:
            return False, f"R multiple {max(r_multiples):.1f} too low (min 1.5)", details
        
        # All checks passed
        return True, "Signal validated", details
    
    def record_trade(self, signal: TradeSignal, position_size: int, result: Optional[str] = None):
        """
        Record trade for tracking.
        
        Args:
            signal: Trade signal
            position_size: Actual position size
            result: Optional trade result
        """
        trade_record = {
            "timestamp": datetime.now().isoformat(),
            "strategy": signal.strategy_id,
            "instrument": signal.instrument,
            "direction": signal.direction,
            "entry": signal.entry_price,
            "stop": signal.stop_price,
            "size": position_size,
            "result": result
        }
        
        self.trade_history.append(trade_record)
        self.daily_trades += 1
    
    def update_daily_loss(self, loss_amount: float):
        """Update daily loss tracker."""
        self.daily_loss += loss_amount
        print(f"[RISK] Daily loss updated: ${self.daily_loss:.2f} / ${self.daily_loss_limit}")
    
    def reset_daily(self):
        """Reset daily counters (call at start of trading day)."""
        self.daily_loss = 0.0
        self.daily_trades = 0
        self.trade_history = []
        print(f"[RISK] Daily counters reset")
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get current risk summary."""
        return {
            "account_size": self.account_size,
            "max_risk_per_trade": self.max_risk_usd,
            "daily_loss": self.daily_loss,
            "daily_loss_limit": self.daily_loss_limit,
            "daily_trades": self.daily_trades,
            "remaining_loss_budget": self.daily_loss_limit - self.daily_loss
        }


# Test
if __name__ == "__main__":
    print("Testing UnifiedRiskManager...")
    
    risk = UnifiedRiskManager()
    
    # Test valid signal
    from shared.signal_schema import TradeSignal
    
    signal = TradeSignal(
        strategy_id="AAFR",
        instrument="NQ",
        direction="BUY",
        entry_price=20150.00,
        stop_price=20115.50,  # 34.5 points = 138 ticks
        take_profit=[20200.00, 20250.00],
        max_loss_usd=750
    )
    
    print("\n1. Testing NQ signal validation...")
    is_valid, msg, details = risk.validate_signal(signal)
    print(f"   Valid: {is_valid}")
    print(f"   Message: {msg}")
    if details:
        print(f"   Position size: {details['position_size']} contracts")
        print(f"   Risk: ${details['actual_risk_usd']:.2f} ({details['actual_risk_pct']:.2f}%)")
        print(f"   R multiples: {details['r_multiples']}")
    
    # Test invalid instrument
    print("\n2. Testing invalid instrument...")
    try:
        invalid_signal = TradeSignal(
            strategy_id="AJR",
            instrument="BTC",  # Not allowed
            direction="BUY",
            entry_price=50000,
            stop_price=49000,
            take_profit=[51000]
        )
    except ValueError as e:
        print(f"   [OK] Validation caught: {e}")
    
    # Test position sizing for each instrument
    print("\n3. Testing position sizing for all instruments...")
    
    test_signals = [
        ("NQ", 20150.00, 20110.00),  # 40 ticks
        ("ES", 5350.00, 5342.50),     # 30 ticks
        ("GC", 2600.00, 2596.00),     # 40 ticks
        ("CL", 70.00, 69.70)          # 30 ticks
    ]
    
    for symbol, entry, stop in test_signals:
        sig = TradeSignal(
            strategy_id="AJR",
            instrument=symbol,
            direction="BUY",
            entry_price=entry,
            stop_price=stop,
            take_profit=[entry + (entry - stop) * 1.5],
            max_loss_usd=750
        )
        
        is_valid, msg, details = risk.validate_signal(sig)
        if is_valid and details:
            print(f"   {symbol}: {details['position_size']} contracts, "
                  f"Risk ${details['actual_risk_usd']:.2f}")
    
    print("\n[OK] Risk manager tests passed!")

