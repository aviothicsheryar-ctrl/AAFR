# Quick Start Guide - Dual Strategy System (AAFR + AJR)

## 🚀 Running the System

### Step 1: Run Both Strategies Together

```bash
# Single instrument
python dual_strategy_main.py --symbols NQ

# Multiple instruments
python dual_strategy_main.py --symbols NQ ES GC CL
```

**What this does:**
- Starts AAFR strategy (ICC pattern detection)
- Starts AJR strategy (gap inversion detection)
- Both run in parallel, sharing the Execution Arbiter
- WebSocket server starts (for GUI bot connection)
- CSV logging begins

### Step 2: Start GUI Bot (Optional)

In a **separate terminal**:

```bash
python gui_bot/client.py
```

**What this does:**
- Connects to WebSocket server
- Receives trade signals from both strategies
- Executes orders on Tradovate DOM
- Tracks positions and manages stops

## 🧪 Testing

### Quick Test (All Components)

```bash
python test_dual_strategy.py
```

**Expected Output:**
```
======================================================================
                    DUAL STRATEGY SYSTEM TESTS
======================================================================
[PASS]   Signal Schema
[PASS]   Risk Manager
[PASS]   Gap Tracker
[PASS]   AJR Strategy
[PASS]   CSV Logging
[PASS]   Arbiter Conflicts
======================================================================
  TOTAL: 6/6 tests passed (100.0%)
======================================================================
```

### Test Individual Components

```bash
# Test signal format
python shared/signal_schema.py

# Test risk manager
python shared/unified_risk_manager.py

# Test arbiter
python shared/execution_arbiter.py

# Test AJR strategy
python ajr/ajr_strategy.py
```

## 📊 What You'll See

### Console Output

```
======================================================================
DUAL STRATEGY SYSTEM - AAFR + AJR
======================================================================
[SYSTEM] Initialized
[SYSTEM] AAFR: enabled
[SYSTEM] AJR: enabled
[SYSTEM] Arbiter: enabled
[SYSTEM] GUI Bot: enabled

[SYSTEM] Starting dual strategy system...
[SYSTEM] Symbols: ['NQ']
[SYSTEM] Press Ctrl+C to stop

[NQ] Starting monitoring...
[NQ] Loaded 200 historical candles

[AAFR] Signal detected: NQ BUY
[ARBITER] ACCEPTED: AAFR NQ BUY @ 20150.0, Size: 2
[WS] Emitted AAFR signal to GUI bot

[AJR] SIGNAL GENERATED: SELL NQ @ 20145.00
[ARBITER] REJECTED: Position already open for NQ
```

### CSV Logs

Check `logs/signals/` directory:
- `signals_YYYYMMDD.csv` - All signals from both strategies
- `executions_YYYYMMDD.csv` - Acceptance/rejection decisions

## ⚙️ Configuration

### Enable/Disable Strategies

Edit `aafr/config.json`:

```json
{
  "strategies": {
    "AAFR": {
      "enabled": true  // Set to false to disable
    },
    "AJR": {
      "enabled": true  // Set to false to disable
    }
  }
}
```

### Enable/Disable GUI Bot

```json
{
  "gui_bot": {
    "enabled": true  // Set to false to disable WebSocket
  }
}
```

## 🔍 Monitoring

### Check Logs

```bash
# View today's signals
cat logs/signals/signals_$(date +%Y%m%d).csv

# View today's executions
cat logs/signals/executions_$(date +%Y%m%d).csv
```

### Check GUI Bot Logs

```bash
# View automation logs
cat gui_bot/logs/automation_$(date +%Y%m%d).log
```

## 🛑 Stopping the System

Press `Ctrl+C` in the terminal running `dual_strategy_main.py`

The system will:
- Stop monitoring
- Close WebSocket connections
- Print final statistics
- Save all logs

## 📝 Example Workflow

### Full Test Run

```bash
# Terminal 1: Start system
python dual_strategy_main.py --symbols NQ

# Terminal 2: Start GUI bot (dry run mode)
# First, set dry_run_mode: true in gui_bot/bot_config.json
python gui_bot/client.py

# Watch both terminals for:
# - Signal generation
# - Arbiter decisions
# - GUI bot actions (dry run)
```

### Production Run

```bash
# Terminal 1: Start system
python dual_strategy_main.py --symbols NQ ES GC CL

# Terminal 2: Start GUI bot (live mode)
# Make sure dry_run_mode: false in gui_bot/bot_config.json
python gui_bot/client.py

# Terminal 3: Monitor logs
tail -f logs/signals/signals_*.csv
```

## ✅ Verification Checklist

Before going live:

- [ ] Both strategies enabled in config
- [ ] E-Mini instruments configured (NQ, ES, GC, CL)
- [ ] Risk limits set ($750 per trade, $1500 daily)
- [ ] GUI bot calibrated (if using)
- [ ] Dry run tested successfully
- [ ] CSV logs working
- [ ] WebSocket connection working
- [ ] All tests passing

## 🆘 Troubleshooting

### "Config file not found"
- Make sure you're in project root: `d:\office projects\trading`
- Config should be at: `aafr/config.json`

### "No signals generated"
- Check strategies are enabled
- Verify historical data loaded (200+ candles)
- Check console for pattern detection messages

### "GUI bot won't connect"
- Ensure `dual_strategy_main.py` is running first
- Check WebSocket port 8765 not blocked
- Verify `gui_bot.enabled: true` in config

### "Signals rejected"
- Check E-Mini validation (only NQ, ES, GC, CL)
- Verify risk limits not exceeded
- Check if position already open

## 📚 More Information

- Full documentation: `DUAL_STRATEGY_README.md`
- GUI bot guide: `gui_bot/README.md`
- Integration guide: `INTEGRATION_GUIDE.md`

