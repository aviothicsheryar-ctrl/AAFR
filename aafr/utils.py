"""
Utility functions for the AAFR trading system.
Includes helpers for data validation, logging, and mock data generation.
"""

import json
import os
import csv
import random
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path


def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    """
    Load configuration from JSON file.
    
    Args:
        config_path: Path to config.json file (relative to aafr directory)
    
    Returns:
        Configuration dictionary
    
    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file is malformed
    """
    # Get absolute path to config file
    base_dir = Path(__file__).parent
    full_path = base_dir / config_path
    
    if not full_path.exists():
        raise FileNotFoundError(f"Config file not found: {full_path}")
    
    with open(full_path, 'r') as f:
        return json.load(f)


def calculate_atr(highs: List[float], lows: List[float], 
                  closes: List[float], period: int = 14) -> Optional[float]:
    """
    Calculate Average True Range (ATR) for volatility-based stops.
    
    Args:
        highs: List of high prices
        lows: List of low prices
        closes: List of closing prices
        period: ATR calculation period (default 14)
    
    Returns:
        ATR value or None if insufficient data
    """
    if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
        return None
    
    true_ranges = []
    for i in range(1, len(closes)):
        tr1 = highs[i] - lows[i]
        tr2 = abs(highs[i] - closes[i-1])
        tr3 = abs(lows[i] - closes[i-1])
        true_ranges.append(max(tr1, tr2, tr3))
    
    # Calculate ATR as simple moving average of true ranges
    if len(true_ranges) < period:
        return None
    
    atr = sum(true_ranges[-period:]) / period
    return atr


def detect_displacement(candles: List[Dict], threshold_multiplier: float = 1.5) -> bool:
    """
    Detect if a candle represents displacement (impulsive move).
    
    Args:
        candles: List of candle dictionaries with 'high', 'low', 'open', 'close', 'volume'
        threshold_multiplier: Multiplier for ATR-based displacement threshold
    
    Returns:
        True if displacement detected on most recent candle
    """
    if len(candles) < 15:
        return False
    
    # Extract price data for ATR calculation
    highs = [c['high'] for c in candles]
    lows = [c['low'] for c in candles]
    closes = [c['close'] for c in candles]
    
    atr = calculate_atr(highs, lows, closes)
    if atr is None:
        return False
    
    # Check current candle vs previous range
    current = candles[-1]
    prev_close = candles[-2]['close']
    
    body_size = abs(current['close'] - current['open'])
    
    # Displacement: large body relative to ATR
    return body_size >= atr * threshold_multiplier


def log_trade_signal(signal: Dict[str, Any], log_dir: str = "logs/trades") -> None:
    """
    Log trade signal to CSV file with ISO format timestamps.
    
    Args:
        signal: Dictionary containing trade signal details
        log_dir: Directory to save log files
    """
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"trades_{datetime.now().strftime('%Y%m%d')}.csv")
    
    # Field names for CSV
    fieldnames = [
        'timestamp', 'symbol', 'direction', 'entry', 'stop_loss', 
        'take_profit', 'r_multiple', 'position_size', 'dollar_risk', 
        'risk_percent', 'status', 'result'
    ]
    
    # Check if file exists to determine if we need to write headers
    file_exists = os.path.exists(log_file)
    
    with open(log_file, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        # Ensure all fields are present and format timestamp
        row = {field: signal.get(field, '') for field in fieldnames}
        
        # Format timestamp if it's a datetime object
        if 'timestamp' in row and isinstance(row['timestamp'], datetime):
            row['timestamp'] = get_formatted_timestamp(row['timestamp'])
        elif 'timestamp' not in row or not row['timestamp']:
            row['timestamp'] = get_formatted_timestamp()
        
        writer.writerow(row)


def format_trade_output(signal: Dict[str, Any]) -> str:
    """
    Format trade signal for console output.
    
    Args:
        signal: Trade signal dictionary
    
    Returns:
        Formatted string for printing
    """
    direction = signal.get('direction', 'UNKNOWN')
    symbol = signal.get('symbol', 'UNKNOWN')
    entry = signal.get('entry', 0)
    stop = signal.get('stop_loss', 0)
    tp1 = signal.get('take_profit', 0)
    r_multiple = signal.get('r_multiple', 0)
    size = signal.get('position_size', 0)
    risk = signal.get('dollar_risk', 0)
    risk_pct = signal.get('risk_percent', 0)
    
    return (f"{direction} {symbol} @ {entry:.2f} | "
            f"SL {stop:.2f} | TP1 {tp1:.2f} | R={r_multiple:.1f} | "
            f"Size: {size} {symbol} | Risk ${risk:.2f} ({risk_pct:.1f}% of 150K)")


def generate_mock_candles(count: int = 100, symbol: str = "MNQ") -> List[Dict]:
    """
    Generate mock candle data for testing when API is unavailable.
    
    Args:
        count: Number of candles to generate
        symbol: Trading symbol
    
    Returns:
        List of candle dictionaries
    """
    # Base price for different instruments
    base_prices = {
        "MNQ": 18000.0,
        "MES": 4500.0,
        "MGC": 2000.0,
        "MCL": 75.0,
        "MYM": 35000.0
    }
    
    base_price = base_prices.get(symbol, 100.0)
    candles = []
    
    current_price = base_price
    
    for i in range(count):
        # Generate realistic OHLC with some trend
        volatility = random.uniform(5, 30)
        trend = random.uniform(-10, 10) * (i / count)  # Gentle trend
        
        open_price = current_price
        high = open_price + random.uniform(0, volatility)
        low = open_price - random.uniform(0, volatility)
        close = open_price + trend + random.uniform(-volatility/2, volatility/2)
        
        # Ensure OHLC logic is maintained
        high = max(high, open_price, close)
        low = min(low, open_price, close)
        
        volume = random.randint(1000, 10000)
        
        candles.append({
            'timestamp': i,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume,
            'symbol': symbol
        })
        
        current_price = close
    
    return candles


def get_instrument_volatility_profile(symbol: str) -> Dict[str, float]:
    """
    Get volatility profile for a specific instrument.
    
    Args:
        symbol: Trading symbol
    
    Returns:
        Dictionary with volatility parameters
    """
    profiles = {
        "MNQ": {
            "base_volatility": 15.0,  # Points
            "volatility_range": (10.0, 35.0),
            "trend_strength": 0.3,  # Multiplier for trend component
            "volume_base": 5000,
            "volume_range": (2000, 15000)
        },
        "MES": {
            "base_volatility": 8.0,
            "volatility_range": (5.0, 20.0),
            "trend_strength": 0.3,
            "volume_base": 6000,
            "volume_range": (2500, 18000)
        },
        "MGC": {
            "base_volatility": 5.0,
            "volatility_range": (3.0, 12.0),
            "trend_strength": 0.4,
            "volume_base": 4000,
            "volume_range": (1500, 12000)
        },
        "MCL": {
            "base_volatility": 0.5,
            "volatility_range": (0.2, 1.2),
            "trend_strength": 0.5,
            "volume_base": 3500,
            "volume_range": (1200, 10000)
        },
        "MYM": {
            "base_volatility": 25.0,
            "volatility_range": (15.0, 50.0),
            "trend_strength": 0.3,
            "volume_base": 4500,
            "volume_range": (1800, 14000)
        }
    }
    
    return profiles.get(symbol, {
        "base_volatility": 10.0,
        "volatility_range": (5.0, 25.0),
        "trend_strength": 0.3,
        "volume_base": 5000,
        "volume_range": (2000, 12000)
    })


def generate_mock_candles_for_period(
    start_date: datetime,
    end_date: datetime,
    symbol: str = "MNQ",
    interval_minutes: int = 5
) -> List[Dict]:
    """
    Generate mock candle data for a specific date period.
    
    Simulates realistic market patterns including:
    - Intraday volatility cycles
    - Weekly patterns (higher volume on certain days)
    - Trend simulation for longer periods
    - Market hours awareness (simulated)
    
    Args:
        start_date: Start date for data generation
        end_date: End date for data generation
        symbol: Trading symbol
        interval_minutes: Candle interval in minutes (default: 5 minutes)
    
    Returns:
        List of candle dictionaries with timestamps
    """
    # Base prices for different instruments
    base_prices = {
        "MNQ": 18000.0,
        "MES": 4500.0,
        "MGC": 2000.0,
        "MCL": 75.0,
        "MYM": 35000.0
    }
    
    base_price = base_prices.get(symbol, 100.0)
    profile = get_instrument_volatility_profile(symbol)
    
    candles = []
    current_time = start_date
    current_price = base_price
    
    # Calculate total candles needed
    total_seconds = (end_date - start_date).total_seconds()
    total_candles = int(total_seconds / (interval_minutes * 60))
    
    # Long-term trend direction (subtle)
    long_term_trend = random.uniform(-0.5, 0.5)  # Small daily trend
    trend_accumulator = 0.0
    
    # Days counter for weekly patterns
    day_counter = 0
    
    while current_time < end_date:
        # Calculate day of week (0 = Monday, 6 = Sunday)
        day_of_week = current_time.weekday()
        
        # Weekly pattern: Higher volatility on Monday/Wednesday/Friday
        if day_of_week in [0, 2, 4]:  # Mon, Wed, Fri
            volatility_multiplier = 1.2
            volume_multiplier = 1.3
        elif day_of_week == 5:  # Saturday (lower activity)
            volatility_multiplier = 0.6
            volume_multiplier = 0.5
        elif day_of_week == 6:  # Sunday (minimal activity)
            volatility_multiplier = 0.4
            volume_multiplier = 0.3
        else:  # Tuesday, Thursday
            volatility_multiplier = 1.0
            volume_multiplier = 1.0
        
        # Intraday pattern: Higher volatility during "market hours" (9 AM - 4 PM)
        hour = current_time.hour
        if 9 <= hour < 16:  # Market hours
            intraday_multiplier = 1.0 + random.uniform(0.1, 0.3)
        else:  # After hours
            intraday_multiplier = 0.5 + random.uniform(0.0, 0.2)
        
        # Calculate volatility with multipliers
        base_vol = profile["base_volatility"]
        volatility = base_vol * volatility_multiplier * intraday_multiplier
        volatility = random.uniform(
            profile["volatility_range"][0],
            profile["volatility_range"][1]
        ) * volatility_multiplier * intraday_multiplier
        
        # Long-term trend component (accumulates over days)
        trend_accumulator += long_term_trend * profile["trend_strength"]
        short_term_trend = random.uniform(-volatility * 0.3, volatility * 0.3)
        trend = trend_accumulator + short_term_trend
        
        # Generate OHLC
        open_price = current_price
        
        # Random walk with trend
        price_change = trend + random.uniform(-volatility, volatility)
        close = open_price + price_change
        
        # High and low with some randomness
        high = max(open_price, close) + random.uniform(0, volatility * 0.5)
        low = min(open_price, close) - random.uniform(0, volatility * 0.5)
        
        # Ensure OHLC logic
        high = max(high, open_price, close)
        low = min(low, open_price, close)
        
        # Volume calculation
        base_volume = profile["volume_base"]
        volume = int(base_volume * volume_multiplier * intraday_multiplier)
        volume = random.randint(
            int(profile["volume_range"][0] * volume_multiplier),
            int(profile["volume_range"][1] * volume_multiplier)
        )
        
        # Add some correlation: higher volume on larger moves
        move_size = abs(close - open_price)
        if move_size > volatility * 0.7:
            volume = int(volume * 1.2)
        
        candles.append({
            'timestamp': int(current_time.timestamp()),
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close, 2),
            'volume': volume,
            'symbol': symbol
        })
        
        current_price = close
        current_time += timedelta(minutes=interval_minutes)
        
        # Reset trend accumulator every week (prevents drift)
        day_counter += 1
        if day_counter >= (7 * 24 * 60 / interval_minutes):  # Approx 1 week
            trend_accumulator = 0.0
            day_counter = 0
            # Slight trend adjustment weekly
            long_term_trend = random.uniform(-0.5, 0.5)
    
    return candles


def get_formatted_timestamp(dt: Optional[datetime] = None) -> str:
    """
    Get formatted timestamp in ISO format.
    
    Args:
        dt: Optional datetime object (defaults to now)
    
    Returns:
        Formatted timestamp string (YYYY-MM-DD HH:MM:SS.microseconds)
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime('%Y-%m-%d %H:%M:%S.%f')


def generate_mock_volume_data(candles: List[Dict], bullish_ratio: float = 0.52) -> List[int]:
    """
    Generate mock buy/sell volume split for CVD calculation.
    
    Args:
        candles: List of candle dictionaries
        bullish_ratio: Ratio of buy volume to total volume (default 52%)
    
    Returns:
        List of CVD values
    """
    cvd = []
    cumulative = 0
    
    for candle in candles:
        # Split volume based on candle direction
        if candle['close'] >= candle['open']:
            # Bullish candle
            buy_vol = int(candle['volume'] * bullish_ratio)
        else:
            # Bearish candle
            buy_vol = int(candle['volume'] * (1 - bullish_ratio))
        
        sell_vol = candle['volume'] - buy_vol
        delta = buy_vol - sell_vol
        cumulative += delta
        cvd.append(cumulative)
    
    return cvd


def load_candles_from_csv(csv_path: str, symbol: str = "MNQ") -> List[Dict]:
    """
    Load candle data from CSV file.
    
    Expected CSV format:
    timestamp,open,high,low,close,volume
    0,18000.0,18005.0,17995.0,18003.0,5000
    1,18003.0,18010.0,18000.0,18008.0,6000
    ...
    
    Or with headers:
    timestamp,open,high,low,close,volume
    ...
    
    Args:
        csv_path: Path to CSV file
        symbol: Trading symbol (default: MNQ)
    
    Returns:
        List of candle dictionaries
    
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If CSV format is invalid
    """
    candles = []
    csv_path = Path(csv_path)
    
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    with open(csv_path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        
        # Check if required columns exist
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in reader.fieldnames for col in required_cols):
            raise ValueError(
                f"CSV must contain columns: {required_cols}. "
                f"Found: {reader.fieldnames}"
            )
        
        for idx, row in enumerate(reader):
            try:
                # Parse timestamp (use index if not provided)
                timestamp = int(row.get('timestamp', idx))
                
                candle = {
                    'timestamp': timestamp,
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': int(float(row['volume'])),
                    'symbol': row.get('symbol', symbol)
                }
                
                candles.append(candle)
            except (ValueError, KeyError) as e:
                raise ValueError(f"Error parsing row {idx + 1}: {e}")
    
    if not candles:
        raise ValueError("CSV file is empty or contains no valid data")
    
    return candles


def load_candles_from_json(json_path: str) -> List[Dict]:
    """
    Load candle data from JSON file.
    
    Expected JSON format:
    [
        {
            "timestamp": 0,
            "open": 18000.0,
            "high": 18005.0,
            "low": 17995.0,
            "close": 18003.0,
            "volume": 5000,
            "symbol": "MNQ"
        },
        ...
    ]
    
    Args:
        json_path: Path to JSON file
    
    Returns:
        List of candle dictionaries
    
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON is invalid
        ValueError: If data format is invalid
    """
    json_path = Path(json_path)
    
    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        raise ValueError("JSON must contain a list of candles")
    
    if not data:
        raise ValueError("JSON file is empty")
    
    # Validate structure
    required_keys = ['open', 'high', 'low', 'close', 'volume']
    for idx, candle in enumerate(data):
        if not isinstance(candle, dict):
            raise ValueError(f"Candle at index {idx} is not a dictionary")
        
        missing_keys = [key for key in required_keys if key not in candle]
        if missing_keys:
            raise ValueError(
                f"Candle at index {idx} missing keys: {missing_keys}"
            )
        
        # Ensure types are correct
        try:
            candle['open'] = float(candle['open'])
            candle['high'] = float(candle['high'])
            candle['low'] = float(candle['low'])
            candle['close'] = float(candle['close'])
            candle['volume'] = int(float(candle['volume']))
            if 'timestamp' not in candle:
                candle['timestamp'] = idx
            else:
                candle['timestamp'] = int(candle['timestamp'])
            if 'symbol' not in candle:
                candle['symbol'] = 'MNQ'
        except (ValueError, TypeError) as e:
            raise ValueError(f"Error parsing candle at index {idx}: {e}")
    
    return data


def export_json(data: Dict[str, Any], file_path: str) -> None:
    """
    Export data to JSON file.
    
    Args:
        data: Dictionary to export
        file_path: Path to output JSON file
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def export_equity_curve_csv(equity_curve: List[Dict], file_path: str) -> None:
    """
    Export equity curve data to CSV file.
    
    Args:
        equity_curve: List of equity curve data points
            Each dict should have 'time' (or 'timestamp') and 'equity' keys
        file_path: Path to output CSV file
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    fieldnames = ['timestamp', 'equity']
    
    with open(file_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for point in equity_curve:
            # Handle both 'time' and 'timestamp' keys
            timestamp = point.get('timestamp', point.get('time', ''))
            
            # Format timestamp if it's a datetime object
            if isinstance(timestamp, datetime):
                timestamp = get_formatted_timestamp(timestamp)
            elif isinstance(timestamp, (int, float)):
                # Convert Unix timestamp to datetime
                timestamp = get_formatted_timestamp(datetime.fromtimestamp(timestamp))
            
            row = {
                'timestamp': timestamp,
                'equity': point.get('equity', 0)
            }
            writer.writerow(row)


# Example usage
if __name__ == "__main__":
    # Test config loading
    try:
        config = load_config()
        print("Config loaded successfully")
        print(f"Environment: {config['environment']}")
        print(f"Account size: ${config['account']['size']}")
    except Exception as e:
        print(f"Error loading config: {e}")
    
    # Test ATR calculation
    mock_candles = generate_mock_candles(50)
    atr = calculate_atr(
        [c['high'] for c in mock_candles],
        [c['low'] for c in mock_candles],
        [c['close'] for c in mock_candles]
    )
    print(f"\nATR calculated: {atr:.2f}")
    
    # Test trade signal output
    sample_signal = {
        'timestamp': datetime.now(),
        'symbol': 'MNQ',
        'direction': 'LONG',
        'entry': 17893.50,
        'stop_loss': 17864.25,
        'take_profit': 17965.00,
        'r_multiple': 3.1,
        'position_size': 2,
        'dollar_risk': 480,
        'risk_percent': 0.5
    }
    print(f"\nSample output:\n{format_trade_output(sample_signal)}")

