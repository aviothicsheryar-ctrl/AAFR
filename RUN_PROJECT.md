# How to Run the Trading System

## Quick Start Guide

### Prerequisites
1. Python 3.7+ installed
2. All dependencies installed: `pip install -r requirements.txt`
3. Config file set up: `aafr/config.json`
4. (Optional) GUI Bot calibrated: `python -m gui_bot.config`

---

## Option 1: Run Dual Strategy System (AAFR + AJR)

### Single Terminal - Trading System Only

```bash
# From project root directory
python dual_strategy_main.py --symbols NQ
```

**Multiple instruments:**
```bash
python dual_strategy_main.py --symbols NQ ES GC CL
```

**What this does:**
- Starts both AAFR and AJR strategies
- Monitors specified instruments for trade signals
- Uses shared Execution Arbiter (prevents conflicts)
- Uses shared Risk Manager (E-Mini validation, position sizing)
- Logs signals to CSV files
- Starts WebSocket server (if enabled in config)

**Output:**
- Real-time signal detection
- Arbiter decisions (accept/reject)
- Risk calculations
- CSV logs in `logs/signals/`

---

## Option 2: Run with GUI Bot (Automated DOM Trading)

### Terminal 1 - Trading System
```bash
python dual_strategy_main.py --symbols NQ
```

### Terminal 2 - GUI Bot Client
```bash
python -m gui_bot.client
```

**What this does:**
- Terminal 1: Generates trade signals (AAFR + AJR)
- Terminal 2: Receives signals via WebSocket and executes on Tradovate DOM

**Requirements:**
- Tradovate DOM must be open and visible
- DOM coordinates must be calibrated (run `python -m gui_bot.config` first)
- WebSocket must be enabled in `aafr/config.json`:
  ```json
  {
    "gui_bot": {
      "enabled": true,
      "websocket_host": "localhost",
      "websocket_port": 8765
    }
  }
  ```

---

## Option 3: Run AAFR Only (Original System)

```bash
python -m aafr.main --mode live --symbol NQ
```

**Note:** This runs the original AAFR system separately (not integrated with AJR).

---

## Configuration

### Enable/Disable Strategies

Edit `aafr/config.json`:
```json
{
  "strategies": {
    "AAFR": {
      "enabled": true,
      "priority": 1
    },
    "AJR": {
      "enabled": true,
      "priority": 2,
      "gap_lookback_candles": 50,
      "min_gap_size_ticks": 10,
      "max_gap_age_candles": 100
    }
  }
}
```

### Enable/Disable GUI Bot

Edit `aafr/config.json`:
```json
{
  "gui_bot": {
    "enabled": true,
    "websocket_host": "localhost",
    "websocket_port": 8765,
    "mode": "EVAL"  // or "LIVE"
  }
}
```

---

## Testing

### Run Tests
```bash
python test_dual_strategy.py
```

### Test AJR Strategy Only
```bash
python -m ajr.ajr_strategy
```

---

## Troubleshooting

### Port Already in Use (WebSocket)
If you see: `[WARNING] Port 8765 already in use`

**Solution:**
```powershell
# Find process using port 8765
netstat -ano | findstr :8765

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

### GUI Bot Not Connecting
1. Check WebSocket is enabled in config
2. Verify Trading System is running first
3. Check `gui_bot/bot_config.json` has correct connection settings

### No Signals Generated
1. Check strategies are enabled in config
2. Verify instruments are in allowed list (NQ, ES, GC, CL)
3. Check API credentials (or mock data mode)
4. Review logs in `logs/signals/`

---

## File Locations

- **Main System**: `dual_strategy_main.py`
- **Config**: `aafr/config.json`
- **GUI Bot Config**: `gui_bot/bot_config.json`
- **Logs**: `logs/signals/signals_YYYYMMDD.csv`
- **GUI Bot Logs**: `gui_bot/logs/automation_YYYYMMDD.log`

---

## Example Run

```bash
# Terminal 1
D:\office projects\trading> python dual_strategy_main.py --symbols NQ ES

[SYSTEM] Dual Strategy System starting...
[SYSTEM] AAFR: enabled
[SYSTEM] AJR: enabled
[RISK] Unified Risk Manager initialized
[ARBITER] Execution Arbiter initialized
[OK] WebSocket server started on ws://localhost:8765
Monitoring NQ...
Monitoring ES...
[AJR] Strategy initialized
[GAP] Gap Tracker initialized
...
```

```bash
# Terminal 2 (if using GUI bot)
D:\office projects\trading> python -m gui_bot.client

[INFO] GUI Bot initialized
[INFO] AAFR Server: ws://localhost:8765
[OK] Connected to AAFR server
Waiting for trade signals...
```

---

## Stopping the System

Press `Ctrl+C` in the terminal running the trading system.

The system will:
- Stop monitoring
- Close WebSocket connections
- Save final logs
- Exit gracefully

