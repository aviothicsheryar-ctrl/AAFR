"""
Logging utilities for GUI Bot.
Comprehensive logging of events, actions, and errors.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class BotLogger:
    """
    Logger for GUI bot automation actions.
    Logs events, clicks, drags, and errors with timestamps.
    """
    
    def __init__(self, log_dir: str = "gui_bot/logs"):
        """
        Initialize bot logger.
        
        Args:
            log_dir: Directory for log files
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log filename with date
        date_str = datetime.now().strftime('%Y%m%d')
        log_file = self.log_dir / f"automation_{date_str}.log"
        
        # Setup logging
        self.logger = logging.getLogger('gui_bot')
        self.logger.setLevel(logging.DEBUG)
        
        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler (INFO and above)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers if not already added
        if not self.logger.handlers:
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
        
        # Metrics tracking
        self.metrics = {
            'events_received': 0,
            'clicks_executed': 0,
            'drags_executed': 0,
            'errors': 0,
            'retries': 0
        }
        
        self.logger.info("="*60)
        self.logger.info("GUI Bot Logger initialized")
        self.logger.info(f"Log file: {log_file}")
        self.logger.info("="*60)
    
    def log_event(self, event: Dict[str, Any]) -> None:
        """
        Log received event.
        
        Args:
            event: Event dictionary
        """
        event_type = event.get('event', 'UNKNOWN')
        self.metrics['events_received'] += 1
        
        # Log compact event info
        event_str = json.dumps(event, indent=None)
        if len(event_str) > 200:
            event_str = event_str[:200] + "..."
        
        self.logger.info(f"Event received: {event_type}")
        self.logger.debug(f"Event data: {event_str}")
    
    def log_click(self, side: str, order_type: str, price: float, 
                  qty: int, symbol: str, coordinates: tuple) -> None:
        """
        Log click action.
        
        Args:
            side: 'BUY' or 'SELL'
            order_type: 'LIMIT' or 'STOP'
            price: Order price
            qty: Quantity
            symbol: Trading symbol
            coordinates: (x, y) screen coordinates
        """
        self.metrics['clicks_executed'] += 1
        
        self.logger.info(
            f"Click: {side} {order_type} | {symbol} | "
            f"{qty}x @ {price} | Coords: {coordinates}"
        )
    
    def log_drag(self, symbol: str, from_price: float, to_price: float,
                 qty: int, reason: str) -> None:
        """
        Log drag action.
        
        Args:
            symbol: Trading symbol
            from_price: Original price
            to_price: Target price
            qty: Stop quantity
            reason: Reason for drag (e.g., 'TP1_BE_MOVE')
        """
        self.metrics['drags_executed'] += 1
        
        self.logger.info(
            f"Drag: {symbol} | Stop moved {from_price} → {to_price} | "
            f"Qty: {qty} | Reason: {reason}"
        )
    
    def log_position_update(self, symbol: str, action: str, details: str) -> None:
        """
        Log position state update.
        
        Args:
            symbol: Trading symbol
            action: Action type (e.g., 'OPENED', 'TP_FILLED', 'CLOSED')
            details: Additional details
        """
        self.logger.info(f"Position {action}: {symbol} | {details}")
    
    def log_error(self, error_msg: str, context: Optional[Dict] = None) -> None:
        """
        Log error with context.
        
        Args:
            error_msg: Error message
            context: Optional context dictionary
        """
        self.metrics['errors'] += 1
        
        if context:
            context_str = json.dumps(context, indent=None)
            self.logger.error(f"{error_msg} | Context: {context_str}")
        else:
            self.logger.error(error_msg)
    
    def log_retry(self, action: str, attempt: int, reason: str) -> None:
        """
        Log retry attempt.
        
        Args:
            action: Action being retried
            attempt: Attempt number
            reason: Reason for retry
        """
        self.metrics['retries'] += 1
        
        self.logger.warning(
            f"Retry {attempt}: {action} | Reason: {reason}"
        )
    
    def log_validation(self, check: str, passed: bool, details: str = "") -> None:
        """
        Log validation check.
        
        Args:
            check: Check description
            passed: Whether check passed
            details: Additional details
        """
        status = "PASS" if passed else "FAIL"
        level = logging.INFO if passed else logging.WARNING
        
        msg = f"Validation [{status}]: {check}"
        if details:
            msg += f" | {details}"
        
        self.logger.log(level, msg)
    
    def log_metrics_summary(self) -> None:
        """Log current metrics summary."""
        self.logger.info("="*60)
        self.logger.info("Metrics Summary:")
        for key, value in self.metrics.items():
            self.logger.info(f"  {key}: {value}")
        self.logger.info("="*60)
    
    def info(self, msg: str) -> None:
        """Log info message."""
        self.logger.info(msg)
    
    def debug(self, msg: str) -> None:
        """Log debug message."""
        self.logger.debug(msg)
    
    def warning(self, msg: str) -> None:
        """Log warning message."""
        self.logger.warning(msg)
    
    def error(self, msg: str) -> None:
        """Log error message."""
        self.logger.error(msg)
    
    def get_metrics(self) -> Dict[str, int]:
        """Get current metrics."""
        return self.metrics.copy()


# Test logger
if __name__ == "__main__":
    print("Testing BotLogger...")
    
    logger = BotLogger("gui_bot/logs")
    
    # Test various log types
    logger.info("Test info message")
    logger.debug("Test debug message")
    logger.warning("Test warning")
    logger.error("Test error")
    
    # Test event logging
    test_event = {
        'event': 'NEW_POSITION',
        'symbol': 'NQ',
        'side': 'LONG',
        'size': 3
    }
    logger.log_event(test_event)
    
    # Test click logging
    logger.log_click('BUY', 'LIMIT', 20150.00, 3, 'NQ', (800, 400))
    
    # Test drag logging
    logger.log_drag('NQ', 20115.50, 20151.00, 2, 'TP1_BE_MOVE')
    
    # Test position update
    logger.log_position_update('NQ', 'OPENED', 'LONG 3 @ 20150.00')
    
    # Test validation
    logger.log_validation('DOM Focus', True, 'Tradovate window active')
    logger.log_validation('Coordinates', False, 'Out of bounds')
    
    # Test retry
    logger.log_retry('Drag Stop', 1, 'Failed to locate stop line')
    
    # Test metrics
    logger.log_metrics_summary()
    
    print("\n[OK] Logger test complete. Check gui_bot/logs/ for output.")

