"""
Risk Management Engine for TPT 150K account rules.
Enforces position sizing, daily limits, and restricted event detection.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, date
import json

from aafr.utils import load_config, calculate_atr


class RiskEngine:
    """
    Risk management system enforcing TPT 150K account rules.
    Manages position sizing, daily limits, and event restrictions.
    """
    
    def __init__(self, config_path: str = "config.json"):
        """
        Initialize Risk Engine.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = load_config(config_path)
        self.account_config = self.config['account']
        self.icc_config = self.config['icc']
        
        # Account parameters
        self.account_size = self.account_config['size']  # $150,000
        self.max_risk_per_trade = self.account_config['max_risk_per_trade']  # 0.5%
        self.daily_loss_limit = self.account_config['daily_loss_limit']  # $1,500
        
        # ICC parameters
        self.min_r_multiple = self.icc_config['min_r_multiple']  # 2.0
        self.atr_multiplier = self.icc_config['atr_multiplier']  # 1.5
        
        # Daily tracking
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.max_daily_trades = 20  # Optional limit
        
        # Restricted events (hardcoded important dates - TODO: dynamic calendar)
        self.restricted_events = self.config.get('restricted_events', [])
        self.event_dates = self._load_event_dates()
        
        # Instrument specifications cache
        self.instrument_specs = self.config.get('instruments', {})
    
    def _load_event_dates(self) -> List[str]:
        """
        Load restricted event dates.
        TODO: Implement dynamic calendar loading from external source.
        
        Returns:
            List of event date strings
        """
        # Hardcoded examples - in production, load from calendar API
        return [
            "2025-01-31",  # FOMC
            "2025-02-07",  # NFP
            "2025-02-13",  # CPI
            "2025-03-07",  # NFP
            "2025-03-12",  # FOMC
        ]
    
    def is_trading_restricted(self, check_date: Optional[str] = None) -> bool:
        """
        Check if trading is restricted due to FOMC/NFP/CPI events.
        
        Args:
            check_date: Date string (YYYY-MM-DD), defaults to today
        
        Returns:
            True if trading should be disabled
        """
        if check_date is None:
            check_date = date.today().isoformat()
        
        return check_date in self.event_dates
    
    def calculate_position_size(self, entry_price: float, stop_price: float, 
                               symbol: str, risk_percent: Optional[float] = None) -> Optional[int]:
        """
        Calculate position size based on stop distance and max risk.
        
        Args:
            entry_price: Entry price for the trade
            stop_price: Stop loss price
            symbol: Trading instrument symbol
            risk_percent: Optional override for risk percentage
        
        Returns:
            Number of contracts to trade, or None if invalid
        """
        # Get instrument specifications
        specs = self.instrument_specs.get(symbol)
        if not specs:
            print(f"[ERROR] Unknown instrument: {symbol}")
            return None
        
        tick_size = specs['tick_size']
        tick_value = specs['tick_value']
        
        # Calculate dollar risk per trade
        if risk_percent is None:
            risk_percent = self.max_risk_per_trade
        
        dollar_risk = self.account_size * (risk_percent / 100.0)
        
        # Calculate stop distance in ticks
        stop_distance = abs(entry_price - stop_price)
        ticks_risk = stop_distance / tick_size
        
        if ticks_risk == 0:
            print("[ERROR] Invalid stop distance (zero)")
            return None
        
        # Position size = dollar risk / (ticks * tick value)
        position_size = int(dollar_risk / (ticks_risk * tick_value))
        
        # Minimum 1 contract
        return max(1, position_size)
    
    def calculate_atr_stop(self, entry_price: float, direction: str, 
                          atr: float, candles: List[Dict]) -> float:
        """
        Calculate stop loss using ATR-based method.
        
        Args:
            entry_price: Entry price
            direction: 'LONG' or 'SHORT'
            atr: Current ATR value
            candles: Historical candles for context
        
        Returns:
            Stop loss price
        """
        # ATR-based stop with buffer
        atr_buffer = atr * self.atr_multiplier
        
        if direction == 'LONG':
            stop = entry_price - atr_buffer
        else:
            stop = entry_price + atr_buffer
        
        # TODO: Add swing low/high validation
        # For now, simple ATR-based stop
        return stop
    
    def calculate_take_profit(self, entry_price: float, stop_price: float, 
                             direction: str, r_multiple: float) -> float:
        """
        Calculate take profit based on R multiple.
        
        Args:
            entry_price: Entry price
            stop_price: Stop loss price
            direction: 'LONG' or 'SHORT'
            r_multiple: Desired R multiple (e.g., 2.0 or 3.0)
        
        Returns:
            Take profit price
        """
        risk_distance = abs(entry_price - stop_price)
        reward_distance = risk_distance * r_multiple
        
        if direction == 'LONG':
            return entry_price + reward_distance
        else:
            return entry_price - reward_distance
    
    def validate_trade_setup(self, entry: float, stop: float, direction: str,
                            symbol: str, candles: List[Dict]) -> Tuple[bool, str, Dict]:
        """
        Validate trade setup against all risk rules.
        
        Args:
            entry: Entry price
            stop: Stop loss price
            direction: 'LONG' or 'SHORT'
            symbol: Trading instrument
            candles: Historical candles for ATR calculation
        
        Returns:
            Tuple of (is_valid, message, trade_details)
        """
        trade_details = {}
        
        # 1. Check restricted events
        if self.is_trading_restricted():
            return (False, "Trading restricted due to FOMC/NFP/CPI event", {})
        
        # 2. Check daily loss limit
        if self.daily_pnl <= -self.daily_loss_limit:
            return (False, f"Daily loss limit reached: ${self.daily_pnl:.2f}", {})
        
        # 3. Check daily trade limit
        if self.daily_trades >= self.max_daily_trades:
            return (False, f"Max daily trades reached: {self.daily_trades}", {})
        
        # 4. Calculate R multiple
        risk_distance = abs(entry - stop)
        if risk_distance == 0:
            return (False, "Invalid stop loss (zero distance)", {})
        
        # For now, use 3.0 R as default - actual logic in ICC module
        r_multiple = 3.0
        
        # 5. Validate minimum R multiple
        if r_multiple < self.min_r_multiple:
            return (False, f"R multiple too low: {r_multiple:.1f} < {self.min_r_multiple}", {})
        
        # 6. Calculate position size
        position_size = self.calculate_position_size(entry, stop, symbol)
        if position_size is None:
            return (False, "Could not calculate position size", {})
        
        # 7. Calculate dollar risk
        specs = self.instrument_specs[symbol]
        stop_distance_ticks = abs(entry - stop) / specs['tick_size']
        dollar_risk = stop_distance_ticks * specs['tick_value'] * position_size
        
        # Handle zero account size edge case
        if self.account_size == 0:
            return (False, "Account size is zero", {})
        
        risk_percent = (dollar_risk / self.account_size) * 100.0
        
        # 8. Validate max risk per trade
        if risk_percent > self.max_risk_per_trade:
            return (False, f"Risk too high: {risk_percent:.2f}% > {self.max_risk_per_trade}%", {})
        
        # 9. Calculate take profit
        take_profit = self.calculate_take_profit(entry, stop, direction, r_multiple)
        
        # All validations passed
        trade_details = {
            'entry': entry,
            'stop_loss': stop,
            'take_profit': take_profit,
            'r_multiple': r_multiple,
            'position_size': position_size,
            'dollar_risk': dollar_risk,
            'risk_percent': risk_percent,
            'direction': direction,
            'symbol': symbol
        }
        
        return (True, "Trade setup valid", trade_details)
    
    def update_daily_pnl(self, pnl: float) -> None:
        """
        Update daily P&L tracking.
        
        Args:
            pnl: Profit/loss amount
        """
        self.daily_pnl += pnl
        print(f"Daily P&L: ${self.daily_pnl:.2f}")
    
    def increment_daily_trades(self) -> None:
        """Increment daily trade counter."""
        self.daily_trades += 1
    
    def reset_daily_tracking(self) -> None:
        """Reset daily tracking counters."""
        self.daily_pnl = 0.0
        self.daily_trades = 0
        print("Daily tracking reset")
    
    def get_daily_summary(self) -> Dict:
        """
        Get current daily summary statistics.
        
        Returns:
            Dictionary with daily stats
        """
        return {
            'daily_pnl': self.daily_pnl,
            'daily_trades': self.daily_trades,
            'remaining_risk': self.account_size * (self.max_risk_per_trade / 100.0),
            'under_daily_limit': self.daily_pnl > -self.daily_loss_limit
        }


# Example usage
if __name__ == "__main__":
    risk_engine = RiskEngine()
    
    # Test position sizing
    entry = 17893.50
    stop = 17864.25
    size = risk_engine.calculate_position_size(entry, stop, "MNQ")
    print(f"Position size: {size} contracts")
    
    # Test take profit calculation
    tp = risk_engine.calculate_take_profit(entry, stop, "LONG", 3.0)
    print(f"Take profit: {tp:.2f}")
    
    # Test trade validation
    mock_candles = [
        {'open': 17800, 'high': 17900, 'low': 17780, 'close': 17850, 'volume': 5000}
    ] * 20
    
    is_valid, msg, details = risk_engine.validate_trade_setup(
        entry, stop, "LONG", "MNQ", mock_candles
    )
    
    print(f"\nTrade valid: {is_valid}")
    print(f"Message: {msg}")
    if details:
        print(f"Details: {details}")
    
    # Test daily summary
    summary = risk_engine.get_daily_summary()
    print(f"\nDaily Summary: {summary}")

