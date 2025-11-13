"""
GUI Bot Client - Main application.
Connects to AAFR WebSocket server and executes DOM automation.
"""

import asyncio
import json
import sys
from typing import Dict, Any, Optional
from datetime import datetime
import time

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    print("[ERROR] websockets library not installed. Install with: pip install websockets")
    sys.exit(1)

from gui_bot.position_tracker import PositionTracker
from gui_bot.dom_automation import DOMAutomator
from gui_bot.event_handlers import (
    handle_new_position,
    handle_tp_filled,
    handle_stop_update,
    handle_close_trade
)
from gui_bot.logger import BotLogger
from gui_bot.config import load_bot_config


class GUIBotClient:
    """
    Main GUI bot client.
    Connects to AAFR WebSocket server and handles trade events.
    """
    
    def __init__(self, config_path: str = "gui_bot/bot_config.json"):
        """
        Initialize GUI bot client.
        
        Args:
            config_path: Path to bot configuration file
        """
        self.config = load_bot_config(config_path)
        self.running = False
        self.websocket = None
        self.reconnect_delay = 1  # Start with 1 second
        self.max_reconnect_delay = 60  # Max 60 seconds
        
        # Initialize components
        self.tracker = PositionTracker()
        self.automator = DOMAutomator(self.config)
        self.logger = BotLogger()
        
        # Connection details
        aafr_config = self.config.get('aafr_connection', {})
        self.host = aafr_config.get('host', 'localhost')
        self.port = aafr_config.get('port', 8765)
        self.uri = f"ws://{self.host}:{self.port}"
        
        print(f"[INFO] GUI Bot initialized")
        print(f"[INFO] AAFR Server: {self.uri}")
    
    async def start(self) -> None:
        """Start the GUI bot client."""
        print("\n" + "="*60)
        print("AAFR GUI Bot Client")
        print("="*60)
        print(f"Connecting to AAFR at {self.uri}")
        print("Press Ctrl+C to stop\n")
        
        self.running = True
        
        while self.running:
            try:
                await self.connect()
            except KeyboardInterrupt:
                print("\n[INFO] Shutdown requested by user")
                self.running = False
                break
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                print(f"[ERROR] Unexpected error: {e}")
                
                if self.running:
                    print(f"[INFO] Reconnecting in {self.reconnect_delay} seconds...")
                    await asyncio.sleep(self.reconnect_delay)
                    # Exponential backoff
                    self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
    
    async def connect(self) -> None:
        """Establish WebSocket connection to AAFR."""
        try:
            async with websockets.connect(self.uri) as websocket:
                self.websocket = websocket
                self.reconnect_delay = 1  # Reset backoff on successful connection
                
                print(f"[OK] Connected to AAFR server")
                self.logger.info("Connected to AAFR WebSocket server")
                
                # Listen for messages
                async for message in websocket:
                    try:
                        event = json.loads(message)
                        await self.handle_event(event)
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Invalid JSON received: {e}")
                        print(f"[ERROR] Invalid JSON: {message[:100]}")
                    except Exception as e:
                        self.logger.error(f"Error handling event: {e}")
                        print(f"[ERROR] Error handling event: {e}")
                        
        except websockets.exceptions.ConnectionClosed:
            print("[WARNING] Connection to AAFR closed")
            self.logger.warning("Connection closed")
        except ConnectionRefusedError:
            print(f"[ERROR] Cannot connect to AAFR at {self.uri}")
            print("[INFO] Make sure AAFR is running with --mode live")
            self.logger.error(f"Connection refused: {self.uri}")
        except Exception as e:
            print(f"[ERROR] Connection error: {e}")
            self.logger.error(f"Connection error: {e}")
            raise
    
    async def handle_event(self, event: Dict[str, Any]) -> None:
        """
        Route event to appropriate handler.
        
        Args:
            event: Event dictionary from AAFR
        """
        event_type = event.get('event', 'UNKNOWN')
        timestamp = event.get('timestamp', datetime.now().isoformat())
        
        self.logger.log_event(event)
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Received {event_type} event")
        
        # Route to handler
        try:
            if event_type == 'CONNECTED':
                print(f"[OK] {event.get('message', 'Connected to server')}")
                # Send ping to keep connection alive
                await self.send_ping()
                
            elif event_type == 'NEW_POSITION':
                await handle_new_position(event, self.automator, self.tracker, self.logger)
                
            elif event_type == 'TP_FILLED':
                await handle_tp_filled(event, self.automator, self.tracker, self.logger)
                
            elif event_type == 'STOP_UPDATE':
                await handle_stop_update(event, self.automator, self.tracker, self.logger)
                
            elif event_type == 'CLOSE_TRADE':
                await handle_close_trade(event, self.automator, self.tracker, self.logger)
                
            elif event_type == 'PONG':
                # Keepalive response
                pass
                
            else:
                self.logger.warning(f"Unknown event type: {event_type}")
                print(f"[WARNING] Unknown event type: {event_type}")
                
        except Exception as e:
            self.logger.error(f"Handler error for {event_type}: {e}")
            print(f"[ERROR] Failed to handle {event_type}: {e}")
            import traceback
            traceback.print_exc()
    
    async def send_ping(self) -> None:
        """Send ping to server for keepalive."""
        if self.websocket:
            try:
                ping_msg = {
                    "event": "PING",
                    "timestamp": datetime.now().isoformat()
                }
                await self.websocket.send(json.dumps(ping_msg))
            except Exception as e:
                self.logger.warning(f"Failed to send ping: {e}")
    
    def stop(self) -> None:
        """Stop the GUI bot client."""
        self.running = False
        print("\n[INFO] GUI Bot stopping...")
        self.logger.info("GUI Bot stopped")


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='AAFR GUI Bot Client')
    parser.add_argument('--config', default='gui_bot/bot_config.json',
                       help='Path to bot configuration file')
    
    args = parser.parse_args()
    
    # Create and start client
    client = GUIBotClient(args.config)
    
    try:
        await client.start()
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
    finally:
        client.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")

