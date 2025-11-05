"""
AAFR - Andrew's Automated Futures Routine

A modular algorithmic trading system integrating:
- ICC (Indication-Correction-Continuation) pattern detection
- CVD (Cumulative Volume Delta) order flow analysis
- TPT 150K risk management rules
- Tradovate API integration
- Backtesting capabilities
"""

__version__ = "1.0.0"
__author__ = "AAFR Team"

from .icc_module import ICCDetector
from .cvd_module import CVDCalculator
from .risk_engine import RiskEngine
from .tradovate_api import TradovateAPI
from .backtester import Backtester

__all__ = [
    'ICCDetector',
    'CVDCalculator',
    'RiskEngine',
    'TradovateAPI',
    'Backtester'
]

