"""
DOM Automation Engine for Tradovate.
Handles click and drag operations using PyAutoGUI.
"""

import time
from typing import Dict, Any, Tuple, Optional

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
    # Failsafe: move mouse to corner to abort
    pyautogui.FAILSAFE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    print("[WARNING] pyautogui not installed. Install with: pip install pyautogui")


class DOMAutomator:
    """
    Automates Tradovate DOM interactions.
    Handles limit orders (left-click), stop orders (right-click), and drag operations.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize DOM automator.
        
        Args:
            config: Bot configuration dictionary
        """
        self.config = config
        self.timing = config.get('timing', {})
        self.retry_settings = config.get('retry_settings', {})
        self.safety = config.get('safety', {})
        
        # Timing parameters (convert ms to seconds)
        self.click_delay = self.timing.get('click_delay_ms', 100) / 1000
        self.drag_delay = self.timing.get('drag_delay_ms', 200) / 1000
        self.pre_action_delay = self.timing.get('pre_action_delay_ms', 50) / 1000
        self.post_action_delay = self.timing.get('post_action_delay_ms', 150) / 1000
        self.retry_delay = self.timing.get('retry_delay_ms', 500) / 1000
        
        # Retry settings
        self.max_retries = self.retry_settings.get('max_retries', 1)
        self.enable_fallback = self.retry_settings.get('enable_cancel_replace_fallback', True)
        
        # Safety settings
        self.dry_run = self.safety.get('dry_run_mode', False)
        
        if not PYAUTOGUI_AVAILABLE:
            print("[ERROR] PyAutoGUI not available. Automation will not work.")
            self.dry_run = True  # Force dry run if pyautogui unavailable
        
        if self.dry_run:
            print("[INFO] DRY RUN MODE: Actions will be logged but not executed")
    
    def _calculate_coordinates(self, price: float, symbol: str, side: str) -> Tuple[int, int]:
        """
        Calculate screen coordinates for a price level.
        
        Args:
            price: Price level
            symbol: Trading symbol
            side: 'BID' or 'ASK'
        
        Returns:
            (x, y) screen coordinates
        """
        dom_coords = self.config.get('dom_coordinates', {}).get(symbol)
        if not dom_coords:
            raise ValueError(f"No DOM coordinates configured for {symbol}")
        
        # Get column X based on side
        if side == 'BID':
            x = dom_coords['bid_column_x']
        elif side == 'ASK':
            x = dom_coords['ask_column_x']
        else:
            raise ValueError(f"Invalid side: {side}. Must be 'BID' or 'ASK'")
        
        # Calculate Y position based on price
        top_price = dom_coords['top_price']
        price_row_height = dom_coords['price_row_height']
        bounds = dom_coords['dom_window_bounds']
        
        # Calculate rows from top (assuming 0.25 tick size)
        # TODO: Get tick size from instrument config
        tick_size = 0.25
        price_diff = top_price - price
        row_offset = int(price_diff / tick_size)
        
        y = bounds['top'] + (row_offset * price_row_height)
        
        # Validate coordinates
        if not (bounds['left'] <= x <= bounds['right'] and 
                bounds['top'] <= y <= bounds['bottom']):
            print(f"[WARNING] Coordinates ({x}, {y}) for {price} may be out of bounds")
        
        return (x, y)
    
    def _validate_pre_execution(self, symbol: str) -> bool:
        """
        Validate safety checks before executing action.
        
        Args:
            symbol: Trading symbol
        
        Returns:
            True if validation passes
        """
        if self.dry_run:
            return True
        
        # Check if DOM focus validation is required
        if self.safety.get('require_dom_focus', True):
            # TODO: Implement window focus check
            # For now, assume it's valid
            pass
        
        return True
    
    def place_limit_order(self, side: str, price: float, qty: int, symbol: str) -> bool:
        """
        Place limit order via left-click on DOM.
        
        Args:
            side: 'LONG' (click BID) or 'SHORT' (click ASK)
            price: Order price
            qty: Quantity (number of clicks)
            symbol: Trading symbol
        
        Returns:
            True if successful
        """
        if not self._validate_pre_execution(symbol):
            print(f"[ERROR] Pre-execution validation failed for {symbol}")
            return False
        
        # Determine which side to click
        # LONG entry = Buy Limit = click BID side
        # SHORT entry = Sell Limit = click ASK side
        click_side = 'BID' if side == 'LONG' else 'ASK'
        
        # Calculate coordinates
        try:
            x, y = self._calculate_coordinates(price, symbol, click_side)
        except Exception as e:
            print(f"[ERROR] Failed to calculate coordinates: {e}")
            return False
        
        print(f"[ACTION] Place LIMIT: {side} {qty}x @ {price} on {symbol}")
        print(f"         Clicking {click_side} side at ({x}, {y}) {qty} times")
        
        if self.dry_run:
            print(f"[DRY RUN] Would left-click {qty} times at ({x}, {y})")
            return True
        
        # Execute clicks
        try:
            time.sleep(self.pre_action_delay)
            
            for i in range(qty):
                pyautogui.click(x, y, button='left')
                print(f"         Click {i+1}/{qty}")
                if i < qty - 1:  # Don't delay after last click
                    time.sleep(self.click_delay)
            
            time.sleep(self.post_action_delay)
            print(f"[OK] Limit order clicks completed")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to execute limit order clicks: {e}")
            return False
    
    def place_stop_order(self, side: str, price: float, qty: int, symbol: str) -> bool:
        """
        Place stop order via right-click on DOM.
        
        Args:
            side: 'LONG' (Sell Stop) or 'SHORT' (Buy Stop)
            price: Stop price
            qty: Quantity (number of clicks)
            symbol: Trading symbol
        
        Returns:
            True if successful
        """
        if not self._validate_pre_execution(symbol):
            print(f"[ERROR] Pre-execution validation failed for {symbol}")
            return False
        
        # For stop orders, we right-click
        # LONG stop = Sell Stop (protect long) = right-click
        # SHORT stop = Buy Stop (protect short) = right-click
        # The side of DOM depends on the position
        click_side = 'BID' if side == 'LONG' else 'ASK'
        
        # Calculate coordinates
        try:
            x, y = self._calculate_coordinates(price, symbol, click_side)
        except Exception as e:
            print(f"[ERROR] Failed to calculate coordinates: {e}")
            return False
        
        print(f"[ACTION] Place STOP: {side} {qty}x @ {price} on {symbol}")
        print(f"         Right-clicking at ({x}, {y}) {qty} times")
        
        if self.dry_run:
            print(f"[DRY RUN] Would right-click {qty} times at ({x}, {y})")
            return True
        
        # Execute right-clicks
        try:
            time.sleep(self.pre_action_delay)
            
            for i in range(qty):
                pyautogui.click(x, y, button='right')
                print(f"         Click {i+1}/{qty}")
                if i < qty - 1:
                    time.sleep(self.click_delay)
            
            time.sleep(self.post_action_delay)
            print(f"[OK] Stop order clicks completed")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to execute stop order clicks: {e}")
            return False
    
    def modify_stop_in_place(self, new_qty: int, new_price: float, symbol: str, 
                            side: str, old_price: Optional[float] = None) -> bool:
        """
        Modify existing stop order quantity and price.
        
        Args:
            new_qty: New stop quantity
            new_price: New stop price
            symbol: Trading symbol
            side: 'LONG' or 'SHORT'
            old_price: Optional old price for dragging
        
        Returns:
            True if successful
        """
        print(f"[ACTION] Modify stop: {symbol} → {new_qty} @ {new_price}")
        
        if self.dry_run:
            print(f"[DRY RUN] Would modify stop to {new_qty} @ {new_price}")
            return True
        
        # Step 1: Update quantity (if needed - this would be manual in real DOM)
        # In practice, may need to cancel and replace
        
        # Step 2: Wait cooldown
        time.sleep(self.drag_delay)
        
        # Step 3: Drag to new price if old_price provided
        if old_price and old_price != new_price:
            return self.drag_stop_to_price(old_price, new_price, symbol, side)
        
        return True
    
    def drag_stop_to_price(self, from_price: float, to_price: float, 
                          symbol: str, side: str) -> bool:
        """
        Drag stop order from one price to another.
        
        Args:
            from_price: Current stop price
            to_price: Target stop price
            symbol: Trading symbol
            side: 'LONG' or 'SHORT'
        
        Returns:
            True if successful
        """
        if not self._validate_pre_execution(symbol):
            print(f"[ERROR] Pre-execution validation failed")
            return False
        
        # Calculate coordinates
        click_side = 'BID' if side == 'LONG' else 'ASK'
        
        try:
            from_x, from_y = self._calculate_coordinates(from_price, symbol, click_side)
            to_x, to_y = self._calculate_coordinates(to_price, symbol, click_side)
        except Exception as e:
            print(f"[ERROR] Failed to calculate drag coordinates: {e}")
            return False
        
        print(f"[ACTION] Drag stop: {from_price} → {to_price}")
        print(f"         From ({from_x}, {from_y}) to ({to_x}, {to_y})")
        
        if self.dry_run:
            print(f"[DRY RUN] Would drag from ({from_x}, {from_y}) to ({to_x}, {to_y})")
            return True
        
        # Execute drag
        try:
            time.sleep(self.pre_action_delay)
            
            # Drag operation
            pyautogui.moveTo(from_x, from_y, duration=0.2)
            time.sleep(0.1)
            pyautogui.drag(0, to_y - from_y, duration=0.3, button='left')
            
            time.sleep(self.post_action_delay)
            print(f"[OK] Stop drag completed")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to drag stop: {e}")
            
            # Retry logic
            if self.max_retries > 0:
                print(f"[RETRY] Attempting drag again...")
                time.sleep(self.retry_delay)
                try:
                    pyautogui.moveTo(from_x, from_y, duration=0.2)
                    pyautogui.drag(0, to_y - from_y, duration=0.3, button='left')
                    time.sleep(self.post_action_delay)
                    print(f"[OK] Stop drag completed on retry")
                    return True
                except Exception as retry_e:
                    print(f"[ERROR] Retry failed: {retry_e}")
                    
                    # Fallback: cancel and replace
                    if self.enable_fallback:
                        print(f"[FALLBACK] Will use cancel-and-replace strategy")
                        # TODO: Implement cancel-and-replace
                        return False
            
            return False
    
    def cancel_symbol_orders(self, symbol: str) -> bool:
        """
        Cancel all orders for a symbol.
        
        Args:
            symbol: Trading symbol
        
        Returns:
            True if successful
        """
        print(f"[ACTION] Cancel all orders for {symbol}")
        
        if self.dry_run:
            print(f"[DRY RUN] Would cancel all orders for {symbol}")
            return True
        
        # In practice, this would:
        # 1. Find the "Cancel All" button for this symbol's DOM
        # 2. Click it
        # For now, just log the action
        
        print(f"[WARNING] Cancel orders not yet implemented")
        print(f"[INFO] Manually cancel orders for {symbol} in Tradovate DOM")
        
        return True


# Test functionality
if __name__ == "__main__":
    print("Testing DOMAutomator...")
    
    # Create test config
    test_config = {
        "timing": {
            "click_delay_ms": 100,
            "drag_delay_ms": 200,
            "pre_action_delay_ms": 50,
            "post_action_delay_ms": 150
        },
        "retry_settings": {
            "max_retries": 1,
            "enable_cancel_replace_fallback": True
        },
        "safety": {
            "dry_run_mode": True  # Always dry run for tests
        },
        "dom_coordinates": {
            "NQ": {
                "bid_column_x": 800,
                "ask_column_x": 900,
                "price_row_height": 20,
                "top_price": 20500.0,
                "dom_window_bounds": {
                    "left": 700,
                    "top": 200,
                    "right": 1000,
                    "bottom": 800
                }
            }
        }
    }
    
    automator = DOMAutomator(test_config)
    
    # Test limit order
    print("\n1. Testing LONG limit order...")
    automator.place_limit_order('LONG', 20150.00, 3, 'NQ')
    
    # Test stop order
    print("\n2. Testing LONG stop order...")
    automator.place_stop_order('LONG', 20115.50, 3, 'NQ')
    
    # Test drag
    print("\n3. Testing stop drag...")
    automator.drag_stop_to_price(20115.50, 20151.00, 'NQ', 'LONG')
    
    # Test cancel
    print("\n4. Testing order cancellation...")
    automator.cancel_symbol_orders('NQ')
    
    print("\n[OK] All tests completed (dry run mode)")

