# GUI Bot Integration Guide

Complete guide to setting up and using the AAFR GUI Bot integration.

## Quick Start

### 1. Install Dependencies

```bash
# Install AAFR dependencies (if not already done)
pip install -r requirements.txt

# Install GUI bot dependencies
pip install -r gui_bot/requirements.txt
```

Or install manually:

```bash
pip install websockets pyautogui
```

### 2. Enable GUI Bot in AAFR Config

Edit `aafr/config.json`:

```json
{
  "gui_bot": {
    "enabled": true,
    "websocket_host": "localhost",
    "websocket_port": 8765,
    "mode": "EVAL"
  }
}
```

### 3. Calibrate DOM Coordinates

Before first use, calibrate your Tradovate DOM:

```bash
python gui_bot/config.py
```

Follow the interactive prompts to map click zones for each symbol you trade.

### 4. Configure Bot Settings

Edit `gui_bot/bot_config.json`:

```json
{
  "safety": {
    "dry_run_mode": false
  }
}
```

**Note**: Keep `dry_run_mode: true` for initial testing!

### 5. Start the System

**Terminal 1 - Start AAFR:**

```bash
python -m aafr.main --mode live --symbol MNQ
```

**Terminal 2 - Start GUI Bot:**

```bash
python gui_bot/client.py
```

### 6. Open Tradovate

- Open Tradovate platform
- Display the DOM for your trading symbol (e.g., NQ)
- Position the DOM where you calibrated coordinates
- Ensure the window is visible and not minimized

## System Architecture

```
┌─────────────┐
│    AAFR     │  Detects ICC patterns
│   System    │  Calculates trade levels
└──────┬──────┘
       │ WebSocket
       │ (port 8765)
       ▼
┌─────────────┐
│  GUI Bot    │  Receives events
│   Client    │  Tracks positions
└──────┬──────┘
       │ PyAutoGUI
       │ (mouse clicks)
       ▼
┌─────────────┐
│  Tradovate  │  Executes orders
│     DOM     │  Fills orders
└─────────────┘
```

## Event Flow

### 1. New Trade Signal

1. AAFR detects ICC pattern
2. Risk validation passes
3. WebSocket broadcasts `NEW_POSITION` event
4. GUI Bot receives event
5. Bot clicks DOM to place:
   - Entry order (Limit)
   - Stop order (Stop)
   - TP1, TP2, TP3 (Limits)
6. Position tracked locally

### 2. TP1 Fills

1. (Manual notification or API polling)
2. AAFR broadcasts `TP_FILLED` event (level 1)
3. Bot receives event
4. Bot modifies stop:
   - Reduces quantity to 2
   - Drags to break-even price
5. Position updated in tracker

### 3. TP2 Fills

1. AAFR broadcasts `TP_FILLED` event (level 2)
2. Bot modifies stop:
   - Reduces quantity to 1
   - Drags to structure (swing low/high)
3. Position updated

### 4. Final Exit

1. TP3 fills or stop hits
2. AAFR broadcasts `CLOSE_TRADE` event
3. Bot cancels remaining orders
4. Position cleared from tracker

## Configuration Files

### `aafr/config.json`

Controls AAFR system settings:

```json
{
  "gui_bot": {
    "enabled": true,           // Enable WebSocket server
    "websocket_host": "localhost",
    "websocket_port": 8765,
    "mode": "EVAL"             // "EVAL" or "LIVE"
  }
}
```

- **EVAL mode**: TP3 is a hard target (full exit)
- **LIVE mode**: TP3 trails indefinitely (runner)

### `gui_bot/bot_config.json`

Controls GUI bot behavior:

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
    "dry_run_mode": false      // Set to true for testing
  },
  "dom_coordinates": {
    "NQ": { /* calibrated coords */ }
  }
}
```

## Testing

### Dry Run Mode

Always test with dry run first:

1. Set `dry_run_mode: true` in `gui_bot/bot_config.json`
2. Start AAFR and GUI bot
3. Watch console output
4. No actual clicks will be executed
5. Verify logic is correct

### Integration Test

Run the automated test suite:

```bash
python test_gui_bot_integration.py
```

This tests:
- WebSocket server
- Position tracker
- DOM automation (dry run)
- Event handlers
- Full integration flow

### Manual Testing

1. Enable dry run mode
2. Use AAFR test mode: `python -m aafr.main --mode test`
3. Verify WebSocket connection
4. Check logs in `gui_bot/logs/`
5. Review all output carefully

## Safety Features

### Pre-Execution Checks

- DOM focus validation
- Coordinate bounds checking
- Symbol verification

### Error Handling

- Retry logic (1 attempt for failed actions)
- Cancel-and-replace fallback
- Comprehensive error logging
- Graceful degradation

### Emergency Stop

- **PyAutoGUI Failsafe**: Move mouse to screen corner to abort
- **Keyboard**: Press Ctrl+C to stop bot
- **Manual Override**: Always monitor and manage positions in Tradovate

## Troubleshooting

### Bot Won't Connect

```
[ERROR] Cannot connect to AAFR at ws://localhost:8765
```

**Solutions:**
1. Ensure AAFR is running: `python -m aafr.main --mode live --symbol MNQ`
2. Check `gui_bot.enabled: true` in `aafr/config.json`
3. Verify port 8765 is not blocked by firewall
4. Check console for AAFR WebSocket startup messages

### Clicks Not Working

```
[WARNING] Coordinates may be out of bounds
```

**Solutions:**
1. Re-run calibration: `python gui_bot/config.py`
2. Ensure DOM window is in same position as calibration
3. Check DOM window is not minimized or covered
4. Verify symbol matches calibrated symbol

### Wrong Orders Placed

**Solutions:**
1. Enable dry run mode immediately
2. Review logs in `gui_bot/logs/`
3. Check DOM coordinate mapping
4. Verify tick size calculation
5. Test with smallest position size (1 contract)

### PyAutoGUI Not Found

```
[WARNING] pyautogui not installed
```

**Solution:**

```bash
pip install pyautogui
```

### WebSockets Not Found

```
[WARNING] websockets library not installed
```

**Solution:**

```bash
pip install websockets
```

## Advanced Usage

### Multiple Symbols

Calibrate each symbol:

```bash
python gui_bot/config.py  # Calibrate NQ
python gui_bot/config.py  # Calibrate ES
python gui_bot/config.py  # Calibrate GC
```

Start AAFR with multiple symbols:

```bash
python -m aafr.main --mode live --symbols MNQ MES MGC
```

Bot will handle all symbols simultaneously.

### Custom Timing

Adjust for your system performance:

```json
{
  "timing": {
    "click_delay_ms": 150,      // Slower clicks
    "drag_delay_ms": 300,        // More time before drag
    "retry_delay_ms": 1000       // Longer retry wait
  }
}
```

### Logging

All actions logged to:

```
gui_bot/logs/automation_YYYYMMDD.log
```

Review logs regularly to:
- Monitor bot performance
- Identify issues early
- Verify correct operation
- Track success rate

## Best Practices

### Before Going Live

1. ✅ Test in dry run mode extensively
2. ✅ Calibrate coordinates accurately
3. ✅ Test with paper trading account
4. ✅ Monitor several trades manually
5. ✅ Verify all clicks are correct
6. ✅ Understand emergency stop procedures
7. ✅ Have manual override ready

### During Live Trading

1. 👁️ Monitor bot console output
2. 👁️ Watch Tradovate DOM
3. 👁️ Review each trade execution
4. 👁️ Keep logs open in real-time
5. 👁️ Be ready to stop bot if needed
6. 👁️ Have manual override plan

### Risk Management

1. Start with smallest position sizes
2. Monitor first 5-10 trades closely
3. Gradually increase size as confidence builds
4. Always have stop losses in place
5. Never leave bot unattended initially
6. Set daily loss limits in AAFR config

## Known Limitations

1. **TP Fill Detection**: Currently manual. AAFR doesn't automatically detect fills. You may need to manually trigger `TP_FILLED` events or implement Tradovate API polling.

2. **Order Cancellation**: Cancel functionality logs action but doesn't execute clicks. Manually cancel in DOM or implement via Tradovate API.

3. **Window Focus**: No automatic window activation. Tradovate must be visible.

4. **Screen Resolution**: Coordinates are absolute. Recalibrate if changing monitors or resolution.

5. **Multi-Monitor**: If moving windows between monitors, recalibrate.

## Future Enhancements

Planned improvements:

- [ ] Automatic TP fill detection via Tradovate API
- [ ] Window focus automation
- [ ] Relative coordinates (window-based)
- [ ] Voice/sound alerts
- [ ] Performance dashboard
- [ ] Hotkey emergency controls
- [ ] Position reconciliation with Tradovate API

## Support

If you encounter issues:

1. Check logs: `gui_bot/logs/automation_YYYYMMDD.log`
2. Enable dry run mode for debugging
3. Re-run calibration if clicks misaligned
4. Verify AAFR WebSocket server is running
5. Review this guide thoroughly

## Warnings

⚠️ **USE AT YOUR OWN RISK**

- This bot interacts with a live trading platform
- Always test in paper/demo account first
- Monitor all trades manually
- Have emergency stop procedures ready
- Understand all automation before use
- Check positions regularly in Tradovate

⚠️ **NOT FINANCIAL ADVICE**

This is an educational tool. Use responsibly and at your own discretion.

## Summary

The AAFR GUI Bot provides automated DOM interaction for the AAFR trading system. When properly calibrated and tested, it can execute trades automatically based on AAFR signals. However, it requires careful setup, testing, and monitoring to use safely.

**Remember**: This is a tool to assist, not replace, careful trading. Always maintain oversight and be ready to intervene manually.

