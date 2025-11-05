"""
Backtesting module for AAFR strategy performance analysis.
Calculates win rate, R multiples, drawdown, and equity curve.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import csv
import math

from aafr.icc_module import ICCDetector
from aafr.cvd_module import CVDCalculator
from aafr.risk_engine import RiskEngine
from aafr.utils import log_trade_signal, get_formatted_timestamp, export_json, export_equity_curve_csv


class Backtester:
    """
    Backtesting engine for ICC + CVD strategy.
    Simulates trades on historical data and calculates performance metrics.
    """
    
    def __init__(self, config_path: str = "config.json"):
        """
        Initialize Backtester.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.icc_detector = ICCDetector()
        self.cvd_calculator = CVDCalculator()
        self.risk_engine = RiskEngine(config_path)
        
        # Performance tracking
        self.trades = []
        self.equity_curve = []
        self.current_equity = 100000.0  # Starting equity
        self.max_equity = self.current_equity
        self.max_drawdown = 0.0
        self.max_drawdown_pct = 0.0
    
    def run_backtest(self, candles: List[Dict], symbol: str, 
                    start_equity: float = 100000) -> Dict:
        """
        Run backtest on historical candle data.
        
        Args:
            candles: Historical candle data
            symbol: Trading symbol
            start_equity: Starting equity
        
        Returns:
            Dictionary with backtest results including timestamps
        """
        start_time = datetime.now()
        
        self.current_equity = float(start_equity)
        self.max_equity = float(start_equity)
        self.trades = []
        
        # Initialize equity curve with timestamp
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
        
        # Reset detectors
        self.icc_detector.reset()
        self.cvd_calculator.reset()
        self.risk_engine.reset_daily_tracking()
        
        # Scan through candles for trade setups
        lookahead = 50  # Minimum candles needed for structure detection
        
        for i in range(lookahead, len(candles)):
            # Get history up to current point
            history = candles[:i+1]
            
            # Detect ICC structure
            icc_structure = self.icc_detector.detect_icc_structure(
                history, require_all_phases=True
            )
            
            if not icc_structure or not icc_structure.get('complete'):
                continue
            
            # Validate setup
            is_valid, violations = self.icc_detector.validate_full_setup(
                icc_structure, history
            )
            
            if not is_valid:
                continue
            
            # Calculate entry, stop, and take profit
            entry, stop, tp, r_multiple = self._calculate_trade_levels(
                icc_structure, history, symbol
            )
            
            if r_multiple < 2.0:
                continue
            
            # Validate with risk engine
            is_risk_valid, msg, trade_details = self.risk_engine.validate_trade_setup(
                entry, stop, icc_structure['indication']['direction'], symbol, history
            )
            
            if not is_risk_valid:
                continue
            
            # Calculate actual outcome
            result = self._simulate_trade_outcome(
                entry, stop, tp, trade_details['r_multiple'], 
                trade_details['position_size'], icc_structure['indication']['direction'],
                candles, i+1  # Start from next candle
            )
            
            # Get timestamp for trade
            trade_timestamp = i
            if i < len(candles):
                candle_ts = candles[i].get('timestamp', i)
                if isinstance(candle_ts, (int, float)) and candle_ts > 0:
                    try:
                        trade_dt = datetime.fromtimestamp(candle_ts)
                    except (ValueError, OSError):
                        trade_dt = datetime.now()
                else:
                    trade_dt = datetime.now()
            else:
                trade_dt = datetime.now()
            
            # Record trade
            trade_record = {
                'timestamp': trade_dt,
                'time_index': i,
                'symbol': symbol,
                'direction': icc_structure['indication']['direction'],
                'entry': entry,
                'stop_loss': stop,
                'take_profit': tp,
                'r_multiple': r_multiple,
                'position_size': trade_details['position_size'],
                'dollar_risk': trade_details['dollar_risk'],
                'risk_percent': trade_details['risk_percent'],
                'result': result['pnl'],
                'r_achieved': result['r_achieved'],
                'status': 'win' if result['pnl'] > 0 else 'loss'
            }
            
            self.trades.append(trade_record)
            
            # Update equity
            self.current_equity += result['pnl']
            
            # Add timestamp to equity curve point
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
            'candles_analyzed': len(candles)
        }
        
        return metrics
    
    def _calculate_trade_levels(self, icc_structure: Dict, 
                               candles: List[Dict], symbol: str) -> Tuple[float, float, float, float]:
        """
        Calculate entry, stop, take profit, and R multiple for trade setup.
        
        Args:
            icc_structure: ICC structure dictionary
            candles: Candle history
            symbol: Trading symbol
        
        Returns:
            Tuple of (entry, stop, tp, r_multiple)
        """
        # Entry: continuation candle close
        continuation_candle = icc_structure['continuation']['candle']
        entry = continuation_candle['close']
        direction = icc_structure['indication']['direction']
        
        # Stop: beyond invalidation (correction low for LONG, high for SHORT)
        correction_candles = candles[
            icc_structure['correction']['start_idx']:
            icc_structure['correction']['end_idx']+1
        ]
        
        if direction == 'LONG':
            stop = min(c['low'] for c in correction_candles) - (entry * 0.001)  # Small buffer
        else:
            stop = max(c['high'] for c in correction_candles) + (entry * 0.001)
        
        # R multiple
        r_multiple = self.icc_detector.calculate_r_multiple(entry, stop, candles, 3.0)
        
        # Take profit based on R multiple
        risk_distance = abs(entry - stop)
        reward_distance = risk_distance * r_multiple
        
        if direction == 'LONG':
            tp = entry + reward_distance
        else:
            tp = entry - reward_distance
        
        return (entry, stop, tp, r_multiple)
    
    def _simulate_trade_outcome(self, entry: float, stop: float, tp: float,
                               r_multiple: float, position_size: int,
                               direction: str, candles: List[Dict], 
                               start_idx: int) -> Dict:
        """
        Simulate trade outcome from historical data.
        
        Args:
            entry: Entry price
            stop: Stop loss price
            tp: Take profit price
            r_multiple: R multiple
            position_size: Position size in contracts
            direction: 'LONG' or 'SHORT'
            candles: Remaining candle data
            start_idx: Index to start from
        
        Returns:
            Dictionary with pnl and r_achieved
        """
        if start_idx >= len(candles):
            return {'pnl': 0, 'r_achieved': 0}
        
        # Check remaining candles for stop or TP hit
        for i in range(start_idx, min(start_idx + 100, len(candles))):
            candle = candles[i]
            high = candle['high']
            low = candle['low']
            
            # Check if stop hit
            if direction == 'LONG' and low <= stop:
                # Stop loss hit
                loss = (entry - stop) * position_size
                return {'pnl': -loss, 'r_achieved': -1.0}
            elif direction == 'SHORT' and high >= stop:
                # Stop loss hit
                loss = (stop - entry) * position_size
                return {'pnl': -loss, 'r_achieved': -1.0}
            
            # Check if TP hit
            if direction == 'LONG' and high >= tp:
                # Take profit hit
                profit = (tp - entry) * position_size
                return {'pnl': profit, 'r_achieved': r_multiple}
            elif direction == 'SHORT' and low <= tp:
                # Take profit hit
                profit = (entry - tp) * position_size
                return {'pnl': profit, 'r_achieved': r_multiple}
        
        # No outcome (end of data)
        return {'pnl': 0, 'r_achieved': 0}
    
    def _calculate_metrics(self) -> Dict:
        """
        Calculate comprehensive backtest performance metrics.
        
        Includes:
        - Basic metrics (win rate, avg R, net P&L)
        - Extended metrics (profit factor, Sharpe ratio, win/loss R multiples)
        - Equity curve summary (min/max equity, peak equity date)
        - Streak analysis
        
        Returns:
            Dictionary with performance metrics
        """
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
                'equity_curve_summary': {
                    'min_equity': self.current_equity,
                    'max_equity': self.current_equity,
                    'peak_equity_date': None,
                    'peak_equity_value': self.current_equity
                }
            }
        
        # Basic metrics
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t['status'] == 'win']
        losing_trades = [t for t in self.trades if t['status'] == 'loss']
        
        win_rate = (len(winning_trades) / total_trades) * 100.0
        
        # Average R multiple
        avg_r = sum(t['r_achieved'] for t in self.trades) / total_trades
        
        # Net P&L
        net_pnl = sum(t['result'] for t in self.trades)
        
        # Profit Factor: Gross Profit / Gross Loss
        gross_profit = sum(t['result'] for t in winning_trades) if winning_trades else 0.0
        gross_loss = abs(sum(t['result'] for t in losing_trades)) if losing_trades else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)
        
        # Average win/loss sizes
        avg_win = gross_profit / len(winning_trades) if winning_trades else 0.0
        avg_loss = abs(sum(t['result'] for t in losing_trades) / len(losing_trades)) if losing_trades else 0.0
        
        # Average win/loss R multiples
        avg_win_r = sum(t['r_achieved'] for t in winning_trades) / len(winning_trades) if winning_trades else 0.0
        avg_loss_r = abs(sum(t['r_achieved'] for t in losing_trades) / len(losing_trades)) if losing_trades else 0.0
        
        # Sharpe Ratio (simplified: annualized return / volatility)
        # Calculate returns for each trade
        returns = [t['result'] for t in self.trades]
        if len(returns) > 1:
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            std_dev = math.sqrt(variance) if variance > 0 else 0.0
            sharpe_ratio = (mean_return / std_dev * math.sqrt(252)) if std_dev > 0 else 0.0  # Annualized
        else:
            sharpe_ratio = 0.0
        
        # Equity curve summary
        if self.equity_curve:
            equity_values = [point['equity'] for point in self.equity_curve]
            min_equity = min(equity_values)
            max_equity = max(equity_values)
            
            # Find peak equity date
            peak_equity_point = max(self.equity_curve, key=lambda x: x['equity'])
            peak_equity_date = peak_equity_point.get('timestamp', None)
        else:
            # Handle empty equity curve (shouldn't happen in normal operation)
            min_equity = self.current_equity
            max_equity = self.current_equity
            peak_equity_date = None
        
        equity_curve_summary = {
            'min_equity': min_equity,
            'max_equity': max_equity,
            'peak_equity_date': peak_equity_date,
            'peak_equity_value': max_equity
        }
        
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
            'wins': len(winning_trades),
            'losses': len(losing_trades),
            'equity_curve': self.equity_curve,
            # Extended metrics
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'avg_win_r': avg_win_r,
            'avg_loss_r': avg_loss_r,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'equity_curve_summary': equity_curve_summary
        }
    
    def print_results(self, results: Dict) -> None:
        """
        Print formatted backtest results including extended metrics.
        
        Args:
            results: Results dictionary from run_backtest
        """
        print("\n" + "="*60)
        print("BACKTEST RESULTS")
        print("="*60)
        print(f"Total Trades:       {results['total_trades']}")
        print(f"Wins:               {results.get('wins', 0)}")
        print(f"Losses:             {results.get('losses', 0)}")
        print(f"Win Rate:           {results['win_rate']:.2f}%")
        print(f"Average R:          {results['avg_r']:.2f}")
        print(f"Net P&L:            ${results['net_pnl']:.2f}")
        print(f"Final Equity:       ${results['final_equity']:.2f}")
        print(f"Max Drawdown:       ${results['max_drawdown']:.2f} ({results['max_drawdown_pct']:.2f}%)")
        print(f"Longest Win Streak:  {results['longest_win_streak']}")
        print(f"Longest Loss Streak: {results['longest_loss_streak']}")
        
        # Extended metrics
        if 'profit_factor' in results:
            print(f"\nExtended Metrics:")
            print(f"Profit Factor:     {results['profit_factor']:.2f}")
            print(f"Sharpe Ratio:       {results.get('sharpe_ratio', 0.0):.2f}")
            print(f"Avg Win:            ${results.get('avg_win', 0.0):.2f}")
            print(f"Avg Loss:           ${results.get('avg_loss', 0.0):.2f}")
            print(f"Avg Win R:          {results.get('avg_win_r', 0.0):.2f}")
            print(f"Avg Loss R:         {results.get('avg_loss_r', 0.0):.2f}")
            print(f"Gross Profit:       ${results.get('gross_profit', 0.0):.2f}")
            print(f"Gross Loss:         ${results.get('gross_loss', 0.0):.2f}")
        
        # Equity curve summary
        if 'equity_curve_summary' in results:
            summary = results['equity_curve_summary']
            print(f"\nEquity Curve Summary:")
            print(f"Min Equity:         ${summary['min_equity']:.2f}")
            print(f"Max Equity:         ${summary['max_equity']:.2f}")
            if summary.get('peak_equity_date'):
                peak_date = summary['peak_equity_date']
                if isinstance(peak_date, datetime):
                    print(f"Peak Equity Date:   {get_formatted_timestamp(peak_date)}")
                else:
                    print(f"Peak Equity Date:   {peak_date}")
        
        # Backtest metadata
        if 'backtest_metadata' in results:
            meta = results['backtest_metadata']
            print(f"\nBacktest Metadata:")
            print(f"Symbol:             {meta.get('symbol', 'N/A')}")
            print(f"Candles Analyzed:   {meta.get('candles_analyzed', 0)}")
            print(f"Duration:           {meta.get('duration_seconds', 0):.2f} seconds")
        
        print("="*60 + "\n")
    
    def export_equity_curve(self, results: Dict, file_path: str) -> None:
        """
        Export equity curve to CSV file.
        
        Args:
            results: Results dictionary from run_backtest
            file_path: Path to output CSV file
        """
        if 'equity_curve' in results:
            export_equity_curve_csv(results['equity_curve'], file_path)
    
    def export_metrics(self, results: Dict, file_path: str) -> None:
        """
        Export all metrics to JSON file.
        
        Args:
            results: Results dictionary from run_backtest
            file_path: Path to output JSON file
        """
        # Create exportable copy (convert datetime objects to strings)
        export_data = {}
        for key, value in results.items():
            if key == 'equity_curve':
                # Export equity curve separately, don't include in metrics
                continue
            elif isinstance(value, datetime):
                export_data[key] = get_formatted_timestamp(value)
            elif isinstance(value, dict):
                export_data[key] = {}
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, datetime):
                        export_data[key][sub_key] = get_formatted_timestamp(sub_value)
                    else:
                        export_data[key][sub_key] = sub_value
            else:
                export_data[key] = value
        
        export_json(export_data, file_path)


    def run_backtest_batch(self, candles_by_symbol: Dict[str, List[Dict]], 
                          start_equity: float = 100000) -> Dict[str, Dict]:
        """
        Run backtests for multiple instruments independently.
        
        Each instrument maintains independent state (separate ICC/CVD detectors).
        Useful for testing multiple instruments with the same strategy.
        
        Args:
            candles_by_symbol: Dictionary mapping symbol to candle data
            start_equity: Starting equity for each instrument
        
        Returns:
            Dictionary mapping symbol to backtest results
        """
        results = {}
        
        for symbol, candles in candles_by_symbol.items():
            print(f"\n{'='*60}")
            print(f"Running backtest for {symbol}")
            print(f"{'='*60}")
            
            # Create fresh backtester instance for each symbol (independent state)
            symbol_backtester = Backtester(self.config_path)
            symbol_results = symbol_backtester.run_backtest(candles, symbol, start_equity)
            results[symbol] = symbol_results
            
            # Print results for this symbol
            symbol_backtester.print_results(symbol_results)
        
        return results
    
    def run_multi_instrument_backtest(self, instruments: List[str], 
                                     candles_by_symbol: Dict[str, List[Dict]],
                                     start_equity: float = 100000) -> Dict[str, Dict]:
        """
        Run backtests across all specified instruments.
        
        Args:
            instruments: List of instrument symbols to backtest
            candles_by_symbol: Dictionary mapping symbol to candle data
            start_equity: Starting equity for each instrument
        
        Returns:
            Dictionary mapping symbol to backtest results
        """
        # Filter candles_by_symbol to only include requested instruments
        filtered_candles = {
            symbol: candles_by_symbol[symbol] 
            for symbol in instruments 
            if symbol in candles_by_symbol
        }
        
        return self.run_backtest_batch(filtered_candles, start_equity)


# Example usage
if __name__ == "__main__":
    from aafr.utils import generate_mock_candles
    
    # Generate mock historical data
    candles = generate_mock_candles(200, "MNQ")
    
    # Run backtest
    backtester = Backtester()
    results = backtester.run_backtest(candles, "MNQ")
    
    # Print results
    backtester.print_results(results)

