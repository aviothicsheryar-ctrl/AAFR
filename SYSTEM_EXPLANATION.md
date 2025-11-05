# What is the AAFR Trading System?

## Simple Explanation for Non-Technical People

Think of AAFR (Andrew's Automated Futures Routine) as a **smart trading assistant** that watches the stock market charts for you. Just like a weather app tells you when it's going to rain, this system tells you when there might be a good trading opportunity.

Instead of staring at charts all day, the system:
- **Watches** the price movements
- **Finds** specific patterns that might lead to profitable trades
- **Calculates** how much to risk on each trade
- **Tells you** exactly when to enter, where to set your stop loss, and where to take profit

---

## What is the Purpose?

The purpose of this system is to:

1. **Automate Pattern Detection**: Find trading opportunities automatically without you having to watch charts manually
2. **Manage Risk**: Make sure you never risk too much money on a single trade
3. **Calculate Position Sizes**: Tell you exactly how many contracts to buy/sell
4. **Generate Trade Signals**: Give you clear instructions on when to enter and exit trades

---

## How It Works (Simple Explanation)

### Step 1: Load Price Data
The system needs historical price data to analyze. It reads:
- **Open** price (where the candle started)
- **High** price (highest point reached)
- **Low** price (lowest point reached)
- **Close** price (where the candle ended)
- **Volume** (how many trades happened)

Think of each candle as a snapshot of what happened in a 5-minute period (or whatever time frame you choose).

### Step 2: Detect ICC Patterns
The system looks for a specific pattern called **ICC** (Indication-Correction-Continuation):
- **Indication**: A big move in one direction (like a strong push up or down)
- **Correction**: A pullback (like taking a breath before continuing)
- **Continuation**: A confirmation that the move is continuing

Think of it like a wave: big push → small pullback → continues in the same direction.

### Step 3: Validate with CVD
The system checks if the **volume** (buying vs selling pressure) confirms the pattern. This is like checking if there are more buyers than sellers during the move.

### Step 4: Risk Management
Before giving you a trade signal, the system makes sure:
- You're not risking too much money (max 1% of your account per trade)
- The potential reward is at least 2x the risk (R multiple)
- The position size is calculated correctly

### Step 5: Generate Trade Signal
If everything checks out, the system gives you:
- **Entry price**: Where to enter the trade
- **Stop loss**: Where to exit if the trade goes wrong (to limit losses)
- **Take profit**: Where to exit if the trade goes right (to lock in profits)
- **Position size**: How many contracts to trade
- **Risk amount**: How much money you're risking

---

## Trading Concepts Explained

### 1. ICC Pattern (Indication-Correction-Continuation)

**What it is**: A 3-phase pattern that shows a strong move is likely to continue.

**Phase 1 - Indication**: 
- A large, impulsive price move
- Usually breaks through previous highs/lows
- Shows strong buying or selling pressure
- Like a "declaration" of intent

**Phase 2 - Correction**:
- Price pulls back (retraces) into a "value zone"
- This is where smart money might enter
- The pullback is normal and expected
- Like "taking a breath" before continuing

**Phase 3 - Continuation**:
- Price resumes in the original direction
- Confirms the trend is still valid
- This is the entry signal
- Like "continuing the journey"

**Why it works**: This pattern shows that after a strong move, price pulled back (creating an opportunity), and then continued in the original direction (confirming the trend is still alive).

### 2. CVD (Cumulative Volume Delta)

**What it is**: A measure of buying vs selling pressure over time.

**Simple explanation**: 
- Every trade has a buyer and a seller
- But we can tell if the buyer was more aggressive (buying at higher prices) or the seller was more aggressive (selling at lower prices)
- CVD tracks this imbalance

**How it's calculated**:
```
CVD = Sum of all (Buy Volume - Sell Volume)
```

**Example**:
- Candle 1: Buy volume = 6000, Sell volume = 4000 → Delta = +2000
- Candle 2: Buy volume = 5500, Sell volume = 4500 → Delta = +1000
- CVD = 2000 + 1000 = 3000 (accumulating buying pressure)

**Why it matters**: 
- If price is going up but CVD is going down → **Divergence** (warning sign)
- If price and CVD both going up → **Alignment** (confirms the move)

### 3. ATR (Average True Range)

**What it is**: A measure of how volatile (active) the market is.

**Simple explanation**: 
- Some days the market moves a lot (high volatility)
- Some days it moves little (low volatility)
- ATR tells you how much the market typically moves

**How it's calculated**:
```
True Range = Maximum of:
1. High - Low (the candle's range)
2. High - Previous Close (gap up)
3. Previous Close - Low (gap down)

ATR = Average of True Range over 14 periods
```

**Why it matters**: 
- Used to set stop losses (more volatile = wider stops)
- Helps determine if a move is "big enough" to be significant
- Prevents placing stops too close (which would get hit by normal market noise)

### 4. Risk Management

**What it is**: Rules to protect your account from large losses.

**Key principles**:

1. **Never risk more than 1% per trade**
   - If you have $150,000, max risk = $1,500 per trade
   - This means even if you lose 10 trades in a row, you'd only lose 10% of your account

2. **Daily Loss Limit**
   - Stop trading if you lose $1,500 in a day
   - Prevents revenge trading and emotional decisions

3. **Minimum R Multiple**
   - Only take trades where potential reward is at least 2x the risk
   - Example: Risk $100 to make $200+ (R = 2.0)
   - Preferred: Risk $100 to make $300+ (R = 3.0)

4. **Position Sizing**
   - The bigger the stop distance, the smaller the position size
   - This keeps your dollar risk constant regardless of where you place the stop

**Why it matters**: 
- Most traders fail because of poor risk management, not bad entries
- Protecting capital is more important than making profits
- You can be wrong 50% of the time and still be profitable with good risk management

### 5. Position Sizing

**What it is**: Calculating exactly how many contracts to trade based on your risk.

**The formula**:
```
Position Size = (Max Risk Amount) / (Stop Distance × Tick Value)
```

**Example**:
- Account: $150,000
- Max risk: 0.5% = $750
- Entry: 18000
- Stop: 17950
- Stop distance: 50 points
- Tick value: $0.50 per point (for MNQ)

Position Size = $750 / (50 × $0.50) = $750 / $25 = 30 contracts

**Why it matters**: 
- Ensures you always risk the same dollar amount
- Prevents over-trading (too many contracts)
- Prevents under-trading (too few contracts)
- Makes your risk predictable and manageable

### 6. R Multiple

**What it is**: A way to measure risk vs reward.

**The formula**:
```
R = (Take Profit - Entry) / (Entry - Stop Loss)
```

**Example (LONG trade)**:
- Entry: 18000
- Stop Loss: 17950 (risk 50 points)
- Take Profit: 18150 (reward 150 points)
- R = 150 / 50 = 3.0

This means: "For every $1 risked, I can make $3"

**Why it matters**:
- If you win 40% of trades with R=3.0, you're profitable
- Example: 10 trades, 4 wins, 6 losses
  - 4 wins × 3R = +12R
  - 6 losses × 1R = -6R
  - Net: +6R (profitable!)

- Higher R multiple = better win rate needed
- Lower R multiple = need more wins

---

## Formulas Used in the System

### 1. ATR (Average True Range) Calculation

```
Step 1: Calculate True Range for each candle
True Range = max(
    High - Low,
    abs(High - Previous Close),
    abs(Low - Previous Close)
)

Step 2: Calculate Average
ATR = Sum of last 14 True Ranges / 14
```

**Example**:
- Candle 1: High=18010, Low=18000, PrevClose=18005
- TR = max(10, 5, 5) = 10
- Repeat for 14 candles
- ATR = Average of these 14 values

### 2. CVD (Cumulative Volume Delta) Calculation

```
For each candle:
1. Determine Buy Volume and Sell Volume
   - If close > open: Mostly buying (more buy volume)
   - If close < open: Mostly selling (more sell volume)

2. Calculate Delta
   Volume Delta = Buy Volume - Sell Volume

3. Accumulate
   CVD = Previous CVD + Current Volume Delta
```

**Example**:
- Candle 1: Buy=6000, Sell=4000 → Delta=2000, CVD=2000
- Candle 2: Buy=5500, Sell=4500 → Delta=1000, CVD=3000
- Candle 3: Buy=4000, Sell=6000 → Delta=-2000, CVD=1000

### 3. Position Sizing Formula

```
Position Size = (Max Risk Amount) / (Stop Distance × Tick Value)

Where:
- Max Risk Amount = Account Size × Risk Percentage
- Stop Distance = |Entry Price - Stop Loss Price|
- Tick Value = Dollar value per price point
```

**Example**:
- Account: $150,000
- Risk: 0.5% = $750
- Entry: 18000
- Stop: 17950
- Stop Distance: 50 points
- Tick Value: $0.50

Position Size = $750 / (50 × $0.50) = $750 / $25 = 30 contracts

### 4. R Multiple Calculation

```
For LONG trades:
R = (Take Profit - Entry) / (Entry - Stop Loss)

For SHORT trades:
R = (Entry - Take Profit) / (Stop Loss - Entry)
```

**Example (LONG)**:
- Entry: 18000
- Stop: 17950 (risk = 50 points)
- TP: 18150 (reward = 150 points)
- R = 150 / 50 = 3.0

**Example (SHORT)**:
- Entry: 18000
- Stop: 18050 (risk = 50 points)
- TP: 17850 (reward = 150 points)
- R = 150 / 50 = 3.0

### 5. Dollar Risk Calculation

```
Dollar Risk = Position Size × Stop Distance × Tick Value
```

**Example**:
- Position Size: 4 contracts
- Stop Distance: 50 points
- Tick Value: $0.50 per point
- Dollar Risk = 4 × 50 × $0.50 = $100

### 6. Risk Percentage Calculation

```
Risk Percentage = (Dollar Risk / Account Size) × 100
```

**Example**:
- Dollar Risk: $750
- Account Size: $150,000
- Risk Percentage = ($750 / $150,000) × 100 = 0.5%

### 7. Displacement Detection

```
Displacement = Large body size relative to ATR

If |Close - Open| ≥ (ATR × 1.5):
    Displacement detected
```

**Example**:
- ATR = 20 points
- Candle body = 30 points
- 30 ≥ (20 × 1.5) = 30 ≥ 30 → Displacement detected ✓

---

## What the System Does

### Input
- Price data (OHLCV) from CSV/JSON file or API
- Configuration settings (account size, risk parameters, trading symbol)

### Process
1. **Loads** price data and validates it
2. **Detects** ICC patterns in the data
3. **Validates** pattern with CVD (volume analysis)
4. **Calculates** entry, stop, and take profit levels
5. **Applies** risk management rules
6. **Calculates** position size based on risk
7. **Validates** all 5 conditions are met
8. **Generates** trade signal if valid

### Output
- **Trade Signal**: Formatted output showing entry, stop, TP, R multiple, position size, and risk
- **CSV Log**: All trade signals logged to `logs/trades/trades_YYYYMMDD.csv` for review

**Example Output**:
```
LONG MNQ @ 17880.00 | SL 17803.12 | TP1 18110.64 | R=3.0 | Size: 4 MNQ | Risk $615.04 (0.4% of 150K)
```

This means:
- **Direction**: LONG (buy)
- **Symbol**: MNQ (Micro E-mini NASDAQ-100)
- **Entry**: 17880.00
- **Stop Loss**: 17803.12 (if price goes here, exit to limit loss)
- **Take Profit**: 18110.64 (if price goes here, exit to lock profit)
- **R Multiple**: 3.0 (risk $1 to make $3)
- **Position Size**: 4 contracts
- **Dollar Risk**: $615.04
- **Risk Percentage**: 0.4% of $150,000 account

---

## System Architecture (How It's Built)

### Main Components

1. **ICC Module** (`icc_module.py`)
   - Detects Indication-Correction-Continuation patterns
   - Calculates entry, stop, and take profit levels
   - Validates all 5 setup conditions

2. **CVD Module** (`cvd_module.py`)
   - Calculates Cumulative Volume Delta
   - Detects price/volume divergences
   - Validates CVD alignment during each ICC phase

3. **Risk Engine** (`risk_engine.py`)
   - Manages position sizing
   - Enforces risk limits (0.5-1% per trade)
   - Validates trade setups meet risk criteria
   - Tracks daily losses

4. **Tradovate API** (`tradovate_api.py`)
   - Fetches market data from Tradovate broker
   - Handles authentication
   - Falls back to mock data if API unavailable

5. **Backtester** (`backtester.py`)
   - Runs historical backtests
   - Calculates performance metrics (win rate, avg R, drawdown)
   - Tracks equity curve

6. **Main System** (`main.py`)
   - Orchestrates all modules
   - Handles user commands
   - Manages data flow between components

---

## Example Workflow (Step by Step)

### Scenario: Bullish ICC Pattern Detected

**Step 1: Indication Detected**
- Large bullish candle appears (60 point move)
- High volume (30,000 contracts)
- CVD increases (buying pressure)
- System identifies this as "Indication" phase

**Step 2: Correction Identified**
- Price pulls back into value zone
- 5 candles of correction
- CVD neutralizes (volume balances)
- System identifies this as "Correction" phase

**Step 3: Continuation Confirmed**
- Bullish confirmation candle appears
- CVD resumes upward trend
- System identifies this as "Continuation" phase
- Complete ICC pattern detected!

**Step 4: Trade Levels Calculated**
- Entry: 17880.00 (continuation candle close)
- Stop: 17803.12 (below correction low with buffer)
- Take Profit: 18110.64 (3R target)
- R Multiple: 3.0 (calculated)

**Step 5: Risk Validation**
- Position size calculated: 4 contracts
- Dollar risk: $615.04
- Risk percentage: 0.41% (within 0.5-1% limit)
- R multiple: 3.0 (meets 2.0 minimum)
- All 5 conditions validated ✓

**Step 6: Trade Signal Generated**
- Output displayed to user
- Signal logged to CSV file
- Ready for execution (if desired)

---

## Key Features

✅ **Automatic Pattern Detection**: Finds ICC patterns automatically  
✅ **Risk Management**: Limits risk to 0.5-1% per trade  
✅ **Position Sizing**: Calculates exact contract size based on risk  
✅ **CVD Validation**: Confirms patterns with volume analysis  
✅ **Trade Logging**: Records all signals for review and analysis  
✅ **Backtesting**: Tests strategy on historical data  
✅ **Flexible Data Input**: Works with CSV/JSON files or API data  

---

## Important Notes

⚠️ **This system is for educational and testing purposes only**

- Not financial advice
- Test thoroughly before live trading
- Monitor all trades manually
- Risk management is critical
- Past performance doesn't guarantee future results
- Market conditions change, patterns may not always appear

---

## Summary

The AAFR Trading System is an **automated trading assistant** that:

1. **Analyzes** price charts to find ICC (Indication-Correction-Continuation) patterns
2. **Validates** patterns using CVD (Cumulative Volume Delta) to confirm buying/selling pressure
3. **Manages risk** by limiting position size and dollar risk per trade
4. **Generates** trade signals with specific entry, stop loss, and take profit levels
5. **Logs** all signals for review and performance analysis

It uses proven trading concepts like:
- **ICC Patterns**: Three-phase pattern showing trend continuation
- **CVD**: Volume analysis to confirm price moves
- **ATR**: Volatility measurement for stop placement
- **Risk Management**: Position sizing and risk limits
- **R Multiple**: Risk/reward ratio calculation

The system helps traders identify high-probability trading opportunities while maintaining strict risk management to protect their capital.

---

## Understanding the Output

When you see a trade signal like:
```
LONG MNQ @ 17880.00 | SL 17803.12 | TP1 18110.64 | R=3.0 | Size: 4 MNQ | Risk $615.04 (0.4% of 150K)
```

**What it means in plain English**:
- **Buy** 4 contracts of MNQ
- **Enter** when price reaches 17880.00
- **Exit with loss** if price drops to 17803.12 (you'll lose $615.04)
- **Exit with profit** if price reaches 18110.64 (you'll make $1,845.12)
- **Risk/Reward**: You're risking $615 to make $1,845 (3x your risk)
- **Risk**: Only 0.4% of your $150,000 account

This is a **high-quality trade setup** because:
- Clear pattern (ICC)
- Volume confirms (CVD)
- Good risk/reward (3R)
- Small risk percentage (0.4%)
- All 5 validation conditions met

---

## Conclusion

The AAFR system automates the process of finding trading opportunities based on proven patterns while maintaining strict risk management. It does the heavy lifting of pattern detection, risk calculation, and signal generation, allowing you to focus on execution and trade management.

Remember: **The system is a tool, not a guarantee**. Always use proper risk management, test thoroughly, and never risk more than you can afford to lose.

