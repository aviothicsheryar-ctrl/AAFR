"""
Telegram bot integration for AAFR trading system.
Sends trade signal alerts to Telegram when valid signals are generated.
"""

import os
import requests
from typing import Dict, Optional
from pathlib import Path

try:
    from dotenv import load_dotenv
    # Load .env file from project root
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    # python-dotenv not installed
    pass


def format_telegram_message(signal: Dict) -> str:
    """
    Format trade signal message for Telegram.
    
    Args:
        signal: Trade signal dictionary with keys:
            - symbol: Trading symbol
            - direction: 'LONG' or 'SHORT'
            - entry: Entry price
            - stop_loss: Stop loss price
            - take_profit: Take profit price
            - r_multiple: R multiple
            - dollar_risk: Dollar risk amount
            - position_size: Position size in contracts
    
    Returns:
        Formatted message string
    """
    symbol = signal.get('symbol', 'UNKNOWN')
    direction = signal.get('direction', 'UNKNOWN')
    entry = signal.get('entry', 0)
    stop_loss = signal.get('stop_loss', 0)
    take_profit = signal.get('take_profit', 0)
    r_multiple = signal.get('r_multiple', 0)
    dollar_risk = signal.get('dollar_risk', 0)
    position_size = signal.get('position_size', 0)
    
    message = (
        f"[AAFR LIVE] {symbol} | {direction} @ {entry:.2f}\n"
        f"SL: {stop_loss:.2f} | TP: {take_profit:.2f}\n"
        f"R = {r_multiple:.1f} | Risk ${dollar_risk:.2f} | Size: {position_size} contracts"
    )
    
    return message


def send_telegram_alert(message: str) -> bool:
    """
    Send alert message to Telegram.
    
    Args:
        message: Message text to send
    
    Returns:
        True if message sent successfully, False otherwise
    """
    # Check if Telegram is enabled
    telegram_enabled = os.getenv('TELEGRAM_ENABLED', 'false').lower()
    
    if telegram_enabled != 'true':
        print("[INFO] Telegram alerts are disabled (TELEGRAM_ENABLED=false or not set)")
        return False
    
    # Get Telegram credentials
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        print("[WARNING] Telegram credentials not found in .env file")
        print("[WARNING] Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env to enable alerts")
        return False
    
    # Prepare API request
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML'  # Optional: allows basic HTML formatting
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        
        # Get response JSON
        try:
            result = response.json()
        except Exception:
            result = {}
        
        # Check if request was successful
        if response.status_code == 200 and result.get('ok'):
            print("[OK] Telegram alert sent successfully")
            return True
        else:
            # Extract error description from response
            error_desc = result.get('description', f'HTTP {response.status_code}')
            error_code = result.get('error_code', response.status_code)
            print(f"[ERROR] Telegram alert failed ({error_code}): {error_desc}")
            
            # Debug: Show helpful messages for common errors
            if "empty" in error_desc.lower() or "message text" in error_desc.lower():
                print(f"[DEBUG] Payload sent: {payload}")
                print(f"[DEBUG] Message length: {len(message) if message else 0}")
            elif "chat not found" in error_desc.lower() or "chat_id" in error_desc.lower():
                print(f"[INFO] Chat ID issue detected. Please verify:")
                print(f"  1. Chat ID is correct: {chat_id}")
                print(f"  2. You've sent /start to your bot")
                print(f"  3. Bot is in the chat/group you're trying to message")
            
            return False
            
    except requests.exceptions.Timeout:
        print("[ERROR] Telegram alert failed: Request timeout")
        return False
    except requests.exceptions.ConnectionError:
        print("[ERROR] Telegram alert failed: Connection error")
        return False
    except requests.exceptions.HTTPError as e:
        # Try to get error details from response
        try:
            error_data = e.response.json()
            error_desc = error_data.get('description', str(e))
            error_code = error_data.get('error_code', e.response.status_code)
            print(f"[ERROR] Telegram alert failed ({error_code}): {error_desc}")
        except Exception:
            print(f"[ERROR] Telegram alert failed: {str(e)}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Telegram alert failed: {str(e)}")
        return False
    except Exception as e:
        print(f"[ERROR] Telegram alert failed: Unexpected error - {str(e)}")
        return False

