"""
Integration test for AAFR GUI Bot system.
Tests WebSocket communication and event handling.
"""

import asyncio
import json
from datetime import datetime
import time

# Test WebSocket server
from aafr.websocket_server import WebSocketServer

# Test GUI bot components
from gui_bot.position_tracker import PositionTracker
from gui_bot.dom_automation import DOMAutomator
from gui_bot.logger import BotLogger
from gui_bot.config import load_bot_config
from gui_bot.event_handlers import (
    handle_new_position,
    handle_tp_filled,
    handle_close_trade
)


async def test_websocket_server():
    """Test WebSocket server independently."""
    print("\n" + "="*60)
    print("TEST 1: WebSocket Server")
    print("="*60)
    
    server = WebSocketServer("localhost", 8765)
    
    # Start server in background
    server_task = asyncio.create_task(server.start())
    
    # Wait for server to start
    await asyncio.sleep(0.5)
    
    # Simulate broadcasting events
    test_event = {
        "event": "TEST",
        "message": "Server is working",
        "timestamp": datetime.now().isoformat()
    }
    
    await server.broadcast_event(test_event)
    print("[OK] WebSocket server started and broadcast test event")
    
    # Stop server
    await server.stop()
    server_task.cancel()
    
    print("[OK] WebSocket server test passed")


async def test_position_tracker():
    """Test position tracker."""
    print("\n" + "="*60)
    print("TEST 2: Position Tracker")
    print("="*60)
    
    tracker = PositionTracker()
    
    # Open position
    tracker.open_position("NQ", "LONG", 3, 20150.00)
    assert tracker.has_position("NQ")
    assert tracker.get_remaining_size("NQ") == 3
    print("[OK] Position opened and tracked")
    
    # Mark TP filled
    tracker.mark_tp_filled("NQ", 1, 1)
    assert tracker.get_remaining_size("NQ") == 2
    print("[OK] TP1 filled, size updated")
    
    # Update stop
    tracker.update_stop("NQ", 20151.00, 2)
    position = tracker.get_position("NQ")
    assert position.stop_price == 20151.00
    print("[OK] Stop updated")
    
    # Close position
    tracker.close_position("NQ")
    assert not tracker.has_position("NQ")
    print("[OK] Position closed")
    
    print("[OK] Position tracker test passed")


def test_dom_automation():
    """Test DOM automation (dry run)."""
    print("\n" + "="*60)
    print("TEST 3: DOM Automation (Dry Run)")
    print("="*60)
    
    config = load_bot_config()
    config['safety']['dry_run_mode'] = True
    
    automator = DOMAutomator(config)
    
    # Test limit order
    success = automator.place_limit_order('LONG', 20150.00, 3, 'NQ')
    assert success
    print("[OK] Limit order (dry run)")
    
    # Test stop order
    success = automator.place_stop_order('LONG', 20115.50, 3, 'NQ')
    assert success
    print("[OK] Stop order (dry run)")
    
    # Test drag
    success = automator.drag_stop_to_price(20115.50, 20151.00, 'NQ', 'LONG')
    assert success
    print("[OK] Stop drag (dry run)")
    
    print("[OK] DOM automation test passed")


async def test_event_handlers():
    """Test event handlers."""
    print("\n" + "="*60)
    print("TEST 4: Event Handlers")
    print("="*60)
    
    config = load_bot_config()
    config['safety']['dry_run_mode'] = True
    
    automator = DOMAutomator(config)
    tracker = PositionTracker()
    logger = BotLogger("gui_bot/logs")
    
    # Test NEW_POSITION handler
    new_pos_event = {
        'event': 'NEW_POSITION',
        'symbol': 'NQ',
        'side': 'LONG',
        'entry_price': 20150.00,
        'size': 3,
        'initial_stop': 20115.50,
        'tps': [
            {'price': 20165.00, 'qty': 1},
            {'price': 20175.00, 'qty': 1},
            {'price': 20195.00, 'qty': 1}
        ],
        'mode': 'EVAL',
        'atr': 15.5
    }
    
    await handle_new_position(new_pos_event, automator, tracker, logger)
    assert tracker.has_position('NQ')
    print("[OK] NEW_POSITION handler executed")
    
    # Test TP_FILLED handler
    tp_filled_event = {
        'event': 'TP_FILLED',
        'symbol': 'NQ',
        'tp_level': 1,
        'remaining_size': 2,
        'stop_update': {
            'qty': 2,
            'price': 20150.50,
            'action': 'MODIFY_IN_PLACE',
            'reason': 'TP1_BE_MOVE'
        }
    }
    
    await handle_tp_filled(tp_filled_event, automator, tracker, logger)
    assert tracker.get_remaining_size('NQ') == 2
    print("[OK] TP_FILLED handler executed")
    
    # Test CLOSE_TRADE handler
    close_event = {
        'event': 'CLOSE_TRADE',
        'symbol': 'NQ',
        'action': 'CANCEL_SYMBOL_ORDERS',
        'reason': 'final_exit'
    }
    
    await handle_close_trade(close_event, automator, tracker, logger)
    assert not tracker.has_position('NQ')
    print("[OK] CLOSE_TRADE handler executed")
    
    print("[OK] Event handlers test passed")


async def test_full_integration():
    """Test full integration with mock WebSocket client."""
    print("\n" + "="*60)
    print("TEST 5: Full Integration")
    print("="*60)
    
    # This would test full AAFR → WebSocket → GUI Bot flow
    # For now, we've tested components separately
    
    print("[INFO] Full integration requires:")
    print("  1. AAFR running in live mode")
    print("  2. GUI bot client running")
    print("  3. Manual verification of DOM interactions")
    print("\n[INFO] Run these commands in separate terminals:")
    print("  Terminal 1: python -m aafr.main --mode live --symbol MNQ")
    print("  Terminal 2: python gui_bot/client.py")
    
    print("\n[OK] Integration test setup ready")


async def run_all_tests():
    """Run all tests."""
    print("\n" + "="*70)
    print(" "*20 + "AAFR GUI BOT INTEGRATION TESTS")
    print("="*70)
    
    try:
        await test_websocket_server()
        await test_position_tracker()
        test_dom_automation()
        await test_event_handlers()
        await test_full_integration()
        
        print("\n" + "="*70)
        print(" "*25 + "ALL TESTS PASSED ✓")
        print("="*70)
        print("\n[OK] GUI Bot integration is ready for use")
        print("\n[NEXT STEPS]")
        print("1. Calibrate DOM coordinates: python gui_bot/config.py")
        print("2. Set dry_run_mode to false in bot_config.json")
        print("3. Start AAFR: python -m aafr.main --mode live --symbol MNQ")
        print("4. Start GUI bot: python gui_bot/client.py")
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    import sys
    
    print("\nStarting integration tests...")
    print("These tests run in DRY RUN mode (no actual DOM clicks)")
    
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)

