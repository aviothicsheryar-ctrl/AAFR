# AAFR GUI Bot

Automated Tradovate DOM interaction client for AAFR trading system.

## Overview

The GUI Bot connects to the AAFR trading system via WebSocket and automatically executes trades by clicking and dragging on the Tradovate DOM (Depth of Market) interface. It eliminates manual order placement while maintaining full control through the Tradovate platform.

## Architecture

```
AAFR System → WebSocket → GUI Bot → PyAutoGUI → Tradovate DOM
```

- **AAFR** calculates trade signals and emits events
- **WebSocket** provides real-time communication
- **GUI Bot** receives events and executes automation
- **PyAutoGUI** performs mouse clicks and drags
- **Tradovate DOM** receives the automated interactions

## Features

- ✅ Automated entry order placement (Limit orders)
- ✅ Automated stop loss placement (Stop orders)
- ✅ TP ladder creation (3-level take profit)
- ✅ Trailing stop management (break-even and structure-based)
- ✅ Per-symbol position tracking
- ✅ Comprehensive logging and error handling
- ✅ Dry run mode for testing
- ✅ DOM calibration utility

## Installation

### 1. Install Dependencies

```bash
cd gui_bot
pip install -r requirements.txt
```

Or manually:

```bash
pip install websockets pyautogui
```

### 2. Calibrate DOM Coordinates

Before running the bot, you must calibrate the DOM coordinates for each symbol you trade:

```bash
python gui_bot/config.py
```

Follow the interactive prompts to map:
- Bid column X position
- Ask column X position
- Top price and row height
- DOM window bounds

The calibration tool will save coordinates to `gui_bot/bot_config.json`.

### 3. Configure Settings

Edit `gui_bot/bot_config.json` (auto-created on first run):

```json
{
  "aafr_connection": {
    "host": "localhost",
    "port": 8765
  },
  "timing": {
    "click_delay_ms": 100,
    "drag_delay_ms": 200
  },
  "safety": {
    "dry_run_mode": false
  }
}
```

## Usage

### Start the GUI Bot

1. **Start AAFR in live mode:**

```bash
python -m aafr.main --mode live --symbol MNQ
```

2. **Start the GUI Bot:**

```bash
python gui_bot/client.py
```

3. **Open Tradovate** with the DOM visible for your symbol

The bot will connect to AAFR and wait for trade signals.

### Trade Flow

When AAFR detects a trade signal:

1. **NEW_POSITION** event is broadcast
2. GUI Bot receives event
3. Bot clicks DOM to place:
   - Entry order (Limit)
   - Initial stop (Stop with ATR buffer)
   - TP ladder (3 levels)
4. Position is tracked locally

When TP levels are hit (monitored by AAFR):

5. **TP_FILLED** event is broadcast
6. Bot adjusts stop:
   - TP1: Move to break-even
   - TP2: Trail to structure
   - TP3: Hard TP (EVAL) or runner (LIVE)

When trade is complete:

7. **CLOSE_TRADE** event is broadcast
8. Bot cancels remaining orders
9. Position is cleared

## Click Mapping

### Long Trade
- **Entry**: Left-click BID side (Buy Limit)
- **Stop**: Right-click below entry (Sell Stop)
- **TPs**: Left-click ASK side (Sell Limit)

### Short Trade
- **Entry**: Left-click ASK side (Sell Limit)
- **Stop**: Right-click above entry (Buy Stop)
- **TPs**: Left-click BID side (Buy Limit)

## Safety Features

### Pre-Execution Validation
- DOM focus verification
- Coordinate bounds checking
- Dry run mode for testing

### Error Handling
- Retry logic (1 attempt)
- Cancel-and-replace fallback
- Comprehensive error logging

### Emergency Stop
- Move mouse to screen corner (PyAutoGUI failsafe)
- Press Ctrl+C to stop bot
- Manually manage positions in Tradovate

## Configuration Reference

### Timing Settings

```json
"timing": {
  "click_delay_ms": 100,        // Delay between clicks
  "drag_delay_ms": 200,          // Delay before drag
  "pre_action_delay_ms": 50,     // Delay before action
  "post_action_delay_ms": 150,   // Delay after action
  "retry_delay_ms": 500          // Delay before retry
}
```

### Retry Settings

```json
"retry_settings": {
  "max_retries": 1,
  "enable_cancel_replace_fallback": true
}
```

### Trail Settings

```json
"trail_settings": {
  "structure_buffer_ticks": 2,   // Ticks beyond swing
  "atr_multiplier": 0.75,        // ATR trailing distance
  "min_distance_ticks": 2        // Min stop distance
}
```

### Safety Settings

```json
"safety": {
  "require_dom_focus": true,
  "validate_coordinates": true,
  "dry_run_mode": false         // Set true for testing
}
```

## DOM Coordinate Format

Each symbol needs calibrated coordinates:

```json
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
  }
}
```

## Testing

### Dry Run Mode

Enable dry run in config:

```json
"safety": {
  "dry_run_mode": true
}
```

The bot will:
- Connect to AAFR
- Receive events
- Log all actions
- **NOT** execute clicks/drags

### Test Individual Components

```bash
# Test position tracker
python gui_bot/position_tracker.py

# Test DOM automation (dry run)
python gui_bot/dom_automation.py

# Test event handlers
python gui_bot/event_handlers.py

# Test logger
python gui_bot/logger.py
```

### Manual Testing

1. Start AAFR in test mode: `python -m aafr.main --mode test`
2. Start GUI bot with dry run enabled
3. Verify WebSocket connection
4. Check logs in `gui_bot/logs/`

## Logs

All actions are logged to:

```
gui_bot/logs/automation_YYYYMMDD.log
```

Log contents:
- Events received
- Clicks executed
- Drags performed
- Position updates
- Errors and retries
- Performance metrics

## Troubleshooting

### Bot Cannot Connect

```
[ERROR] Cannot connect to AAFR at ws://localhost:8765
```

**Solution**: Make sure AAFR is running with `--mode live` and `gui_bot.enabled: true` in config.

### Clicks Not Working

```
[WARNING] Coordinates may be out of bounds
```

**Solution**: Re-run calibration tool: `python gui_bot/config.py`

### PyAutoGUI Not Found

```
[WARNING] pyautogui not installed
```

**Solution**: Install dependencies: `pip install -r gui_bot/requirements.txt`

### Wrong Orders Placed

**Solution**: 
1. Enable dry run mode
2. Verify DOM coordinates
3. Test with small position sizes
4. Monitor logs for coordinate issues

## Advanced Usage

### Multiple Instruments

Calibrate each symbol:

```bash
python gui_bot/config.py  # Calibrate NQ
python gui_bot/config.py  # Calibrate ES
```

Bot will automatically handle multiple symbols simultaneously.

### Custom Timing

Adjust timing for your platform performance:

- Fast computer / low latency: 50-100ms delays
- Slower system: 150-300ms delays
- High network latency: Add extra retry delay

### EVAL vs LIVE Mode

Set in AAFR config (`aafr/config.json`):

```json
"gui_bot": {
  "mode": "EVAL"  // or "LIVE"
}
```

- **EVAL**: TP3 is hard target (full exit)
- **LIVE**: TP3 trails indefinitely (runner)

## Event Types

### NEW_POSITION

```json
{
  "event": "NEW_POSITION",
  "symbol": "NQ",
  "side": "LONG",
  "entry_price": 20150.00,
  "size": 3,
  "initial_stop": 20115.50,
  "tps": [
    {"price": 20165.00, "qty": 1},
    {"price": 20175.00, "qty": 1},
    {"price": 20195.00, "qty": 1}
  ],
  "mode": "EVAL",
  "atr": 15.5
}
```

### TP_FILLED

```json
{
  "event": "TP_FILLED",
  "symbol": "NQ",
  "tp_level": 1,
  "remaining_size": 2,
  "stop_update": {
    "qty": 2,
    "price": 20150.50,
    "action": "MODIFY_IN_PLACE",
    "reason": "TP1_BE_MOVE"
  }
}
```

### STOP_UPDATE

```json
{
  "event": "STOP_UPDATE",
  "symbol": "NQ",
  "details": {
    "price": 20168.75,
    "qty": 1,
    "method": "STRUCTURE_TRAIL",
    "reason": "TP2_TRAIL"
  }
}
```

### CLOSE_TRADE

```json
{
  "event": "CLOSE_TRADE",
  "symbol": "NQ",
  "action": "CANCEL_SYMBOL_ORDERS",
  "reason": "final_exit"
}
```

## Known Limitations

- **Manual TP fill detection**: Currently, AAFR doesn't automatically detect TP fills. You may need to manually trigger TP_FILLED events or implement Tradovate API polling.
- **Cancel orders**: Cancel functionality logs action but doesn't click. Manually cancel in DOM or implement via Tradovate API.
- **Window focus**: No automatic window activation. Ensure Tradovate is visible.
- **Multi-monitor**: Coordinates are absolute screen positions. Recalibrate if moving windows between monitors.

## Future Enhancements

- [ ] Automatic TP fill detection via Tradovate API
- [ ] Window focus automation
- [ ] Relative coordinates (window-based)
- [ ] Voice/sound alerts
- [ ] Performance analytics dashboard
- [ ] Hotkey emergency controls

## Support

For issues or questions:
1. Check logs in `gui_bot/logs/`
2. Enable dry run mode for debugging
3. Re-run calibration if clicks are misaligned
4. Verify AAFR WebSocket server is running

## Warnings

⚠️ **USE AT YOUR OWN RISK**

- This bot interacts with live trading platform
- Always test in paper/demo account first
- Monitor all trades manually
- Have emergency stop procedures
- Understand all automation before use
- Check positions regularly in Tradovate

⚠️ **NOT FINANCIAL ADVICE**

This is an educational tool. Use responsibly and at your own discretion.

## License

Same as AAFR project (MIT License)

