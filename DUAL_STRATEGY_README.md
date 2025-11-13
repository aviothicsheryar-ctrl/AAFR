

# Dual Strategy System - AAFR + AJR

Complete integration of AAFR (trend continuation) and AJR (gap inversion) strategies running in parallel with shared execution arbiter and GUI bot.

## Overview

This system runs two complementary trading strategies simultaneously:

- **AAFR**: Trend continuation strategy (ICC patterns)
- **AJR**: Gap inversion/reversal strategy

Both strategies:
- Share a unified execution arbiter (prevents conflicts)
- Use the same risk manager (E-Mini only, proper position sizing)
- Emit signals through the same GUI bot
- Log to CSV for analysis

## Instruments (E-Mini Only)

**ONLY these 4 instruments are allowed:**

| Instrument | Contract | Tick Size | Dollar/Tick |
|------------|----------|-----------|-------------|
| NQ | E-mini NASDAQ-100 | 0.25 | $5.00 |
| ES | E-mini S&P 500 | 0.25 | $12.50 |
| GC | Gold (100 oz) | 0.10 | $10.00 |
| CL | WTI Crude Oil (1,000 bbl) | 0.01 | $10.00 |

Any attempt to trade other instruments will be rejected.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configuration

Edit `aafr/config.json`:

```json
{
  "account": {
    "enabled_instruments": ["NQ", "ES", "GC", "CL"],
    "max_risk_usd_per_trade": 750
  },
  "arbiter": {
    "enabled": true
  },
  "strategies": {
    "AAFR": {
      "enabled": true
    },
    "AJR": {
      "enabled": true
    }
  }
}
```

### 3. Run Both Strategies

```bash
# Single instrument
python dual_strategy_main.py --symbols NQ

# Multiple instruments
python dual_strategy_main.py --symbols NQ ES GC CL
```

### 4. Start GUI Bot (Optional)

In a separate terminal:

```bash
python gui_bot/client.py
```

## Architecture

```
┌────────────┐    ┌────────────┐
│    AAFR    │    │    AJR     │
│ (ICC/CVD)  │    │ (Gap Inv)  │
└─────┬──────┘    └─────┬──────┘
      │                 │
      │   Signals       │
      └────────┬────────┘
               ▼
      ┌────────────────┐
      │   Execution    │
      │    Arbiter     │
      │ - Conflicts    │
      │ - Priority     │
      │ - Merging      │
      └────────┬───────┘
               ▼
      ┌────────────────┐
      │  Risk Manager  │
      │ - E-Mini only  │
      │ - Position size│
      │ - Loss limits  │
      └────────┬───────┘
               ▼
      ┌────────────────┐
      │  CSV Logging   │
      │  WebSocket     │
      │  GUI Bot       │
      └────────────────┘
```

## Strategy Details

### AAFR (Andrew's Automated Futures Routine)

**Pattern**: Indication-Correction-Continuation (ICC)

- Detects trend continuation setups
- Uses CVD for volume confirmation
- Calculates entry/stop/TP based on structure
- Priority during continuation hours (9:30-15:30)

**Signal Example:**
```json
{
  "strategy_id": "AAFR",
  "instrument": "NQ",
  "direction": "BUY",
  "entry_price": 20150.00,
  "stop_price": 20115.50,
  "take_profit": [20200.00, 20250.00]
}
```

### AJR (Andrew's Justified Reversal)

**Pattern**: Gap Inversion

- Detects price gaps
- Waits for price to close through far side of gap
- BUY if close above gap (after gap down)
- SELL if close below gap (after gap up)
- Stop beyond recent swing with buffer
- TPs at 1.5× and 2.5× stop distance
- Priority during reversal windows (around market open/close)

**Signal Example:**
```json
{
  "strategy_id": "AJR",
  "instrument": "ES",
  "direction": "SELL",
  "entry_price": 5348.50,
  "stop_price": 5356.75,
  "take_profit": [5328.50, 5318.25]
}
```

## Execution Arbiter

The arbiter prevents conflicting trades and manages priority:

### Rules

1. **One position per symbol max**
2. **Same direction signals**: Can merge (up to 1.5× size)
3. **Opposite directions**: Apply priority rules
   - Continuation hours (9:30-15:30): AAFR wins
   - Reversal windows (open/close): AJR wins
   - Otherwise: first signal wins

### Conflict Examples

**Scenario 1: Both Want BUY**
```
AAFR: BUY NQ @ 20150
AJR:  BUY NQ @ 20148
→ Arbiter: MERGE both signals
→ Result: BUY with better entry and larger size
```

**Scenario 2: Opposite Directions**
```
Time: 10:00 (continuation hours)
AAFR: BUY NQ @ 20150
AJR:  SELL NQ @ 20145
→ Arbiter: AAFR wins (continuation priority)
→ Result: BUY signal accepted, SELL rejected
```

## Risk Management

### Position Sizing Formula

```
contracts = floor(max_risk_usd / (stop_distance_ticks × dollar_per_tick))
```

### Examples @ $750 Risk

- **NQ**: 40-tick stop → 40 × $5 = $200/contract → 3 contracts
- **ES**: 30-tick stop → 30 × $12.50 = $375/contract → 2 contracts
- **GC**: 40-tick stop → 40 × $10 = $400/contract → 1-2 contracts
- **CL**: 30-tick stop → 30 × $10 = $300/contract → 2 contracts

### Risk Limits

- Max risk per trade: $750 (0.5%)
- Daily loss limit: $1,500
- Minimum R multiple: 1.5
- Account size: $150,000

## CSV Logging

All signals and executions are logged:

### Signals Log

```
logs/signals/signals_YYYYMMDD.csv
```

Contains:
- Strategy ID
- Instrument
- Direction
- Entry/Stop/TPs
- Notes

### Executions Log

```
logs/signals/executions_YYYYMMDD.csv
```

Contains:
- Acceptance/rejection status
- Position size
- Risk amounts
- R multiples
- Arbiter decision reason

## GUI Bot Integration

If GUI bot is enabled, trade signals are broadcast via WebSocket:

```json
{
  "event": "NEW_POSITION",
  "symbol": "NQ",
  "side": "BUY",
  "entry_price": 20150.00,
  "size": 3,
  "initial_stop": 20115.50,
  "tps": [
    {"price": 20200.00, "qty": 1},
    {"price": 20250.00, "qty": 1},
    {"price": 20300.00, "qty": 1}
  ]
}
```

The GUI bot automatically executes orders on Tradovate DOM.

## Testing

### Component Tests

```bash
# Test signal schema
python shared/signal_schema.py

# Test risk manager
python shared/unified_risk_manager.py

# Test arbiter
python shared/execution_arbiter.py

# Test AJR strategy
python ajr/ajr_strategy.py

# Test gap tracker
python ajr/gap_tracker.py
```

### Integration Test

```bash
python test_dual_strategy.py
```

This tests:
- Signal generation from both strategies
- Arbiter conflict resolution
- Risk validation
- CSV logging

## Configuration Reference

### Arbiter Settings

```json
"arbiter": {
  "enabled": true,
  "max_positions_per_symbol": 1,
  "allow_signal_merging": true,
  "max_merged_size_multiplier": 1.5,
  "continuation_hours": [[9, 30], [15, 30]],
  "reversal_windows": [[8, 30], [9, 30], [15, 30], [16, 0]]
}
```

### Strategy Settings

```json
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
```

## Command Line Options

```bash
python dual_strategy_main.py [OPTIONS]

Options:
  --symbols NQ ES GC CL    Instruments to trade (E-Mini only)
  --config PATH            Path to config file (default: aafr/config.json)
```

## Monitoring

### Console Output

The system prints:
- Strategy signals detected
- Arbiter decisions
- Risk validation
- Position updates
- Statistics

### Logs

Check these locations:
- `logs/signals/` - Signal and execution logs
- `gui_bot/logs/` - GUI bot automation logs (if enabled)

## Troubleshooting

### No Signals Generated

**Check:**
1. Strategies enabled in config?
2. Sufficient historical data (200 candles)?
3. Patterns actually present in data?

### Signals Rejected by Arbiter

**Check:**
1. Position already open for that symbol?
2. Conflicting signal has priority?
3. Risk limits exceeded?

### E-Mini Validation Errors

**Check:**
1. Only trading NQ, ES, GC, CL?
2. Instrument configured in config.json?
3. Tick sizes correct?

## Performance Metrics

After running, check:

```
[ARBITER] Statistics:
  Total signals: 45
  Accepted: 32
  Rejected: 13
  Merged: 5
  Acceptance rate: 71.1%
```

## Best Practices

1. **Start with one instrument** (NQ) to learn the system
2. **Monitor first day manually** to ensure correct operation
3. **Review CSV logs daily** to understand arbiter decisions
4. **Adjust priority windows** based on your market observations
5. **Use dry run mode** in GUI bot initially

## Known Limitations

1. **Mock data mode**: Currently uses simulated candle updates (5s intervals)
2. **No live fill detection**: GUI bot doesn't automatically detect TP fills
3. **Manual gap detection**: Gaps detected from open-to-previous-close (simplified)
4. **No state recovery**: Restart loses open position tracking

## Future Enhancements

- [ ] Live WebSocket data feed from Tradovate
- [ ] Automatic TP fill detection
- [ ] State persistence and recovery
- [ ] More sophisticated gap detection (intraday gaps)
- [ ] Performance analytics dashboard
- [ ] Multi-timeframe analysis

## Files Created

### Core Components
- `shared/signal_schema.py` - Unified signal format
- `shared/unified_risk_manager.py` - E-Mini risk management
- `shared/execution_arbiter.py` - Conflict resolution
- `shared/signal_logger.py` - CSV logging

### AJR Strategy
- `ajr/ajr_strategy.py` - Gap inversion strategy
- `ajr/gap_tracker.py` - Gap detection

### Main System
- `dual_strategy_main.py` - Main orchestrator
- `aafr/config.json` - Updated configuration

## Support

For issues:
1. Check logs in `logs/signals/`
2. Run component tests individually
3. Verify configuration settings
4. Review this README

## Warnings

⚠️ **E-Mini Trading Only**
Only NQ, ES, GC, CL are permitted. All other instruments will be rejected.

⚠️ **Risk Management**
Always monitor trades. The system enforces limits but you remain responsible.

⚠️ **Testing Required**
Test thoroughly with mock data before live trading.

## License

Same as AAFR project (MIT License)

---

**Summary**: This system successfully integrates AAFR and AJR strategies with proper conflict resolution, risk management, and E-Mini restrictions. All deliverables complete.

