"""
Position State Tracker for GUI Bot.
Tracks open positions, fills, and remaining sizes per symbol.
"""

from typing import Dict, Optional, List
from datetime import datetime


class Position:
    """Represents an open position for a symbol."""
    
    def __init__(self, symbol: str, side: str, size: int, entry: float):
        """
        Initialize position.
        
        Args:
            symbol: Trading symbol
            side: 'LONG' or 'SHORT'
            size: Initial position size
            entry: Entry price
        """
        self.symbol = symbol
        self.side = side
        self.initial_size = size
        self.current_size = size
        self.entry = entry
        self.stop_price = None
        self.stop_qty = None
        self.filled_tps = []
        self.tp_prices = []
        self.opened_at = datetime.now()
        
    def mark_tp_filled(self, tp_level: int, qty: int) -> None:
        """
        Mark a TP level as filled.
        
        Args:
            tp_level: TP level number (1, 2, 3)
            qty: Quantity filled
        """
        if tp_level not in self.filled_tps:
            self.filled_tps.append(tp_level)
            self.current_size -= qty
            if self.current_size < 0:
                self.current_size = 0
    
    def update_stop(self, price: float, qty: int) -> None:
        """
        Update stop loss details.
        
        Args:
            price: New stop price
            qty: New stop quantity
        """
        self.stop_price = price
        self.stop_qty = qty
    
    def set_tps(self, tp_prices: List[float]) -> None:
        """
        Set TP price levels.
        
        Args:
            tp_prices: List of TP prices
        """
        self.tp_prices = tp_prices
    
    def get_remaining_size(self) -> int:
        """Get current remaining position size."""
        return self.current_size
    
    def is_closed(self) -> bool:
        """Check if position is fully closed."""
        return self.current_size <= 0
    
    def __repr__(self) -> str:
        return (f"Position({self.symbol}, {self.side}, "
                f"Size: {self.current_size}/{self.initial_size}, "
                f"Entry: {self.entry}, TPs filled: {len(self.filled_tps)})")


class PositionTracker:
    """
    Tracks position state for all symbols.
    Maintains position details, fills, and stop updates.
    """
    
    def __init__(self):
        """Initialize position tracker."""
        self.positions: Dict[str, Position] = {}
    
    def open_position(self, symbol: str, side: str, size: int, entry: float) -> None:
        """
        Record a new position opening.
        
        Args:
            symbol: Trading symbol
            side: 'LONG' or 'SHORT'
            size: Position size
            entry: Entry price
        """
        position = Position(symbol, side, size, entry)
        self.positions[symbol] = position
        print(f"[TRACKER] Opened position: {position}")
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """
        Get position for symbol.
        
        Args:
            symbol: Trading symbol
        
        Returns:
            Position object or None
        """
        return self.positions.get(symbol)
    
    def mark_tp_filled(self, symbol: str, tp_level: int, qty: int) -> bool:
        """
        Mark a TP level as filled.
        
        Args:
            symbol: Trading symbol
            tp_level: TP level (1, 2, 3)
            qty: Quantity filled
        
        Returns:
            True if successful, False if position not found
        """
        position = self.positions.get(symbol)
        if not position:
            print(f"[TRACKER] Warning: No position found for {symbol}")
            return False
        
        position.mark_tp_filled(tp_level, qty)
        print(f"[TRACKER] TP{tp_level} filled for {symbol}. Remaining: {position.current_size}")
        return True
    
    def update_stop(self, symbol: str, price: float, qty: int) -> bool:
        """
        Update stop loss for position.
        
        Args:
            symbol: Trading symbol
            price: New stop price
            qty: New stop quantity
        
        Returns:
            True if successful, False if position not found
        """
        position = self.positions.get(symbol)
        if not position:
            print(f"[TRACKER] Warning: No position found for {symbol}")
            return False
        
        position.update_stop(price, qty)
        print(f"[TRACKER] Stop updated for {symbol}: {qty} @ {price}")
        return True
    
    def get_remaining_size(self, symbol: str) -> int:
        """
        Get remaining position size.
        
        Args:
            symbol: Trading symbol
        
        Returns:
            Remaining size, or 0 if no position
        """
        position = self.positions.get(symbol)
        if not position:
            return 0
        return position.get_remaining_size()
    
    def set_tps(self, symbol: str, tp_prices: List[float]) -> bool:
        """
        Set TP price levels for position.
        
        Args:
            symbol: Trading symbol
            tp_prices: List of TP prices
        
        Returns:
            True if successful, False if position not found
        """
        position = self.positions.get(symbol)
        if not position:
            print(f"[TRACKER] Warning: No position found for {symbol}")
            return False
        
        position.set_tps(tp_prices)
        return True
    
    def close_position(self, symbol: str) -> bool:
        """
        Close and remove position.
        
        Args:
            symbol: Trading symbol
        
        Returns:
            True if position was closed, False if not found
        """
        if symbol in self.positions:
            position = self.positions[symbol]
            print(f"[TRACKER] Closing position: {position}")
            del self.positions[symbol]
            return True
        else:
            print(f"[TRACKER] No position to close for {symbol}")
            return False
    
    def has_position(self, symbol: str) -> bool:
        """
        Check if symbol has an open position.
        
        Args:
            symbol: Trading symbol
        
        Returns:
            True if position exists and not closed
        """
        position = self.positions.get(symbol)
        if not position:
            return False
        return not position.is_closed()
    
    def get_all_positions(self) -> Dict[str, Position]:
        """Get all tracked positions."""
        return self.positions.copy()
    
    def get_position_summary(self, symbol: str) -> Optional[Dict]:
        """
        Get summary of position state.
        
        Args:
            symbol: Trading symbol
        
        Returns:
            Dictionary with position details or None
        """
        position = self.positions.get(symbol)
        if not position:
            return None
        
        return {
            'symbol': position.symbol,
            'side': position.side,
            'initial_size': position.initial_size,
            'current_size': position.current_size,
            'entry': position.entry,
            'stop_price': position.stop_price,
            'stop_qty': position.stop_qty,
            'filled_tps': position.filled_tps,
            'tp_count': len(position.filled_tps),
            'opened_at': position.opened_at.isoformat()
        }


# Test functionality
if __name__ == "__main__":
    print("Testing PositionTracker...")
    
    tracker = PositionTracker()
    
    # Open position
    tracker.open_position("NQ", "LONG", 3, 20150.00)
    
    # Check position
    assert tracker.has_position("NQ")
    assert tracker.get_remaining_size("NQ") == 3
    
    # Mark TP1 filled
    tracker.mark_tp_filled("NQ", 1, 1)
    assert tracker.get_remaining_size("NQ") == 2
    
    # Update stop
    tracker.update_stop("NQ", 20151.00, 2)
    
    # Mark TP2 filled
    tracker.mark_tp_filled("NQ", 2, 1)
    assert tracker.get_remaining_size("NQ") == 1
    
    # Get summary
    summary = tracker.get_position_summary("NQ")
    print(f"\nPosition Summary: {summary}")
    
    # Close position
    tracker.close_position("NQ")
    assert not tracker.has_position("NQ")
    
    print("\n[OK] All tests passed!")

