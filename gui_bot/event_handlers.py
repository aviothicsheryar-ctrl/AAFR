"""
Event handlers for GUI bot.
Processes trade events and executes appropriate DOM actions.
"""

import asyncio
from typing import Dict, Any
from gui_bot.dom_automation import DOMAutomator
from gui_bot.position_tracker import PositionTracker
from gui_bot.logger import BotLogger


async def handle_new_position(event: Dict[str, Any], automator: DOMAutomator,
                              tracker: PositionTracker, logger: BotLogger) -> None:
    """
    Handle NEW_POSITION event.
    Places entry order, initial stop, and TP ladder.
    
    Args:
        event: NEW_POSITION event dictionary
        automator: DOM automator instance
        tracker: Position tracker instance
        logger: Logger instance
    """
    symbol = event.get('symbol')
    side = event.get('side')
    entry_price = event.get('entry_price')
    size = event.get('size')
    initial_stop = event.get('initial_stop')
    tps = event.get('tps', [])
    mode = event.get('mode', 'EVAL')
    atr = event.get('atr', 0)
    
    logger.info(f"Processing NEW_POSITION: {symbol} {side} {size}x @ {entry_price}")
    print(f"\n{'='*60}")
    print(f"NEW POSITION: {symbol} {side}")
    print(f"Entry: {entry_price} | Size: {size} | Stop: {initial_stop}")
    print(f"TPs: {len(tps)} levels | Mode: {mode}")
    print(f"{'='*60}")
    
    try:
        # Step 1: Place entry order (Limit order)
        print(f"\n[1/3] Placing entry order...")
        success = automator.place_limit_order(side, entry_price, size, symbol)
        if success:
            logger.log_click(
                'BUY' if side == 'LONG' else 'SELL',
                'LIMIT',
                entry_price,
                size,
                symbol,
                (0, 0)  # Coordinates logged in automator
            )
        else:
            logger.log_error(f"Failed to place entry order for {symbol}")
            return
        
        # Small delay between actions
        await asyncio.sleep(0.2)
        
        # Step 2: Place initial stop (Stop order with ATR buffer)
        print(f"\n[2/3] Placing initial stop @ {initial_stop}...")
        # Apply ATR buffer to stop if provided
        if atr > 0:
            buffer = atr * 0.5
            if side == 'LONG':
                buffered_stop = initial_stop - buffer
            else:
                buffered_stop = initial_stop + buffer
            print(f"         Stop with buffer: {buffered_stop} (ATR: {atr})")
            stop_price = buffered_stop
        else:
            stop_price = initial_stop
        
        success = automator.place_stop_order(side, stop_price, size, symbol)
        if success:
            logger.log_click(
                'SELL' if side == 'LONG' else 'BUY',
                'STOP',
                stop_price,
                size,
                symbol,
                (0, 0)
            )
        else:
            logger.log_error(f"Failed to place stop for {symbol}")
            return
        
        await asyncio.sleep(0.2)
        
        # Step 3: Place TP ladder
        print(f"\n[3/3] Placing TP ladder ({len(tps)} levels)...")
        for i, tp in enumerate(tps, 1):
            tp_price = tp.get('price')
            tp_qty = tp.get('qty')
            
            print(f"         TP{i}: {tp_qty}x @ {tp_price}")
            
            # TPs are limit orders on opposite side
            # LONG position: Sell Limit (exit) → click ASK side
            # SHORT position: Buy Limit (exit) → click BID side
            tp_side = 'SHORT' if side == 'LONG' else 'LONG'
            
            success = automator.place_limit_order(tp_side, tp_price, tp_qty, symbol)
            if success:
                logger.log_click(
                    'SELL' if side == 'LONG' else 'BUY',
                    'LIMIT',
                    tp_price,
                    tp_qty,
                    symbol,
                    (0, 0)
                )
            
            await asyncio.sleep(0.1)
        
        # Record position in tracker
        tracker.open_position(symbol, side, size, entry_price)
        tracker.update_stop(symbol, stop_price, size)
        tracker.set_tps(symbol, [tp['price'] for tp in tps])
        
        logger.log_position_update(symbol, 'OPENED', f"{side} {size}x @ {entry_price}")
        print(f"\n[OK] Position setup complete for {symbol}")
        
    except Exception as e:
        logger.log_error(f"Error handling NEW_POSITION: {e}", {'event': event})
        print(f"\n[ERROR] Failed to process NEW_POSITION: {e}")


async def handle_tp_filled(event: Dict[str, Any], automator: DOMAutomator,
                          tracker: PositionTracker, logger: BotLogger) -> None:
    """
    Handle TP_FILLED event.
    Updates stop quantity and drags to new price.
    
    Args:
        event: TP_FILLED event dictionary
        automator: DOM automator instance
        tracker: Position tracker instance
        logger: Logger instance
    """
    symbol = event.get('symbol')
    tp_level = event.get('tp_level')
    remaining_size = event.get('remaining_size')
    stop_update = event.get('stop_update', {})
    
    logger.info(f"Processing TP_FILLED: {symbol} TP{tp_level}, remaining: {remaining_size}")
    print(f"\n{'='*60}")
    print(f"TP{tp_level} FILLED: {symbol}")
    print(f"Remaining size: {remaining_size}")
    print(f"{'='*60}")
    
    try:
        # Get position details
        position = tracker.get_position(symbol)
        if not position:
            logger.log_error(f"No position found for {symbol}")
            print(f"[ERROR] No position tracked for {symbol}")
            return
        
        # Mark TP as filled
        # Calculate qty filled (difference from before)
        qty_filled = position.current_size - remaining_size
        tracker.mark_tp_filled(symbol, tp_level, qty_filled)
        
        # Update stop
        new_stop_price = stop_update.get('price')
        new_stop_qty = stop_update.get('qty', remaining_size)
        action = stop_update.get('action', 'MODIFY_IN_PLACE')
        reason = stop_update.get('reason', f'TP{tp_level}_ADJUSTMENT')
        
        print(f"\n[1/2] Updating stop quantity to {new_stop_qty}...")
        print(f"[2/2] Moving stop to {new_stop_price} ({reason})...")
        
        # Get old stop price for dragging
        old_stop_price = position.stop_price
        
        # Modify stop in place
        if action == 'MODIFY_IN_PLACE' and old_stop_price:
            success = automator.modify_stop_in_place(
                new_stop_qty,
                new_stop_price,
                symbol,
                position.side,
                old_stop_price
            )
            
            if success:
                logger.log_drag(symbol, old_stop_price, new_stop_price, new_stop_qty, reason)
                tracker.update_stop(symbol, new_stop_price, new_stop_qty)
            else:
                logger.log_error(f"Failed to modify stop for {symbol}")
        else:
            logger.log_error(f"Unsupported stop update action: {action}")
        
        logger.log_position_update(symbol, f'TP{tp_level}_FILLED', 
                                  f"Remaining: {remaining_size}, Stop @ {new_stop_price}")
        print(f"\n[OK] TP{tp_level} processing complete")
        
    except Exception as e:
        logger.log_error(f"Error handling TP_FILLED: {e}", {'event': event})
        print(f"\n[ERROR] Failed to process TP_FILLED: {e}")


async def handle_stop_update(event: Dict[str, Any], automator: DOMAutomator,
                             tracker: PositionTracker, logger: BotLogger) -> None:
    """
    Handle STOP_UPDATE event.
    Updates stop order details.
    
    Args:
        event: STOP_UPDATE event dictionary
        automator: DOM automator instance
        tracker: Position tracker instance
        logger: Logger instance
    """
    symbol = event.get('symbol')
    details = event.get('details', {})
    
    price = details.get('price')
    qty = details.get('qty')
    reason = details.get('reason', 'UPDATE')
    method = details.get('method', 'MODIFY_IN_PLACE')
    
    logger.info(f"Processing STOP_UPDATE: {symbol} → {qty} @ {price}")
    print(f"\n{'='*60}")
    print(f"STOP UPDATE: {symbol}")
    print(f"New stop: {qty}x @ {price} | Reason: {reason}")
    print(f"{'='*60}")
    
    try:
        position = tracker.get_position(symbol)
        if not position:
            logger.log_error(f"No position found for {symbol}")
            return
        
        old_stop_price = position.stop_price
        
        # Apply update
        if method == 'MODIFY_IN_PLACE' and old_stop_price:
            success = automator.modify_stop_in_place(
                qty, price, symbol, position.side, old_stop_price
            )
            
            if success:
                logger.log_drag(symbol, old_stop_price, price, qty, reason)
                tracker.update_stop(symbol, price, qty)
                print(f"[OK] Stop updated")
            else:
                logger.log_error(f"Failed to update stop for {symbol}")
        
    except Exception as e:
        logger.log_error(f"Error handling STOP_UPDATE: {e}", {'event': event})
        print(f"\n[ERROR] Failed to process STOP_UPDATE: {e}")


async def handle_close_trade(event: Dict[str, Any], automator: DOMAutomator,
                             tracker: PositionTracker, logger: BotLogger) -> None:
    """
    Handle CLOSE_TRADE event.
    Cancels all orders for symbol and cleans up position.
    
    Args:
        event: CLOSE_TRADE event dictionary
        automator: DOM automator instance
        tracker: Position tracker instance
        logger: Logger instance
    """
    symbol = event.get('symbol')
    action = event.get('action', 'CANCEL_SYMBOL_ORDERS')
    reason = event.get('reason', 'final_exit')
    
    logger.info(f"Processing CLOSE_TRADE: {symbol} | Reason: {reason}")
    print(f"\n{'='*60}")
    print(f"CLOSE TRADE: {symbol}")
    print(f"Reason: {reason}")
    print(f"{'='*60}")
    
    try:
        # Cancel all orders for this symbol
        if action == 'CANCEL_SYMBOL_ORDERS':
            print(f"\n[1/2] Cancelling all orders for {symbol}...")
            success = automator.cancel_symbol_orders(symbol)
            
            if not success:
                logger.log_error(f"Failed to cancel orders for {symbol}")
        
        # Close position in tracker
        print(f"[2/2] Clearing position from tracker...")
        tracker.close_position(symbol)
        
        logger.log_position_update(symbol, 'CLOSED', f"Reason: {reason}")
        print(f"\n[OK] Trade closed for {symbol}")
        
    except Exception as e:
        logger.log_error(f"Error handling CLOSE_TRADE: {e}", {'event': event})
        print(f"\n[ERROR] Failed to process CLOSE_TRADE: {e}")


# Test handlers with mock data
if __name__ == "__main__":
    import asyncio
    from gui_bot.config import load_bot_config
    
    print("Testing event handlers...")
    
    # Load config
    config = load_bot_config()
    config['safety']['dry_run_mode'] = True  # Force dry run
    
    # Initialize components
    automator = DOMAutomator(config)
    tracker = PositionTracker()
    logger = BotLogger("gui_bot/logs")
    
    async def test_handlers():
        # Test NEW_POSITION
        print("\n" + "="*60)
        print("TEST 1: NEW_POSITION")
        print("="*60)
        
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
        
        # Test TP_FILLED
        print("\n" + "="*60)
        print("TEST 2: TP_FILLED")
        print("="*60)
        
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
        
        # Test CLOSE_TRADE
        print("\n" + "="*60)
        print("TEST 3: CLOSE_TRADE")
        print("="*60)
        
        close_event = {
            'event': 'CLOSE_TRADE',
            'symbol': 'NQ',
            'action': 'CANCEL_SYMBOL_ORDERS',
            'reason': 'final_exit'
        }
        
        await handle_close_trade(close_event, automator, tracker, logger)
        
        # Show metrics
        print("\n" + "="*60)
        logger.log_metrics_summary()
    
    asyncio.run(test_handlers())
    print("\n[OK] Handler tests complete")

