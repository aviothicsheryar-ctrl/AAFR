"""
Unified signal schema for AAFR and AJR strategies.
Standardized JSON format for trade signals.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json


class TradeSignal:
    """
    Standardized trade signal for both AAFR and AJR strategies.
    """
    
    def __init__(self, strategy_id: str, instrument: str, direction: str,
                 entry_price: float, stop_price: float, take_profit: List[float],
                 max_loss_usd: float = 750.0, notes: str = ""):
        """
        Initialize trade signal.
        
        Args:
            strategy_id: "AAFR" or "AJR"
            instrument: "NQ", "ES", "GC", or "CL"
            direction: "BUY" or "SELL"
            entry_price: Entry price
            stop_price: Stop loss price
            take_profit: List of TP prices (1-3 levels)
            max_loss_usd: Maximum loss in USD
            notes: Optional notes
        """
        self.strategy_id = strategy_id
        self.signal_id = self._generate_signal_id(instrument)
        self.instrument = instrument
        self.direction = direction.upper()
        self.entry_price = entry_price
        self.stop_price = stop_price
        self.take_profit = take_profit
        self.max_loss_usd = max_loss_usd
        self.notes = notes
        self.timestamp = datetime.now()
        
        # Validate
        self._validate()
    
    def _generate_signal_id(self, instrument: str) -> str:
        """Generate unique signal ID."""
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        counter = datetime.now().microsecond % 1000
        return f"{timestamp}Z-{instrument}-{counter:03d}"
    
    def _validate(self) -> None:
        """Validate signal parameters."""
        # Validate strategy
        if self.strategy_id not in ["AAFR", "AJR"]:
            raise ValueError(f"Invalid strategy_id: {self.strategy_id}")
        
        # Validate instrument
        if self.instrument not in ["NQ", "ES", "GC", "CL"]:
            raise ValueError(f"Invalid instrument: {self.instrument}. Only NQ, ES, GC, CL allowed.")
        
        # Validate direction
        if self.direction not in ["BUY", "SELL"]:
            raise ValueError(f"Invalid direction: {self.direction}")
        
        # Validate prices
        if self.entry_price <= 0:
            raise ValueError("Entry price must be positive")
        if self.stop_price <= 0:
            raise ValueError("Stop price must be positive")
        
        # Validate stop is on correct side
        if self.direction == "BUY" and self.stop_price >= self.entry_price:
            raise ValueError("BUY stop must be below entry")
        if self.direction == "SELL" and self.stop_price <= self.entry_price:
            raise ValueError("SELL stop must be above entry")
        
        # Validate TPs
        if not self.take_profit or len(self.take_profit) == 0:
            raise ValueError("At least one take profit level required")
        
        for tp in self.take_profit:
            if self.direction == "BUY" and tp <= self.entry_price:
                raise ValueError("BUY take profits must be above entry")
            if self.direction == "SELL" and tp >= self.entry_price:
                raise ValueError("SELL take profits must be below entry")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert signal to dictionary."""
        return {
            "strategy_id": self.strategy_id,
            "signal_id": self.signal_id,
            "instrument": self.instrument,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "stop_price": self.stop_price,
            "take_profit": self.take_profit,
            "max_loss_usd": self.max_loss_usd,
            "notes": self.notes,
            "timestamp": self.timestamp.isoformat()
        }
    
    def to_json(self) -> str:
        """Convert signal to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradeSignal':
        """Create signal from dictionary."""
        return cls(
            strategy_id=data['strategy_id'],
            instrument=data['instrument'],
            direction=data['direction'],
            entry_price=data['entry_price'],
            stop_price=data['stop_price'],
            take_profit=data['take_profit'],
            max_loss_usd=data.get('max_loss_usd', 750.0),
            notes=data.get('notes', '')
        )
    
    def calculate_stop_distance(self) -> float:
        """Calculate stop distance in price points."""
        return abs(self.entry_price - self.stop_price)
    
    def calculate_risk_reward(self) -> List[float]:
        """Calculate R multiples for each TP level."""
        stop_distance = self.calculate_stop_distance()
        r_multiples = []
        
        for tp in self.take_profit:
            profit_distance = abs(tp - self.entry_price)
            r = profit_distance / stop_distance if stop_distance > 0 else 0
            r_multiples.append(round(r, 2))
        
        return r_multiples
    
    def __repr__(self) -> str:
        r_multiples = self.calculate_risk_reward()
        return (f"Signal({self.strategy_id}, {self.instrument}, {self.direction}, "
                f"Entry: {self.entry_price}, Stop: {self.stop_price}, "
                f"TPs: {self.take_profit}, R: {r_multiples})")


# Test
if __name__ == "__main__":
    print("Testing TradeSignal...")
    
    # Test AAFR signal
    aafr_signal = TradeSignal(
        strategy_id="AAFR",
        instrument="NQ",
        direction="BUY",
        entry_price=20150.00,
        stop_price=20115.50,
        take_profit=[20200.00, 20250.00, 20300.00],
        notes="ICC continuation pattern"
    )
    
    print("\nAAFR Signal:")
    print(aafr_signal)
    print(aafr_signal.to_json())
    
    # Test AJR signal
    ajr_signal = TradeSignal(
        strategy_id="AJR",
        instrument="ES",
        direction="SELL",
        entry_price=5348.50,
        stop_price=5356.75,
        take_profit=[5328.50, 5318.25],
        notes="Gap inversion pattern detected"
    )
    
    print("\nAJR Signal:")
    print(ajr_signal)
    print(ajr_signal.to_json())
    
    # Test validation
    try:
        invalid = TradeSignal(
            strategy_id="INVALID",
            instrument="BTC",  # Invalid
            direction="BUY",
            entry_price=50000,
            stop_price=49000,
            take_profit=[51000]
        )
    except ValueError as e:
        print(f"\n[OK] Validation caught error: {e}")
    
    print("\n[OK] All tests passed!")

