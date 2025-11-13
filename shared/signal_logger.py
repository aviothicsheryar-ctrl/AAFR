"""
CSV logging for signals and executions.
Logs all signals from both AAFR and AJR strategies.
"""

import os
import csv
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from shared.signal_schema import TradeSignal


class SignalLogger:
    """
    Logs signals and executions to CSV files.
    Separate logs for signals and executions.
    """
    
    def __init__(self, log_dir: str = "logs/signals"):
        """Initialize signal logger."""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Log files
        date_str = datetime.now().strftime('%Y%m%d')
        self.signals_file = self.log_dir / f"signals_{date_str}.csv"
        self.executions_file = self.log_dir / f"executions_{date_str}.csv"
        
        # Initialize CSV files with headers
        self._init_signals_log()
        self._init_executions_log()
        
        print(f"[LOG] Signal Logger initialized")
        print(f"[LOG] Signals: {self.signals_file}")
        print(f"[LOG] Executions: {self.executions_file}")
    
    def _init_signals_log(self):
        """Initialize signals log file with headers."""
        if not self.signals_file.exists():
            with open(self.signals_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp',
                    'strategy_id',
                    'signal_id',
                    'instrument',
                    'direction',
                    'entry_price',
                    'stop_price',
                    'tp1',
                    'tp2',
                    'tp3',
                    'max_loss_usd',
                    'notes'
                ])
    
    def _init_executions_log(self):
        """Initialize executions log file with headers."""
        if not self.executions_file.exists():
            with open(self.executions_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp',
                    'strategy_id',
                    'signal_id',
                    'instrument',
                    'direction',
                    'status',
                    'position_size',
                    'entry_price',
                    'stop_price',
                    'risk_usd',
                    'risk_pct',
                    'r_multiple',
                    'reason'
                ])
    
    def log_signal(self, signal: TradeSignal):
        """
        Log trade signal to CSV.
        
        Args:
            signal: Trade signal to log
        """
        # Prepare TPs (up to 3)
        tps = signal.take_profit + [None] * (3 - len(signal.take_profit))
        
        row = [
            datetime.now().isoformat(),
            signal.strategy_id,
            signal.signal_id,
            signal.instrument,
            signal.direction,
            signal.entry_price,
            signal.stop_price,
            tps[0] if len(tps) > 0 else None,
            tps[1] if len(tps) > 1 else None,
            tps[2] if len(tps) > 2 else None,
            signal.max_loss_usd,
            signal.notes
        ]
        
        with open(self.signals_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(row)
    
    def log_execution(self, signal: TradeSignal, status: str,
                     position_size: int, risk_usd: float, risk_pct: float,
                     r_multiple: float, reason: str = ""):
        """
        Log execution result to CSV.
        
        Args:
            signal: Trade signal
            status: "ACCEPTED" or "REJECTED"
            position_size: Actual position size
            risk_usd: Dollar risk amount
            risk_pct: Risk percentage
            r_multiple: R multiple
            reason: Execution or rejection reason
        """
        row = [
            datetime.now().isoformat(),
            signal.strategy_id,
            signal.signal_id,
            signal.instrument,
            signal.direction,
            status,
            position_size,
            signal.entry_price,
            signal.stop_price,
            risk_usd,
            risk_pct,
            r_multiple,
            reason
        ]
        
        with open(self.executions_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(row)
    
    def log_arbiter_decision(self, signal: TradeSignal, accepted: bool,
                            reason: str, details: Optional[Dict[str, Any]] = None):
        """
        Log arbiter decision about signal.
        
        Args:
            signal: Trade signal
            accepted: Whether signal was accepted
            reason: Decision reason
            details: Optional execution details
        """
        # Log the signal itself
        self.log_signal(signal)
        
        # Log execution
        if accepted and details:
            self.log_execution(
                signal=signal,
                status="ACCEPTED",
                position_size=details.get('position_size', 0),
                risk_usd=details.get('risk_usd', 0),
                risk_pct=details.get('risk_pct', 0),
                r_multiple=details.get('r_multiples', [0])[0] if details.get('r_multiples') else 0,
                reason=reason
            )
        else:
            self.log_execution(
                signal=signal,
                status="REJECTED",
                position_size=0,
                risk_usd=0,
                risk_pct=0,
                r_multiple=0,
                reason=reason
            )


# Test
if __name__ == "__main__":
    print("Testing SignalLogger...")
    
    from shared.signal_schema import TradeSignal
    
    logger = SignalLogger("logs/signals")
    
    # Test AAFR signal
    aafr_signal = TradeSignal(
        strategy_id="AAFR",
        instrument="NQ",
        direction="BUY",
        entry_price=20150.00,
        stop_price=20115.50,
        take_profit=[20200.00, 20250.00, 20300.00],
        notes="ICC continuation"
    )
    
    logger.log_arbiter_decision(
        signal=aafr_signal,
        accepted=True,
        reason="Signal validated",
        details={
            'position_size': 3,
            'risk_usd': 517.50,
            'risk_pct': 0.35,
            'r_multiples': [2.9, 5.8, 8.7]
        }
    )
    
    # Test AJR signal (rejected)
    ajr_signal = TradeSignal(
        strategy_id="AJR",
        instrument="NQ",
        direction="SELL",
        entry_price=20145.00,
        stop_price=20160.00,
        take_profit=[20120.00, 20100.00],
        notes="Gap inversion"
    )
    
    logger.log_arbiter_decision(
        signal=ajr_signal,
        accepted=False,
        reason="Conflicting with AAFR signal",
        details=None
    )
    
    print(f"\n[OK] Logs written to {logger.log_dir}")
    print(f"  Signals: {logger.signals_file.name}")
    print(f"  Executions: {logger.executions_file.name}")

