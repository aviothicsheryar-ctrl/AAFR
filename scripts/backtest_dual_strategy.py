"""
Dual Strategy Backtester - Runs backtests for both AAFR and AJR strategies.
Compares performance and exports results separately for each strategy.
"""

import sys
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aafr.backtester import Backtester
from aafr.utils import (
    generate_mock_candles_for_period, 
    load_config, 
    get_formatted_timestamp,
    load_candles_from_json,
    get_micro_symbol
)
from aafr.tradovate_api import TradovateAPI
from ajr.ajr_strategy import AJRStrategy
from shared.unified_risk_manager import UnifiedRiskManager
from shared.signal_schema import TradeSignal


class AJRBacktester:
    """
    Backtesting engine for AJR strategy.
    Simulates trades on historical data and calculates performance metrics.
    """
    
    def __init__(self, config_path: str = "aafr/config.json"):
        """Initialize AJR Backtester."""
        self.config_path = config_path
        self.ajr_strategy = AJRStrategy(config_path)
        self.risk_manager = UnifiedRiskManager(config_path)
        
        # Performance tracking
        self.trades = []
        self.equity_curve = []
        self.current_equity = 100000.0
        self.max_equity = self.current_equity
        self.max_drawdown = 0.0
        self.max_drawdown_pct = 0.0
    
    def run_backtest(self, candles: List[Dict], symbol: str, 
                    start_equity: float = 100000) -> Dict:
        """
        Run backtest on historical candle data for AJR strategy.
        
        Args:
            candles: Historical candle data
            symbol: Trading symbol
            start_equity: Starting equity
        
        Returns:
            Dictionary with backtest results
        """
        start_time = datetime.now()
        
        self.current_equity = float(start_equity)
        self.max_equity = float(start_equity)
        self.trades = []
        
        # Initialize equity curve
        first_timestamp = candles[0].get('timestamp', 0) if candles else 0
        if isinstance(first_timestamp, (int, float)) and first_timestamp > 0:
            try:
                first_dt = datetime.fromtimestamp(first_timestamp)
            except (ValueError, OSError):
                first_dt = datetime.now()
        else:
            first_dt = datetime.now()
        
        self.equity_curve = [{
            'timestamp': first_dt,
            'time': 0,
            'equity': float(start_equity)
        }]
        
        # Reset strategy
        self.ajr_strategy.reset(symbol)
        self.risk_manager.reset_daily()
        
        # Need minimum candles for gap detection and probe filter
        min_candles = 50
        total_candles = len(candles)
        progress_interval = max(1000, total_candles // 20)
        
        print(f"[AJR] Starting backtest on {len(candles)} candles...")
        
        for i in range(min_candles, total_candles):
            # Print progress
            if i % progress_interval == 0 or i == min_candles:
                progress_pct = ((i - min_candles) / (total_candles - min_candles)) * 100
                print(f"[AJR] Processing candle {i}/{total_candles} ({progress_pct:.1f}%) - Trades: {len(self.trades)}")
            
            # Get current candle
            candle = candles[i]
            
            # Add prev_close for gap detection
            if i > 0:
                candle['prev_close'] = candles[i-1]['close']
            
            # Process candle through AJR strategy
            signal = self.ajr_strategy.process_candle(candle, symbol)
            
            if not signal:
                continue
            
            # Validate signal with risk manager
            is_valid, msg, details = self.risk_manager.validate_signal(signal)
            
            if not is_valid:
                continue
            
            # Get position size from risk manager
            position_size = details['position_size']
            
            # Calculate entry timestamp
            trade_timestamp = i
            candle_ts = candle.get('timestamp', i)
            if isinstance(candle_ts, (int, float)) and candle_ts > 0:
                try:
                    trade_dt = datetime.fromtimestamp(candle_ts)
                except (ValueError, OSError):
                    trade_dt = datetime.now()
            else:
                trade_dt = datetime.now()
            
            # Simulate trade outcome (AJR has multiple TPs)
            result = self._simulate_ajr_trade_outcome(
                signal, position_size, candles, i+1, trade_dt
            )
            
            # Record trade
            trade_record = {
                'timestamp': trade_dt,
                'entry_timestamp': trade_dt,
                'exit_timestamp': result.get('exit_timestamp', trade_dt),
                'time_index': i,
                'symbol': symbol,
                'direction': signal.direction,
                'entry': signal.entry_price,
                'stop_loss': signal.stop_price,
                'take_profit': signal.take_profit,
                'position_size': position_size,
                'dollar_risk': details['actual_risk_usd'],
                'risk_percent': details['actual_risk_pct'],
                'result': result['pnl'],
                'r_achieved': result['r_achieved'],
                'status': 'win' if result['pnl'] > 0 else 'loss',
                'duration_minutes': result.get('duration_minutes', 0),
                'tp_hit': result.get('tp_hit', None)
            }
            
            self.trades.append(trade_record)
            
            # Update equity
            self.current_equity += result['pnl']
            
            # Update equity curve
            equity_ts = trade_dt
            if i + 1 < len(candles):
                next_candle_ts = candles[i + 1].get('timestamp', i + 1)
                if isinstance(next_candle_ts, (int, float)) and next_candle_ts > 0:
                    try:
                        equity_ts = datetime.fromtimestamp(next_candle_ts)
                    except (ValueError, OSError):
                        pass
            
            self.equity_curve.append({
                'timestamp': equity_ts,
                'time': i,
                'equity': self.current_equity
            })
            
            # Update max equity and drawdown
            if self.current_equity > self.max_equity:
                self.max_equity = self.current_equity
            
            drawdown = self.max_equity - self.current_equity
            drawdown_pct = (drawdown / self.max_equity) * 100.0
            
            if drawdown_pct > self.max_drawdown_pct:
                self.max_drawdown = drawdown
                self.max_drawdown_pct = drawdown_pct
        
        # Calculate performance metrics
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        metrics = self._calculate_metrics()
        
        # Add backtest metadata
        metrics['backtest_metadata'] = {
            'start_time': start_time,
            'end_time': end_time,
            'duration_seconds': duration,
            'symbol': symbol,
            'start_equity': float(start_equity),
            'candles_analyzed': len(candles),
            'strategy': 'AJR'
        }
        
        return metrics
    
    def _simulate_ajr_trade_outcome(self, signal: TradeSignal, position_size: int,
                                   candles: List[Dict], start_idx: int,
                                   entry_timestamp: datetime) -> Dict:
        """
        Simulate AJR trade outcome with multiple TPs.
        
        AJR has 2 TPs, so we need to:
        1. Check if stop is hit first
        2. If not, check if TP1 is hit (close partial position)
        3. If TP1 hit, check if TP2 is hit (close remaining)
        4. Calculate weighted P&L based on which TPs were hit
        
        Args:
            signal: Trade signal
            position_size: Position size in contracts
            candles: Remaining candle data
            start_idx: Index to start from
            entry_timestamp: Entry timestamp
        
        Returns:
            Dictionary with pnl, r_achieved, exit_timestamp, duration_minutes, tp_hit
        """
        if start_idx >= len(candles):
            return {
                'pnl': 0, 
                'r_achieved': 0, 
                'exit_timestamp': None, 
                'duration_minutes': 0,
                'tp_hit': None
            }
        
        entry = signal.entry_price
        stop = signal.stop_price
        tps = signal.take_profit  # List of TP prices
        direction = signal.direction
        
        # Get instrument specs for R calculation
        specs = self.risk_manager.get_instrument_specs(signal.instrument)
        tick_size = specs.get('tick_size', 0.25)
        tick_value = specs.get('tick_value', 5.0)
        
        # Calculate stop distance in ticks and dollars
        stop_distance_points = abs(entry - stop)
        stop_distance_ticks = stop_distance_points / tick_size
        stop_risk_dollars = stop_distance_ticks * tick_value
        
        # Check remaining candles
        contracts_remaining = position_size
        total_pnl = 0.0
        tp_hit = None
        
        # For simplicity, we'll use 1 contract per TP level
        # If position_size = 2, TP1 gets 1 contract, TP2 gets 1 contract
        # If position_size = 3, TP1 gets 1, TP2 gets 1, TP3 gets 1 (if exists)
        tp_contracts = []
        if len(tps) >= 1:
            tp_contracts.append(min(1, position_size))  # TP1: 1 contract
        if len(tps) >= 2:
            tp_contracts.append(min(1, position_size - sum(tp_contracts)))  # TP2: 1 contract
        if len(tps) >= 3:
            tp_contracts.append(position_size - sum(tp_contracts))  # Remaining to TP3
        
        # Ensure we have enough contracts
        while sum(tp_contracts) < position_size and len(tp_contracts) < len(tps):
            tp_contracts.append(1)
        
        # Limit to position size
        tp_contracts = tp_contracts[:position_size]
        
        max_lookahead = min(start_idx + 200, len(candles))  # Look ahead up to 200 candles
        
        for i in range(start_idx, max_lookahead):
            candle = candles[i]
            high = candle['high']
            low = candle['low']
            
            # Get exit timestamp
            exit_ts = candle.get('timestamp', i)
            if isinstance(exit_ts, (int, float)) and exit_ts > 0:
                try:
                    exit_timestamp = datetime.fromtimestamp(exit_ts)
                except (ValueError, OSError):
                    exit_timestamp = datetime.now()
            else:
                exit_timestamp = datetime.now()
            
            # Calculate duration
            duration_delta = exit_timestamp - entry_timestamp
            duration_minutes = duration_delta.total_seconds() / 60.0
            
            # Check if stop hit
            if direction == "BUY" and low <= stop:
                # Stop loss hit - lose all remaining contracts
                # Calculate loss in dollars: (entry - stop) in ticks × tick_value
                loss_ticks = (entry - stop) / tick_size
                loss_per_contract = loss_ticks * tick_value
                total_pnl = -loss_per_contract * contracts_remaining
                r_achieved = -1.0
                return {
                    'pnl': total_pnl,
                    'r_achieved': r_achieved,
                    'exit_timestamp': exit_timestamp,
                    'duration_minutes': duration_minutes,
                    'tp_hit': 'STOP'
                }
            elif direction == "SELL" and high >= stop:
                # Stop loss hit
                loss_ticks = (stop - entry) / tick_size
                loss_per_contract = loss_ticks * tick_value
                total_pnl = -loss_per_contract * contracts_remaining
                r_achieved = -1.0
                return {
                    'pnl': total_pnl,
                    'r_achieved': r_achieved,
                    'exit_timestamp': exit_timestamp,
                    'duration_minutes': duration_minutes,
                    'tp_hit': 'STOP'
                }
            
            # Check TPs in order
            for tp_idx, tp_price in enumerate(tps):
                if tp_idx >= len(tp_contracts) or tp_contracts[tp_idx] == 0:
                    continue
                
                contracts_at_tp = tp_contracts[tp_idx]
                
                # Check if TP hit
                if direction == "BUY" and high >= tp_price:
                    # TP hit - calculate profit in dollars
                    profit_ticks = (tp_price - entry) / tick_size
                    profit_per_contract = profit_ticks * tick_value
                    pnl_at_tp = profit_per_contract * contracts_at_tp
                    total_pnl += pnl_at_tp
                    contracts_remaining -= contracts_at_tp
                    tp_contracts[tp_idx] = 0  # Mark as filled
                    
                    if tp_hit is None:
                        tp_hit = f"TP{tp_idx+1}"
                    else:
                        tp_hit += f"+TP{tp_idx+1}"
                    
                    # If all contracts closed, exit
                    if contracts_remaining <= 0:
                        # Calculate R achieved: total P&L / (stop risk per contract × position size)
                        # R = total_profit / total_risk
                        total_risk = stop_risk_dollars * position_size
                        r_achieved = total_pnl / total_risk if total_risk > 0 else 0
                        return {
                            'pnl': total_pnl,
                            'r_achieved': r_achieved,
                            'exit_timestamp': exit_timestamp,
                            'duration_minutes': duration_minutes,
                            'tp_hit': tp_hit
                        }
                
                elif direction == "SELL" and low <= tp_price:
                    # TP hit - calculate profit in dollars
                    profit_ticks = (entry - tp_price) / tick_size
                    profit_per_contract = profit_ticks * tick_value
                    pnl_at_tp = profit_per_contract * contracts_at_tp
                    total_pnl += pnl_at_tp
                    contracts_remaining -= contracts_at_tp
                    tp_contracts[tp_idx] = 0
                    
                    if tp_hit is None:
                        tp_hit = f"TP{tp_idx+1}"
                    else:
                        tp_hit += f"+TP{tp_idx+1}"
                    
                    # If all contracts closed, exit
                    if contracts_remaining <= 0:
                        # Calculate R achieved
                        total_risk = stop_risk_dollars * position_size
                        r_achieved = total_pnl / total_risk if total_risk > 0 else 0
                        return {
                            'pnl': total_pnl,
                            'r_achieved': r_achieved,
                            'exit_timestamp': exit_timestamp,
                            'duration_minutes': duration_minutes,
                            'tp_hit': tp_hit
                        }
        
        # No outcome (end of data) - calculate partial fills if any
        if contracts_remaining < position_size:
            # Some TPs hit, calculate weighted R based on filled contracts
            filled_contracts = position_size - contracts_remaining
            total_risk = stop_risk_dollars * filled_contracts
            r_achieved = total_pnl / total_risk if total_risk > 0 else 0
        else:
            r_achieved = 0
        
        # Get last candle timestamp
        if len(candles) > start_idx:
            last_candle = candles[-1]
            exit_ts = last_candle.get('timestamp', len(candles) - 1)
            if isinstance(exit_ts, (int, float)) and exit_ts > 0:
                try:
                    exit_timestamp = datetime.fromtimestamp(exit_ts)
                except (ValueError, OSError):
                    exit_timestamp = datetime.now()
            else:
                exit_timestamp = datetime.now()
            duration_delta = exit_timestamp - entry_timestamp
            duration_minutes = duration_delta.total_seconds() / 60.0
        else:
            exit_timestamp = entry_timestamp
            duration_minutes = 0
        
        return {
            'pnl': total_pnl,
            'r_achieved': r_achieved,
            'exit_timestamp': exit_timestamp,
            'duration_minutes': duration_minutes,
            'tp_hit': tp_hit if tp_hit else 'NONE'
        }
    
    def _calculate_metrics(self) -> Dict:
        """Calculate comprehensive backtest performance metrics (same as AAFR)."""
        if not self.trades:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'avg_r': 0.0,
                'net_pnl': 0.0,
                'max_drawdown': 0.0,
                'max_drawdown_pct': 0.0,
                'longest_win_streak': 0,
                'longest_loss_streak': 0,
                'final_equity': self.current_equity,
                'equity_curve': self.equity_curve,
                'profit_factor': 0.0,
                'sharpe_ratio': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'avg_win_r': 0.0,
                'avg_loss_r': 0.0,
                'gross_profit': 0.0,
                'gross_loss': 0.0,
                'expectancy': 0.0,
                'avg_trade_duration': 0.0
            }
        
        # Basic metrics (same calculation as AAFR backtester)
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t['status'] == 'win']
        losing_trades = [t for t in self.trades if t['status'] == 'loss']
        
        win_rate = (len(winning_trades) / total_trades) * 100.0
        avg_r = sum(t['r_achieved'] for t in self.trades) / total_trades
        net_pnl = sum(t['result'] for t in self.trades)
        
        gross_profit = sum(t['result'] for t in winning_trades) if winning_trades else 0.0
        gross_loss = abs(sum(t['result'] for t in losing_trades)) if losing_trades else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)
        
        avg_win = gross_profit / len(winning_trades) if winning_trades else 0.0
        avg_loss = abs(sum(t['result'] for t in losing_trades) / len(losing_trades)) if losing_trades else 0.0
        avg_win_r = sum(t['r_achieved'] for t in winning_trades) / len(winning_trades) if winning_trades else 0.0
        avg_loss_r = abs(sum(t['r_achieved'] for t in losing_trades) / len(losing_trades)) if losing_trades else 0.0
        
        win_rate_decimal = win_rate / 100.0
        loss_rate_decimal = 1.0 - win_rate_decimal
        expectancy = (win_rate_decimal * avg_win) - (loss_rate_decimal * avg_loss)
        
        durations = [t.get('duration_minutes', 0) for t in self.trades if t.get('duration_minutes', 0) > 0]
        avg_trade_duration = sum(durations) / len(durations) if durations else 0.0
        
        returns = [t['result'] for t in self.trades]
        if len(returns) > 1:
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            std_dev = math.sqrt(variance) if variance > 0 else 0.0
            sharpe_ratio = (mean_return / std_dev * math.sqrt(252)) if std_dev > 0 else 0.0
        else:
            sharpe_ratio = 0.0
        
        # Streaks
        current_win_streak = 0
        current_loss_streak = 0
        max_win_streak = 0
        max_loss_streak = 0
        
        for trade in self.trades:
            if trade['status'] == 'win':
                current_win_streak += 1
                current_loss_streak = 0
                max_win_streak = max(max_win_streak, current_win_streak)
            else:
                current_loss_streak += 1
                current_win_streak = 0
                max_loss_streak = max(max_loss_streak, current_loss_streak)
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'avg_r': avg_r,
            'net_pnl': net_pnl,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_pct': self.max_drawdown_pct,
            'longest_win_streak': max_win_streak,
            'longest_loss_streak': max_loss_streak,
            'final_equity': self.current_equity,
            'equity_curve': self.equity_curve,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'avg_win_r': avg_win_r,
            'avg_loss_r': avg_loss_r,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'expectancy': expectancy,
            'avg_trade_duration': avg_trade_duration
        }
    
    def print_results(self, results: Dict):
        """Print backtest results (same format as AAFR)."""
        print(f"\n{'='*70}")
        print("AJR BACKTEST RESULTS")
        print(f"{'='*70}")
        print(f"Total Trades: {results['total_trades']}")
        print(f"Win Rate: {results['win_rate']:.2f}%")
        print(f"Average R: {results['avg_r']:.2f}")
        print(f"Net P&L: ${results['net_pnl']:.2f}")
        print(f"Final Equity: ${results['final_equity']:.2f}")
        print(f"Max Drawdown: ${results['max_drawdown']:.2f} ({results['max_drawdown_pct']:.2f}%)")
        print(f"Profit Factor: {results['profit_factor']:.2f}")
        print(f"Expectancy: ${results['expectancy']:.2f}")
        print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
        print(f"Average Trade Duration: {results['avg_trade_duration']:.1f} minutes")
        print(f"Longest Win Streak: {results['longest_win_streak']}")
        print(f"Longest Loss Streak: {results['longest_loss_streak']}")
        print(f"{'='*70}\n")
    
    def export_metrics(self, results: Dict, file_path: str):
        """Export metrics to JSON file."""
        from aafr.utils import export_json
        export_json(results, file_path)
    
    def export_equity_curve(self, results: Dict, file_path: str):
        """Export equity curve to CSV."""
        from aafr.utils import export_equity_curve_csv
        export_equity_curve_csv(results['equity_curve'], file_path)
    
    def plot_equity_curve(self, results: Dict, file_path: str, symbol: str = "N/A"):
        """Plot equity curve (if matplotlib available)."""
        try:
            from aafr.backtester import Backtester
            # Use AAFR backtester's plot method
            aafr_bt = Backtester()
            aafr_bt.equity_curve = results['equity_curve']
            aafr_bt.plot_equity_curve(results, file_path, symbol)
        except Exception as e:
            print(f"[WARNING] Could not plot equity curve: {e}")


def main():
    """
    Run backtests for both AAFR and AJR strategies.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Dual Strategy Backtester (AAFR + AJR)')
    parser.add_argument('--symbol', default='NQ', help='Trading symbol (NQ, ES, GC, CL)')
    parser.add_argument('--months', type=int, default=2, help='Number of months to backtest (1-3)')
    parser.add_argument('--data-file', help='Path to JSON file with candle data')
    parser.add_argument('--strategies', nargs='+', choices=['AAFR', 'AJR', 'BOTH'], 
                       default=['BOTH'], help='Which strategies to backtest')
    parser.add_argument('--start-equity', type=float, default=150000, 
                       help='Starting equity (default: 150000)')
    
    args = parser.parse_args()
    
    symbol = args.symbol.upper()
    strategies_to_run = args.strategies
    
    if 'BOTH' in strategies_to_run:
        strategies_to_run = ['AAFR', 'AJR']
    
    print("="*70)
    print("DUAL STRATEGY BACKTESTER - AAFR + AJR")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"  Symbol: {symbol}")
    print(f"  Strategies: {', '.join(strategies_to_run)}")
    print(f"  Start Equity: ${args.start_equity:,.2f}")
    print(f"  Period: {args.months} months")
    
    # Load or generate data
    print(f"\n[1/4] Preparing historical data...")
    
    if args.data_file:
        print(f"  Loading from: {args.data_file}")
        candles = load_candles_from_json(args.data_file)
        print(f"  [OK] Loaded {len(candles)} candles")
    else:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.months * 30)
        
        print(f"  Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Try API first, fall back to mock data
        api = TradovateAPI()
        api.authenticate()
        
        # Use micro symbol for data fetching
        micro_symbol = get_micro_symbol(symbol)
        candles = api.get_historical_candles(micro_symbol, count=10000)
        
        if not candles or len(candles) < 1000:
            print(f"  [INFO] Using mock data generation")
            candles = generate_mock_candles_for_period(
                start_date, end_date, micro_symbol, interval_minutes=5
            )
            print(f"  [OK] Generated {len(candles)} candles")
        else:
            print(f"  [OK] Loaded {len(candles)} candles from API")
    
    if len(candles) < 100:
        print(f"[ERROR] Insufficient data: {len(candles)} candles")
        return
    
    # Run backtests
    all_results = {}
    
    # AAFR Backtest
    if 'AAFR' in strategies_to_run:
        print(f"\n[2/4] Running AAFR backtest...")
        aafr_backtester = Backtester()
        aafr_results = aafr_backtester.run_backtest(candles, get_micro_symbol(symbol), args.start_equity)
        aafr_backtester.print_results(aafr_results)
        all_results['AAFR'] = {
            'results': aafr_results,
            'backtester': aafr_backtester
        }
    
    # AJR Backtest
    if 'AJR' in strategies_to_run:
        print(f"\n[3/4] Running AJR backtest...")
        ajr_backtester = AJRBacktester()
        ajr_results = ajr_backtester.run_backtest(candles, symbol, args.start_equity)
        ajr_backtester.print_results(ajr_results)
        all_results['AJR'] = {
            'results': ajr_results,
            'backtester': ajr_backtester
        }
    
    # Export results
    print(f"\n[4/4] Exporting results...")
    output_dir = Path("backtest_results/dual_strategy")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    for strategy_name, data in all_results.items():
        results = data['results']
        backtester = data['backtester']
        
        # Export metrics
        metrics_file = output_dir / f"{symbol}_{strategy_name}_metrics_{timestamp_str}.json"
        backtester.export_metrics(results, str(metrics_file))
        print(f"  [OK] {strategy_name} metrics: {metrics_file}")
        
        # Export equity curve CSV
        equity_csv_file = output_dir / f"{symbol}_{strategy_name}_equity_curve_{timestamp_str}.csv"
        backtester.export_equity_curve(results, str(equity_csv_file))
        print(f"  [OK] {strategy_name} equity curve CSV: {equity_csv_file}")
        
        # Export equity curve PNG
        try:
            equity_png_file = output_dir / f"{symbol}_{strategy_name}_equity_curve_{timestamp_str}.png"
            backtester.plot_equity_curve(results, str(equity_png_file), symbol)
            print(f"  [OK] {strategy_name} equity curve PNG: {equity_png_file}")
        except Exception as e:
            print(f"  [WARNING] Could not generate {strategy_name} equity curve plot: {e}")
    
    # Generate comparison summary
    if len(all_results) > 1:
        print(f"\n{'='*70}")
        print("STRATEGY COMPARISON")
        print(f"{'='*70}")
        print(f"\n{'Strategy':<10} {'Trades':<8} {'Win Rate':<12} {'Net P&L':<12} {'Avg R':<8} {'PF':<8} {'Expectancy':<12}")
        print("-" * 80)
        
        for strategy_name, data in all_results.items():
            results = data['results']
            trades = results['total_trades']
            win_rate = results['win_rate']
            pnl = results['net_pnl']
            avg_r = results['avg_r']
            pf = results.get('profit_factor', 0.0)
            exp = results.get('expectancy', 0.0)
            
            print(f"{strategy_name:<10} {trades:<8} {win_rate:>10.2f}%  ${pnl:>10.2f}  {avg_r:>6.2f}  {pf:>6.2f}  ${exp:>10.2f}")
        
        print(f"\n{'='*70}")
    
    print(f"\n{'='*70}")
    print("DUAL STRATEGY BACKTEST COMPLETE")
    print(f"{'='*70}")
    print(f"\nResults exported to: {output_dir}")
    print(f"\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nBacktest interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

