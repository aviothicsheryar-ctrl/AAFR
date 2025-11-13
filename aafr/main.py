"""
AAFR Main Trading System
Integrates ICC detection, CVD analysis, risk management, and backtesting.
"""

import sys
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from aafr.icc_module import ICCDetector
from aafr.cvd_module import CVDCalculator
from aafr.risk_engine import RiskEngine
from aafr.tradovate_api import TradovateAPI
from aafr.backtester import Backtester
from aafr.utils import format_trade_output, log_trade_signal, load_config, load_candles_from_csv, load_candles_from_json, get_formatted_timestamp, get_micro_symbol, calculate_atr
from aafr.telegram_bot import send_telegram_alert, format_telegram_message
from aafr.websocket_server import WebSocketServer


class AAFRTradingSystem:
    """
    Main AAFR trading system orchestrator.
    Coordinates all modules for live trading and backtesting.
    """
    
    def __init__(self, config_path: str = "config.json"):
        """
        Initialize AAFR Trading System.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = load_config(config_path)
        
        # Initialize core modules
        self.api = TradovateAPI(config_path)
        self.icc_detector = ICCDetector()
        self.cvd_calculator = CVDCalculator()
        self.risk_engine = RiskEngine(config_path)
        
        # Initialize WebSocket server for GUI bot integration
        gui_bot_config = self.config.get('gui_bot', {})
        self.ws_server = None
        if gui_bot_config.get('enabled', False):
            ws_host = gui_bot_config.get('websocket_host', 'localhost')
            ws_port = gui_bot_config.get('websocket_port', 8765)
            self.ws_server = WebSocketServer(ws_host, ws_port)
        
        # System state
        self.running = False
        self.candle_buffers = {}  # Per-symbol candle buffers for independent state
    
    async def start_live_monitoring(self, symbols: List[str]) -> None:
        """
        Start live market monitoring for specified symbols.
        
        Args:
            symbols: List of trading symbols to monitor
        """
        print("Starting AAFR Live Trading System...")
        print("="*60)
        print("Press Ctrl+C to stop monitoring\n")
        
        # Authenticate with API
        if not self.api.authenticate():
            print("[WARNING] API authentication failed, running in mock mode")
        
        self.running = True
        
        try:
            # Start WebSocket server if enabled
            tasks = []
            if self.ws_server:
                ws_task = asyncio.create_task(self.ws_server.start())
                tasks.append(ws_task)
                await asyncio.sleep(0.5)  # Give server time to start
            
            # Start monitoring each symbol
            for symbol in symbols:
                task = asyncio.create_task(self._monitor_symbol(symbol))
                tasks.append(task)
            
            # Wait for all tasks
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("\n\n[INFO] Stopping monitoring...")
            if self.ws_server:
                await self.ws_server.stop()
            self.stop()
            print("[OK] System stopped gracefully")
    
    async def _monitor_symbol(self, symbol: str) -> None:
        """
        Monitor a single symbol for trade setups.
        
        Args:
            symbol: Trading symbol
        """
        print(f"\nMonitoring {symbol}...")
        
        # Initialize with historical data
        historical_candles = self.api.get_historical_candles(symbol, count=100)
        
        if not historical_candles:
            print(f"[ERROR] Failed to get historical data for {symbol}")
            return
        
        # Store per-symbol candle buffer (independent state per symbol)
        self.candle_buffers[symbol] = historical_candles
        timestamp_str = get_formatted_timestamp()
        print(f"[{timestamp_str}] [OK] {symbol}: Loaded {len(historical_candles)} historical candles")
        
        if self.api.is_using_mock_data():
            timestamp_str = get_formatted_timestamp()
            print(f"[{timestamp_str}] [INFO] {symbol}: Using mock data (no API credentials or API unavailable)")
            print(f"[{timestamp_str}] [INFO] {symbol}: Monitoring will check for ICC patterns every 5 seconds...")
        else:
            timestamp_str = get_formatted_timestamp()
            print(f"[{timestamp_str}] [INFO] {symbol}: Using live API data")
            print(f"[{timestamp_str}] [INFO] {symbol}: Monitoring will check for ICC patterns every 5 seconds...")
        
        # Create independent ICC and CVD detectors for this symbol
        symbol_icc_detector = ICCDetector()
        symbol_cvd_calculator = CVDCalculator()
        
        # Main monitoring loop
        check_count = 0
        while self.running:
            # TODO: Implement live data streaming
            # For now, simulate with delays
            await asyncio.sleep(5)
            
            check_count += 1
            if check_count % 12 == 0:  # Print status every minute (12 * 5s = 60s)
                timestamp_str = get_formatted_timestamp()
                print(f"[{timestamp_str}] [INFO] {symbol}: Still monitoring... ({check_count * 5}s elapsed)")
            
            # Get this symbol's candle buffer
            candle_buffer = self.candle_buffers.get(symbol, [])
            
            # Check for ICC structures using symbol-specific detector
            icc_structure = symbol_icc_detector.detect_icc_structure(
                candle_buffer, require_all_phases=True
            )
            
            if not icc_structure or not icc_structure.get('complete'):
                continue
            
            timestamp_str = get_formatted_timestamp()
            print(f"[{timestamp_str}] [INFO] {symbol}: ICC structure detected, validating...")
            
            # Validate setup
            is_valid, violations = symbol_icc_detector.validate_full_setup(
                icc_structure, candle_buffer
            )
            
            if not is_valid:
                if violations:
                    timestamp_str = get_formatted_timestamp()
                    print(f"[{timestamp_str}] [INFO] {symbol}: Setup invalid - {', '.join(violations[:2])}")
                continue
            
            # Process trade signal with symbol's candle buffer
            await self._process_trade_signal(symbol, icc_structure, candle_buffer)
    
    async def _process_trade_signal(self, symbol: str, icc_structure: Dict, 
                                   candle_buffer: List[Dict]) -> None:
        """
        Process and execute a valid trade signal.
        
        Args:
            symbol: Trading symbol
            icc_structure: ICC structure dictionary
            candle_buffer: Candle data for this symbol
        """
        timestamp = get_formatted_timestamp()
        print(f"\n[{timestamp}] >>> TRADE SIGNAL DETECTED for {symbol}")
        
        # Create symbol-specific ICC detector for trade level calculation
        symbol_icc_detector = ICCDetector()
        
        # Calculate trade levels
        entry, stop, tp, r_multiple = symbol_icc_detector.calculate_trade_levels(
            icc_structure, candle_buffer, symbol
        )
        
        if not entry or not stop:
            timestamp_str = get_formatted_timestamp()
            print(f"[{timestamp_str}] [ERROR] {symbol}: Could not calculate trade levels")
            return
        
        # Validate with risk engine
        is_valid, msg, trade_details = self.risk_engine.validate_trade_setup(
            entry, stop, icc_structure['indication']['direction'], 
            symbol, candle_buffer
        )
        
        if not is_valid:
            print(f"[ERROR] Risk validation failed: {msg}")
            return
        
        # Format and display trade signal
        signal_timestamp = datetime.now()
        signal = {
            'timestamp': signal_timestamp,
            'symbol': symbol,
            'direction': icc_structure['indication']['direction'],
            'entry': entry,
            'stop_loss': stop,
            'take_profit': tp,
            'r_multiple': trade_details['r_multiple'],
            'position_size': trade_details['position_size'],
            'dollar_risk': trade_details['dollar_risk'],
            'risk_percent': trade_details['risk_percent'],
            'status': 'pending'
        }
        
        # Print formatted trade signal with timestamp
        timestamp_str = get_formatted_timestamp(signal_timestamp)
        print(f"[{timestamp_str}] {symbol}: {format_trade_output(signal)}")
        
        # Log trade signal
        log_trade_signal(signal)
        
        # Send Telegram alert
        telegram_msg = format_telegram_message(signal)
        send_telegram_alert(telegram_msg)
        
        # Emit WebSocket event for GUI bot
        if self.ws_server:
            await self._emit_new_position_event(signal, icc_structure, candle_buffer)
        
        # TODO: Execute trade via API (paper trading in demo)
        # order_result = await self._place_trade_order(signal)
        
        # Update risk engine
        self.risk_engine.increment_daily_trades()
        
        # Reset detector to avoid duplicate signals
        self.icc_detector.reset()
    
    async def _emit_new_position_event(self, signal: Dict, icc_structure: Dict, 
                                       candle_buffer: List[Dict]) -> None:
        """
        Emit NEW_POSITION event to GUI bot via WebSocket.
        
        Args:
            signal: Trade signal dictionary
            icc_structure: ICC structure details
            candle_buffer: Historical candle data
        """
        # Calculate ATR for stop buffer
        atr = calculate_atr(candle_buffer, period=14) if len(candle_buffer) >= 14 else 0
        
        # Get GUI bot mode from config
        gui_bot_config = self.config.get('gui_bot', {})
        mode = gui_bot_config.get('mode', 'EVAL')
        
        # Calculate TP ladder (divide position into 3 levels)
        position_size = signal['position_size']
        tp_ladder = self._calculate_tp_ladder(
            signal['entry'],
            signal['take_profit'],
            position_size,
            signal['direction']
        )
        
        # Build NEW_POSITION event
        event = {
            'event': 'NEW_POSITION',
            'symbol': signal['symbol'],
            'side': signal['direction'],
            'entry_price': signal['entry'],
            'size': position_size,
            'initial_stop': signal['stop_loss'],
            'tps': tp_ladder,
            'mode': mode,
            'atr': round(atr, 2) if atr else 0,
            'timestamp': signal['timestamp'].isoformat()
        }
        
        # Broadcast event
        await self.ws_server.broadcast_event(event)
        print(f"[WS] Emitted NEW_POSITION event for {signal['symbol']}")
    
    def _calculate_tp_ladder(self, entry: float, final_tp: float, size: int, 
                            direction: str) -> List[Dict]:
        """
        Calculate TP ladder with 3 levels.
        
        Args:
            entry: Entry price
            final_tp: Final take profit target
            size: Total position size
            direction: 'LONG' or 'SHORT'
        
        Returns:
            List of TP dictionaries with price and qty
        """
        if size <= 0:
            return []
        
        # Divide position into thirds (or as close as possible)
        qty_per_level = max(1, size // 3)
        remaining = size - (qty_per_level * 2)
        
        # Calculate TP levels (33%, 66%, 100% of distance)
        distance = abs(final_tp - entry)
        
        if direction == 'LONG':
            tp1_price = entry + (distance * 0.33)
            tp2_price = entry + (distance * 0.66)
            tp3_price = final_tp
        else:  # SHORT
            tp1_price = entry - (distance * 0.33)
            tp2_price = entry - (distance * 0.66)
            tp3_price = final_tp
        
        return [
            {'price': round(tp1_price, 2), 'qty': qty_per_level},
            {'price': round(tp2_price, 2), 'qty': qty_per_level},
            {'price': round(tp3_price, 2), 'qty': remaining}
        ]
    
    async def _place_trade_order(self, signal: Dict) -> Optional[Dict]:
        """
        Place a trade order via API (paper trading).
        
        Args:
            signal: Trade signal dictionary
        
        Returns:
            Order result or None
        """
        # TODO: Implement actual order placement
        order_details = {
            'accountId': 'YOUR_ACCOUNT_ID',
            'action': 'Buy' if signal['direction'] == 'LONG' else 'Sell',
            'symbol': signal['symbol'],
            'orderQty': signal['position_size'],
            'orderType': 'Market',
            'route': 'Default'
        }
        
        result = self.api.place_order(order_details)
        return result
    
    def run_backtest(self, symbol: Optional[str] = None, 
                    candle_data: Optional[List[Dict]] = None,
                    instruments: Optional[List[str]] = None,
                    all_instruments: bool = False) -> Dict:
        """
        Run backtest on historical data.
        
        Args:
            symbol: Trading symbol (for single instrument backtest)
            candle_data: Optional historical candle data (if None, fetch from API)
            instruments: Optional list of instruments to backtest
            all_instruments: If True, backtest all 5 instruments (MNQ, MES, MGC, MCL, MYM)
        
        Returns:
            Backtest results dictionary (or dict of results for multi-instrument)
        """
        from aafr.utils import load_config
        
        # Determine which instruments to backtest
        if all_instruments:
            config = load_config()
            instruments = config['account']['enabled_instruments']
            print(f"\nRunning backtest for all instruments: {instruments}")
        elif instruments:
            print(f"\nRunning backtest for instruments: {instruments}")
        elif symbol:
            instruments = [symbol]
            print(f"\nRunning backtest for {symbol}...")
        else:
            print("[ERROR] Must specify symbol, instruments, or all_instruments=True")
            return {}
        
        print("="*60)
        
        # Fetch or prepare candle data for each instrument
        candles_by_symbol = {}
        
        for sym in instruments:
            if candle_data and sym == symbol:
                # Use provided candle data
                candles_by_symbol[sym] = candle_data
            else:
                # Fetch historical data from API
                data = self.api.get_historical_candles(sym, count=200)
                if not data:
                    print(f"[ERROR] Failed to fetch historical data for {sym}")
                    continue
                candles_by_symbol[sym] = data
                print(f"[INFO] Loaded {len(data)} candles for {sym}")
        
        if not candles_by_symbol:
            print("[ERROR] No candle data available for backtesting")
            return {}
        
        # Run backtest(s)
        if len(candles_by_symbol) == 1:
            # Single instrument backtest
            sym = list(candles_by_symbol.keys())[0]
            backtester = Backtester()
            results = backtester.run_backtest(candles_by_symbol[sym], sym)
            backtester.print_results(results)
            return results
        else:
            # Multi-instrument backtest
            backtester = Backtester()
            results = backtester.run_backtest_batch(candles_by_symbol)
            
            # Print summary
            print("\n" + "="*60)
            print("MULTI-INSTRUMENT BACKTEST SUMMARY")
            print("="*60)
            for sym, sym_results in results.items():
                print(f"\n{sym}:")
                print(f"  Trades: {sym_results['total_trades']}")
                print(f"  Win Rate: {sym_results['win_rate']:.2f}%")
                print(f"  Net P&L: ${sym_results['net_pnl']:.2f}")
                print(f"  Avg R: {sym_results['avg_r']:.2f}")
            print("="*60 + "\n")
            
            return results
    
    def analyze_data(self, candle_data: List[Dict], symbol: str) -> None:
        """
        Analyze custom data for ICC patterns and generate trade signals.
        
        Args:
            candle_data: List of candle dictionaries
            symbol: Trading symbol
        """
        print(f"\nAnalyzing {len(candle_data)} candles for {symbol}...")
        print("="*60)
        
        if not candle_data:
            print("[ERROR] No candle data provided")
            return
        
        # Detect ICC structures
        icc_detector = ICCDetector()
        icc_structure = icc_detector.detect_icc_structure(
            candle_data, require_all_phases=True
        )
        
        if not icc_structure or not icc_structure.get('complete'):
            print("[INFO] No complete ICC structure found in data")
            return
        
        print(f"[OK] ICC structure detected!")
        print(f"    - Indication: {icc_structure['indication']['direction']}")
        print(f"    - Correction: candles {icc_structure['correction']['start_idx']} to {icc_structure['correction']['end_idx']}")
        print(f"    - Continuation: candle {icc_structure['continuation']['idx']}")
        
        # Validate setup
        is_valid, violations = icc_detector.validate_full_setup(
            icc_structure, candle_data
        )
        
        if not is_valid:
            print(f"[WARNING] Setup invalid: {', '.join(violations)}")
            return
        
        # Calculate trade levels
        entry, stop, tp, r_multiple = icc_detector.calculate_trade_levels(
            icc_structure, candle_data, symbol
        )
        
        if not entry or not stop:
            print("[ERROR] Could not calculate trade levels")
            return
        
        # Validate with risk engine
        is_valid, msg, trade_details = self.risk_engine.validate_trade_setup(
            entry, stop, icc_structure['indication']['direction'], 
            symbol, candle_data
        )
        
        if not is_valid:
            print(f"[ERROR] Risk validation failed: {msg}")
            return
        
        # Generate and display trade signal
        signal = {
            'timestamp': datetime.now(),
            'symbol': symbol,
            'direction': icc_structure['indication']['direction'],
            'entry': entry,
            'stop_loss': stop,
            'take_profit': tp,
            'r_multiple': trade_details['r_multiple'],
            'position_size': trade_details['position_size'],
            'dollar_risk': trade_details['dollar_risk'],
            'risk_percent': trade_details['risk_percent'],
            'status': 'pending'
        }
        
        timestamp_str = get_formatted_timestamp()
        print("\n" + "="*60)
        print(f"[{timestamp_str}] TRADE SIGNAL for {symbol}")
        print("="*60)
        print(f"[{timestamp_str}] {symbol}: {format_trade_output(signal)}")
        print("="*60)
        
        # Log trade signal
        log_trade_signal(signal)
        timestamp_str = get_formatted_timestamp()
        print(f"[{timestamp_str}] [OK] Trade signal logged to logs/trades/trades_{datetime.now().strftime('%Y%m%d')}.csv")
        
        # Send Telegram alert
        telegram_msg = format_telegram_message(signal)
        send_telegram_alert(telegram_msg)
    
    def stop(self) -> None:
        """Stop the trading system."""
        self.running = False
        print("\nAAFR Trading System stopped.")


def main():
    """
    Main entry point for AAFR Trading System.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='AAFR Trading System')
    parser.add_argument('--mode', choices=['live', 'backtest', 'test', 'analyze'], 
                       default='test', help='Operating mode (analyze: analyze custom data file)')
    parser.add_argument('--symbol', default='MNQ', 
                       help='Trading symbol (NQ/ES/GC/CL/YM will be mapped to micro contracts)')
    parser.add_argument('--symbols', nargs='+', 
                       help='Multiple symbols for live mode or backtest')
    parser.add_argument('--instruments', nargs='+',
                       help='List of instruments to backtest (e.g., MNQ MES MGC)')
    parser.add_argument('--all-instruments', action='store_true',
                       help='Run backtest on all 5 instruments')
    parser.add_argument('--data-file', type=str,
                       help='Path to CSV or JSON file containing candle data')
    
    args = parser.parse_args()
    
    # Map symbol to micro contract if needed
    if args.symbol:
        args.symbol = get_micro_symbol(args.symbol)
    if args.symbols:
        args.symbols = [get_micro_symbol(s) for s in args.symbols]
    if args.instruments:
        args.instruments = [get_micro_symbol(s) for s in args.instruments]
    
    # Initialize system
    system = AAFRTradingSystem()
    
    try:
        # Load data from file if provided
        candle_data = None
        if args.data_file:
            print(f"[INFO] Loading data from: {args.data_file}")
            file_path = Path(args.data_file)
            
            if not file_path.exists():
                print(f"[ERROR] File not found: {args.data_file}")
                sys.exit(1)
            
            try:
                if file_path.suffix.lower() == '.csv':
                    candle_data = load_candles_from_csv(str(file_path), args.symbol)
                    print(f"[OK] Loaded {len(candle_data)} candles from CSV")
                elif file_path.suffix.lower() == '.json':
                    candle_data = load_candles_from_json(str(file_path))
                    print(f"[OK] Loaded {len(candle_data)} candles from JSON")
                else:
                    print(f"[ERROR] Unsupported file format. Use .csv or .json")
                    sys.exit(1)
            except Exception as e:
                print(f"[ERROR] Failed to load data file: {e}")
                sys.exit(1)
        
        if args.mode == 'backtest':
            # Run backtest (with custom data if provided)
            if args.all_instruments:
                results = system.run_backtest(all_instruments=True)
            elif args.instruments:
                results = system.run_backtest(instruments=args.instruments)
            elif args.symbols:
                results = system.run_backtest(instruments=args.symbols)
            elif candle_data:
                results = system.run_backtest(args.symbol, candle_data=candle_data)
            else:
                results = system.run_backtest(symbol=args.symbol)
            
        elif args.mode == 'analyze':
            # Analyze custom data file
            if not candle_data:
                print("[ERROR] --data-file required for analyze mode")
                sys.exit(1)
            system.analyze_data(candle_data, args.symbol)
            
        elif args.mode == 'live':
        
            # Start live monitoring
            symbols = args.symbols if args.symbols else [args.symbol]
            asyncio.run(system.start_live_monitoring(symbols))
            
        else:  # test mode
            # Quick test of all modules
            print("Running AAFR System Test...")
            print("="*60)
            
            # Test API connection
            api = TradovateAPI()
            api.authenticate()

            # Test data fetch
            candles = api.get_historical_candles(args.symbol, count=50)
            print(f"\n[OK] Fetched {len(candles)} candles for {args.symbol}")
            
            # Test ICC detection
            icc = ICCDetector()
            icc_structure = icc.detect_icc_structure(candles)
            if icc_structure:
                print(f"[OK] ICC structure detected")
            else:
                print(f"[WARNING] No ICC structure found in test data")
            
            # Test CVD
            cvd = CVDCalculator()
            cvd_values = cvd.calculate_cvd(candles)
            print(f"[OK] CVD calculated: {len(cvd_values)} values")
            
            # Test risk engine
            risk = RiskEngine()
            is_valid, msg, details = risk.validate_trade_setup(
                18000.0, 17950.0, 'LONG', 'MNQ', candles
            )
            print(f"[OK] Risk validation: {'PASS' if is_valid else 'FAIL'} - {msg}")
            
            print("\n[OK] All tests completed successfully!")
    
    except KeyboardInterrupt:
        print("\n\nSystem interrupted by user")
        system.stop()
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

