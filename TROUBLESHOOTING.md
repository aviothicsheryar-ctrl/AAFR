# Troubleshooting Guide

## Common Errors and Solutions

### Error 1: WebSocket Port Already in Use

**Error Message:**
```
[Errno 10048] error while attempting to bind on address ('127.0.0.1', 8765): 
only one usage of each socket address (protocol/network address/port) is normally permitted
```

**What it means:**
- Port 8765 is already being used by another process
- Usually another instance of the system or GUI bot

**Solutions:**

#### Option A: Find and Close the Process

```powershell
# Find what's using port 8765
netstat -ano | findstr :8765

# You'll see a PID (Process ID), then:
tasklist | findstr <PID>

# Kill the process (replace <PID> with actual number)
taskkill /PID <PID> /F
```

#### Option B: Change WebSocket Port

Edit `aafr/config.json`:

```json
{
  "gui_bot": {
    "enabled": true,
    "websocket_host": "localhost",
    "websocket_port": 8766  // Change to different port
  }
}
```

Also update `gui_bot/bot_config.json`:

```json
{
  "aafr_connection": {
    "host": "localhost",
    "port": 8766  // Match the new port
  }
}
```

#### Option C: Disable WebSocket (Continue Without GUI Bot)

Edit `aafr/config.json`:

```json
{
  "gui_bot": {
    "enabled": false  // Disable WebSocket
  }
}
```

The system will continue running, but GUI bot won't connect.

**Note:** The system now handles this gracefully - it will continue running even if WebSocket fails to start.

---

### Error 2: API 404 Error

**Error Message:**
```
[ERROR] API request failed: 404 Client Error: Not Found for url: 
https://demo.tradovateapi.com/v1/chart/history
Failed to fetch historical data, using mock data for NQ
```

**What it means:**
- Tradovate API endpoint not found or changed
- System automatically falls back to mock data

**Solutions:**

#### Option A: This is Normal (Mock Data Mode)
- The system will use mock/simulated data
- Strategies will still work and generate signals
- Perfect for testing

#### Option B: Fix API Endpoint (If You Have Real Credentials)
- Check Tradovate API documentation for correct endpoint
- Verify your API credentials in `aafr/config.json`
- Ensure you're using the correct environment (demo vs live)

**Note:** Mock data mode is fine for testing. The system will work normally.

---

### Error 3: Config File Not Found

**Error Message:**
```
FileNotFoundError: Config file not found: D:\office projects\trading\aafr\aafr\config.json
```

**Solution:**
- Make sure you're in the project root: `d:\office projects\trading`
- Config should be at: `aafr/config.json`
- Don't pass `"aafr/config.json"` - just use `"config.json"` (it's relative to aafr directory)

---

### Error 4: No Signals Generated

**Symptoms:**
- System runs but no trade signals appear

**Check:**
1. Strategies enabled in config?
   ```json
   "strategies": {
     "AAFR": { "enabled": true },
     "AJR": { "enabled": true }
   }
   ```

2. Sufficient historical data?
   - Need 200+ candles per instrument
   - Check console: `[NQ] Loaded 200 historical candles`

3. Patterns actually present?
   - AAFR needs ICC patterns
   - AJR needs gap inversions
   - May not appear in every dataset

---

### Error 5: Signals Rejected by Arbiter

**Symptoms:**
- Signals generated but rejected

**Common Reasons:**
1. **Position already open** - One position per symbol max
2. **Conflicting signals** - Opposite directions, priority rules apply
3. **Risk limits exceeded** - Daily loss limit reached
4. **Invalid instrument** - Only NQ, ES, GC, CL allowed

**Check logs:**
```bash
cat logs/signals/executions_*.csv
```

Look for "REJECTED" status and reason column.

---

### Error 6: GUI Bot Won't Connect

**Symptoms:**
- GUI bot can't connect to WebSocket

**Check:**
1. Is `dual_strategy_main.py` running?
2. Is WebSocket server started? (Check console for `[OK] WebSocket server started`)
3. Port 8765 not blocked by firewall?
4. Config matches? (`gui_bot.websocket_port` in both configs)

---

## Quick Fixes

### Kill Process Using Port 8765

```powershell
# Find PID
netstat -ano | findstr :8765

# Kill it (replace <PID>)
taskkill /PID <PID> /F
```

### Disable WebSocket Temporarily

```json
// In aafr/config.json
{
  "gui_bot": {
    "enabled": false
  }
}
```

### Use Different Port

```json
// In aafr/config.json
{
  "gui_bot": {
    "websocket_port": 8766
  }
}

// In gui_bot/bot_config.json
{
  "aafr_connection": {
    "port": 8766
  }
}
```

### Reset Daily Counters

If daily loss limit reached, restart the system (counters reset on startup).

---

## System Status Check

Run this to verify everything:

```bash
# 1. Test all components
python test_dual_strategy.py

# 2. Check config
python -c "from aafr.utils import load_config; import json; print(json.dumps(load_config('config.json'), indent=2))"

# 3. Check if port is free
netstat -ano | findstr :8765
```

---

## Getting Help

1. Check logs: `logs/signals/` and `gui_bot/logs/`
2. Run tests: `python test_dual_strategy.py`
3. Check console output for specific error messages
4. Verify configuration files are correct

