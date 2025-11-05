"""
Test script for Telegram bot integration.
Sends a test message to verify Telegram connection and configuration.
"""

import sys
from pathlib import Path

# Add aafr to path
sys.path.insert(0, str(Path(__file__).parent))

from aafr.telegram_bot import send_telegram_alert


def main():
    """
    Send a test message to Telegram.
    """
    print("="*70)
    print("TELEGRAM BOT TEST")
    print("="*70)
    print("\nSending test message to Telegram...\n")
    
    test_message = "Test message from AAFR Telegram Bot - connection successful!"
    
    success = send_telegram_alert(test_message)
    
    if success:
        print("\n[OK] Telegram test completed successfully!")
        print("Check your Telegram chat to verify the message was received.")
    else:
        print("\n[WARNING] Telegram test failed.")
        print("Please check:")
        print("  1. .env file exists with TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_ENABLED=true")
        print("  2. Bot token is valid")
        print("  3. Chat ID is correct")
        print("  4. Bot has been started (send /start to your bot)")
        print("  5. Internet connection is available")
    
    print("="*70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

