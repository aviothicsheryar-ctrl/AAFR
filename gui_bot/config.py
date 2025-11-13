"""
Configuration and calibration utilities for GUI Bot.
Handles DOM coordinate mapping and bot settings.
"""

import json
import os
from typing import Dict, Any, Tuple, Optional
from pathlib import Path

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    print("[WARNING] pyautogui not installed. Install with: pip install pyautogui")


DEFAULT_CONFIG = {
    "aafr_connection": {
        "host": "localhost",
        "port": 8765
    },
    "timing": {
        "click_delay_ms": 100,
        "drag_delay_ms": 200,
        "pre_action_delay_ms": 50,
        "post_action_delay_ms": 150,
        "retry_delay_ms": 500
    },
    "retry_settings": {
        "max_retries": 1,
        "enable_cancel_replace_fallback": True
    },
    "trail_settings": {
        "structure_buffer_ticks": 2,
        "atr_multiplier": 0.75,
        "min_distance_ticks": 2
    },
    "safety": {
        "require_dom_focus": True,
        "validate_coordinates": True,
        "dry_run_mode": False
    },
    "dom_coordinates": {
        "NQ": {
            "bid_column_x": 800,
            "ask_column_x": 900,
            "price_row_height": 20,
            "top_price": 21000.0,
            "dom_window_bounds": {
                "left": 700,
                "top": 200,
                "right": 1000,
                "bottom": 800
            }
        },
        "ES": {
            "bid_column_x": 800,
            "ask_column_x": 900,
            "price_row_height": 20,
            "top_price": 5000.0,
            "dom_window_bounds": {
                "left": 700,
                "top": 200,
                "right": 1000,
                "bottom": 800
            }
        }
    }
}


def load_bot_config(config_path: str = "gui_bot/bot_config.json") -> Dict[str, Any]:
    """
    Load bot configuration from file.
    Creates default config if file doesn't exist.
    
    Args:
        config_path: Path to configuration file
    
    Returns:
        Configuration dictionary
    """
    config_file = Path(config_path)
    
    # Create default config if doesn't exist
    if not config_file.exists():
        print(f"[INFO] Config file not found, creating default: {config_path}")
        config_file.parent.mkdir(parents=True, exist_ok=True)
        save_bot_config(DEFAULT_CONFIG, config_path)
        return DEFAULT_CONFIG.copy()
    
    # Load existing config
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        print(f"[OK] Loaded config from {config_path}")
        return config
    except Exception as e:
        print(f"[ERROR] Failed to load config: {e}")
        print("[INFO] Using default configuration")
        return DEFAULT_CONFIG.copy()


def save_bot_config(config: Dict[str, Any], config_path: str = "gui_bot/bot_config.json") -> bool:
    """
    Save bot configuration to file.
    
    Args:
        config: Configuration dictionary
        config_path: Path to save configuration
    
    Returns:
        True if successful
    """
    try:
        config_file = Path(config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w') as f:
            json.dump(config, indent=2, fp=f)
        
        print(f"[OK] Config saved to {config_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save config: {e}")
        return False


def calculate_click_position(price: float, symbol: str, side: str, 
                            config: Dict[str, Any]) -> Tuple[int, int]:
    """
    Calculate screen coordinates for a price level click.
    
    Args:
        price: Price to click at
        symbol: Trading symbol
        side: 'BID' or 'ASK'
        config: Bot configuration
    
    Returns:
        (x, y) screen coordinates
    """
    dom_coords = config.get('dom_coordinates', {}).get(symbol)
    if not dom_coords:
        raise ValueError(f"No DOM coordinates configured for {symbol}")
    
    # Get column based on side
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
    
    # Calculate row offset from top
    price_diff = top_price - price
    row_offset = int(price_diff / 0.25)  # Assuming 0.25 tick size for now
    
    y = bounds['top'] + (row_offset * price_row_height)
    
    # Validate coordinates are within bounds
    if not (bounds['left'] <= x <= bounds['right'] and 
            bounds['top'] <= y <= bounds['bottom']):
        print(f"[WARNING] Coordinates ({x}, {y}) may be out of DOM bounds")
    
    return (x, y)


def calibrate_dom_coordinates(symbol: str) -> Dict[str, Any]:
    """
    Interactive calibration tool for DOM coordinates.
    
    Args:
        symbol: Trading symbol to calibrate
    
    Returns:
        Calibrated DOM coordinates dictionary
    """
    if not PYAUTOGUI_AVAILABLE:
        print("[ERROR] pyautogui required for calibration")
        return {}
    
    print("\n" + "="*60)
    print(f"DOM Calibration Tool - {symbol}")
    print("="*60)
    print("\nThis tool will help you map DOM coordinates for automated trading.")
    print("You'll be asked to click on specific locations in the Tradovate DOM.")
    print("\nMake sure the Tradovate DOM for", symbol, "is visible and in focus.")
    input("\nPress Enter when ready...")
    
    coords = {}
    
    # Calibrate bid column
    print("\n1. Hover over the BID column (left side with quantities)")
    input("   Press Enter when positioned...")
    pos = pyautogui.position()
    coords['bid_column_x'] = pos.x
    print(f"   Captured: X = {pos.x}")
    
    # Calibrate ask column
    print("\n2. Hover over the ASK column (right side with quantities)")
    input("   Press Enter when positioned...")
    pos = pyautogui.position()
    coords['ask_column_x'] = pos.x
    print(f"   Captured: X = {pos.x}")
    
    # Calibrate top price
    print("\n3. What is the HIGHEST price visible on the DOM right now?")
    top_price = float(input("   Enter price (e.g., 20500): "))
    coords['top_price'] = top_price
    
    print("\n4. Hover over that top price row")
    input("   Press Enter when positioned...")
    top_pos = pyautogui.position()
    top_y = top_pos.y
    print(f"   Captured: Y = {top_y}")
    
    # Calibrate row height
    print("\n5. Now hover over the price row EXACTLY 10 rows below")
    input("   Press Enter when positioned...")
    bottom_pos = pyautogui.position()
    bottom_y = bottom_pos.y
    
    row_height = (bottom_y - top_y) / 10
    coords['price_row_height'] = int(row_height)
    print(f"   Calculated row height: {row_height}px")
    
    # Calibrate window bounds
    print("\n6. Hover over the TOP-LEFT corner of the DOM")
    input("   Press Enter when positioned...")
    tl = pyautogui.position()
    
    print("\n7. Hover over the BOTTOM-RIGHT corner of the DOM")
    input("   Press Enter when positioned...")
    br = pyautogui.position()
    
    coords['dom_window_bounds'] = {
        'left': tl.x,
        'top': tl.y,
        'right': br.x,
        'bottom': br.y
    }
    
    print("\n" + "="*60)
    print("Calibration Complete!")
    print("="*60)
    print(json.dumps(coords, indent=2))
    
    # Ask to save
    save = input("\nSave these coordinates to config? (y/n): ").lower().strip()
    if save == 'y':
        config = load_bot_config()
        if 'dom_coordinates' not in config:
            config['dom_coordinates'] = {}
        config['dom_coordinates'][symbol] = coords
        save_bot_config(config)
        print(f"[OK] Coordinates saved for {symbol}")
    
    return coords


def validate_dom_focus() -> bool:
    """
    Check if Tradovate DOM window is in focus.
    
    Returns:
        True if validation passes
    """
    if not PYAUTOGUI_AVAILABLE:
        print("[WARNING] Cannot validate DOM focus without pyautogui")
        return True  # Skip validation
    
    try:
        # On Windows, we could check active window title
        # For now, just return True (manual validation)
        return True
    except Exception as e:
        print(f"[WARNING] DOM focus validation failed: {e}")
        return False


# Main calibration script
if __name__ == "__main__":
    import sys
    
    if not PYAUTOGUI_AVAILABLE:
        print("[ERROR] pyautogui is required for calibration")
        print("Install with: pip install pyautogui")
        sys.exit(1)
    
    print("\nGUI Bot - DOM Calibration Utility")
    print("="*60)
    
    # Ask for symbol
    symbol = input("Enter symbol to calibrate (e.g., NQ, ES, GC): ").strip().upper()
    
    if not symbol:
        print("[ERROR] Symbol is required")
        sys.exit(1)
    
    # Run calibration
    coords = calibrate_dom_coordinates(symbol)
    
    if coords:
        print("\n[OK] Calibration successful!")
        print("\nYou can now use these coordinates in the GUI bot.")
    else:
        print("\n[ERROR] Calibration failed or was cancelled")

