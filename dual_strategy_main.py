"""
Dual Strategy Main - Runs AAFR and AJR in parallel.
Both strategies share execution arbiter and GUI bot.
"""

import sys
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from aafr.icc_module import ICCDetector
from aafr.cvd_module import CVDCalculator
from aafr.tradovate_api import TradovateAPI
from aafr.utils import load_config, get_formatted_timestamp, calculate_atr

from ajr.ajr_strategy import AJRStrategy

from shared.signal_schema import TradeSignal
from shared.unified_risk_manager import UnifiedRiskManager
from shared.execution_arbiter import ExecutionArbiter
from shared.signal_logger import SignalLogger

from aafr.websocket_server import WebSocketServer


class DualStrategySystem:
    """
    Main orchestrator for running AAFR and AJR strategies in parallel.
    Both strategies emit signals through shared execution arbiter.
    """
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize dual strategy system."""
        self.config = load_config(config_path)
        
        # Initialize shared components
        self.risk_manager = UnifiedRiskManager(config_path)
        self.arbiter = ExecutionArbiter(config_path, self.risk_manager)
        self.signal_logger = SignalLogger()
        
        # Initialize API
        self.api = TradovateAPI(config_path)
        
        # Initialize AAFR strategy modules
        self.icc_detector = ICCDetector()
        self.cvd_calculator = CVDCalculator()
        
        # Initialize AJR strategy
        self.ajr_strategy = AJRStrategy(config_path)
        
        # Initialize WebSocket server for GUI bot
        gui_bot_config = self.config.get('gui_bot', {})
        self.ws_server = None
        if gui_bot_config.get('enabled', False):
            ws_host = gui_bot_config.get('websocket_host', 'localhost')
            ws_port = gui_bot_config.get('websocket_port', 8765)
            self.ws_server = WebSocketServer(ws_host, ws_port)
        
        # System state
        self.running = False
        self.candle_buffers = {}  # Per-symbol candle buffers
        
        print(f"\n{'='*60}")
        print("DUAL STRATEGY SYSTEM - AAFR + AJR")
        print(f"{'='*60}")
        print(f"[SYSTEM] Initialized")
        print(f"[SYSTEM] AAFR: {'enabled' if self.config.get('strategies', {}).get('AAFR', {}).get('enabled') else 'disabled'}")
        print(f"[SYSTEM] AJR: {'enabled' if self.config.get('strategies', {}).get('AJR', {}).get('enabled') else 'disabled'}")
        print(f"[SYSTEM] Arbiter: {'enabled' if self.arbiter.enabled else 'disabled'}")
        print(f"[SYSTEM] GUI Bot: {'enabled' if self.ws_server else 'disabled'}")
    
    async def start(self, symbols: List[str]):
        """
        Start monitoring and trading for specified symbols.
        
        Args:
            symbols: List of symbols to trade (NQ, ES, GC, CL)
        """
        print(f"\n[SYSTEM] Starting dual strategy system...")
        print(f"[SYSTEM] Symbols: {symbols}")
        print(f"[SYSTEM] Press Ctrl+C to stop\n")
        
        # Authenticate with API
        if not self.api.authenticate():
            print("[WARNING] API authentication failed, using mock data")
        
        self.running = True
        
        try:
            # Start WebSocket server if enabled
            tasks = []
            if self.ws_server:
                try:
                    ws_task = asyncio.create_task(self.ws_server.start())
                    tasks.append(ws_task)
                    await asyncio.sleep(0.5)
                except Exception as e:
                    print(f"[WARNING] WebSocket server not started: {e}")
                    print(f"[INFO] System will continue without WebSocket (GUI bot won't connect)")
            
            # Start monitoring each symbol
            for symbol in symbols:
                task = asyncio.create_task(self._monitor_symbol(symbol))
                tasks.append(task)
            
            # Wait for all tasks
            await asyncio.gather(*tasks)
            
        except KeyboardInterrupt:
            print("\n\n[SYSTEM] Stopping...")
            if self.ws_server:
                await self.ws_server.stop()
            self.stop()
    
    async def _monitor_symbol(self, symbol: str):
        """
        Monitor single symbol with both strategies.
        
        Args:
            symbol: Trading symbol
        """
        print(f"[{symbol}] Starting monitoring...")
        
        # Load historical candles
        candles = self.api.get_historical_candles(symbol, count=200)
        
        if not candles:
            print(f"[{symbol}] ERROR: Failed to get candles")
            return
        
        self.candle_buffers[symbol] = candles
        print(f"[{symbol}] Loaded {len(candles)} historical candles")
        
        # Main monitoring loop
        check_count = 0
        while self.running:
            await asyncio.sleep(5)  # Check every 5 seconds
            
            check_count += 1
            if check_count % 12 == 0:  # Status every minute
                print(f"[{symbol}] Monitoring... ({check_count * 5}s elapsed)")
            
            # Get current candle buffer
            candle_buffer = self.candle_buffers.get(symbol, [])
            
            if not candle_buffer:
                continue
            
            # Check both strategies in parallel
            aafr_signal = await self._check_aafr(symbol, candle_buffer)
            ajr_signal = await self._check_ajr(symbol, candle_buffer)
            
            # Process signals through arbiter
            if aafr_signal:
                await self._process_signal(aafr_signal)
            
            if ajr_signal:
                await self._process_signal(ajr_signal)
    
    async def _check_aafr(self, symbol: str, candles: List[Dict]) -> Optional[TradeSignal]:
        """Check AAFR for signals."""
        if not self.config.get('strategies', {}).get('AAFR', {}).get('enabled', True):
            return None
        
        # Detect ICC structure
        icc_structure = self.icc_detector.detect_icc_structure(candles, require_all_phases=True)
        
        if not icc_structure or not icc_structure.get('complete'):
            return None
        
        # Validate
        is_valid, violations = self.icc_detector.validate_full_setup(icc_structure, candles)
        
        if not is_valid:
            return None
        
        # Calculate trade levels
        entry, stop, tp, r_multiple = self.icc_detector.calculate_trade_levels(
            icc_structure, candles, symbol
        )
        
        if not entry or not stop:
            return None
        
        # Create signal
        try:
            signal = TradeSignal(
                strategy_id="AAFR",
                instrument=symbol,
                direction=icc_structure['indication']['direction'],
                entry_price=entry,
                stop_price=stop,
                take_profit=[tp],
                max_loss_usd=750,
                notes="ICC continuation pattern"
            )
            
            print(f"[AAFR] Signal detected: {symbol} {signal.direction}")
            return signal
            
        except ValueError:
            return None
    
    async def _check_ajr(self, symbol: str, candles: List[Dict]) -> Optional[TradeSignal]:
        """Check AJR for signals."""
        if not candles:
            return None
        
        # Process latest candle
        latest_candle = candles[-1]
        
        # Add previous close for gap detection
        if len(candles) > 1:
            latest_candle['prev_close'] = candles[-2]['close']
        
        signal = self.ajr_strategy.process_candle(latest_candle, symbol)
        
        return signal
    
    async def _process_signal(self, signal: TradeSignal):
        """
        Process signal through arbiter and emit to GUI bot.
        
        Args:
            signal: Trade signal from either strategy
        """
        # Submit to arbiter
        accepted, reason, details = await self.arbiter.process_signal(signal)
        
        # Log decision
        self.signal_logger.log_arbiter_decision(signal, accepted, reason, details)
        
        if accepted:
            # Emit to GUI bot via WebSocket
            if self.ws_server and details:
                await self._emit_to_gui_bot(signal, details)
    
    async def _emit_to_gui_bot(self, signal: TradeSignal, details: Dict):
        """
        Emit trade event to GUI bot.
        
        Args:
            signal: Trade signal
            details: Execution details
        """
        # Build TP ladder: 1 contract per TP level (2-3 contracts = 2-3 TPs)
        position_size = details['position_size']
        tp_count = min(len(signal.take_profit), position_size)  # Match TPs to position size
        
        # Create TP ladder: each TP gets 1 contract
        tp_ladder = []
        for i in range(tp_count):
            tp_ladder.append({
                'price': signal.take_profit[i],
                'qty': 1  # 1 contract per TP level
            })
        
        # Build event for GUI bot
        event = {
            'event': 'NEW_POSITION',
            'symbol': signal.instrument,
            'side': signal.direction,
            'entry_price': signal.entry_price,
            'size': position_size,
            'initial_stop': signal.stop_price,
            'tps': tp_ladder,
            'mode': self.config.get('gui_bot', {}).get('mode', 'EVAL'),
            'strategy': signal.strategy_id,
            'timestamp': datetime.now().isoformat()
        }
        
        await self.ws_server.broadcast_event(event)
        print(f"[WS] Emitted {signal.strategy_id} signal to GUI bot")
    
    def stop(self):
        """Stop the system."""
        self.running = False
        
        # Print final statistics
        print(f"\n{'='*60}")
        print("FINAL STATISTICS")
        print(f"{'='*60}")
        
        self.arbiter.print_stats()
        
        risk_summary = self.risk_manager.get_risk_summary()
        print(f"\n[RISK] Summary:")
        print(f"  Daily loss: ${risk_summary['daily_loss']:.2f}")
        print(f"  Daily trades: {risk_summary['daily_trades']}")
        
        print(f"\n[SYSTEM] System stopped")


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Dual Strategy System (AAFR + AJR)')
    parser.add_argument('--symbols', nargs='+', default=['NQ'],
                       help='Trading symbols (NQ, ES, GC, CL)')
    parser.add_argument('--config', default='config.json',
                       help='Path to config file (relative to aafr directory)')
    
    args = parser.parse_args()
    
    # Validate symbols (E-Mini only)
    allowed = ["NQ", "ES", "GC", "CL"]
    symbols = [s.upper() for s in args.symbols if s.upper() in allowed]
    
    if not symbols:
        print(f"[ERROR] No valid symbols. Only {allowed} allowed.")
        sys.exit(1)
    
    # Create and start system
    system = DualStrategySystem(args.config)
    
    try:
        await system.start(symbols)
    except KeyboardInterrupt:
        print("\n[SYSTEM] Interrupted by user")
    finally:
        system.stop()


if __name__ == "__main__":
    asyncio.run(main())

