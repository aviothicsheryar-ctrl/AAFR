"""
WebSocket server for broadcasting AAFR trade events to GUI bot clients.
Handles client connections and broadcasts JSON events in real-time.
"""

import asyncio
import json
import logging
from typing import Set, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from websockets.server import WebSocketServerProtocol
from datetime import datetime

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketServerProtocol = None  # Type placeholder when not available
    print("[WARNING] websockets library not installed. Install with: pip install websockets")


class WebSocketServer:
    """
    Async WebSocket server for broadcasting trade events.
    Maintains connections to multiple clients and broadcasts events to all.
    """
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        """
        Initialize WebSocket server.
        
        Args:
            host: Host address to bind to
            port: Port number to listen on
        """
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.server = None
        self.running = False
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
    async def start(self) -> None:
        """Start the WebSocket server."""
        if not WEBSOCKETS_AVAILABLE:
            self.logger.error("websockets library not available. Cannot start server.")
            print("[ERROR] WebSocket server cannot start: websockets library not installed")
            return
        
        self.running = True
        
        try:
            self.server = await websockets.serve(
                self.handle_client,
                self.host,
                self.port
            )
            print(f"[OK] WebSocket server started on ws://{self.host}:{self.port}")
            self.logger.info(f"WebSocket server listening on {self.host}:{self.port}")
            
            # Keep server running
            await asyncio.Future()  # Run forever
            
        except OSError as e:
            if "10048" in str(e) or "Address already in use" in str(e):
                self.logger.warning(f"Port {self.port} already in use. WebSocket server disabled.")
                print(f"[WARNING] Port {self.port} already in use. WebSocket server disabled.")
                print(f"[INFO] If you need WebSocket, close the process using port {self.port} or change port in config")
                self.running = False
                return
            else:
                self.logger.error(f"Failed to start WebSocket server: {e}")
                print(f"[ERROR] WebSocket server failed to start: {e}")
                self.running = False
        except Exception as e:
            self.logger.error(f"Failed to start WebSocket server: {e}")
            print(f"[ERROR] WebSocket server failed to start: {e}")
            self.running = False
    
    async def handle_client(self, websocket: "WebSocketServerProtocol", path: str) -> None:
        """
        Handle individual client connection.
        
        Args:
            websocket: Client WebSocket connection
            path: Connection path
        """
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        self.clients.add(websocket)
        print(f"[INFO] GUI Bot client connected: {client_id} (Total: {len(self.clients)})")
        self.logger.info(f"Client connected: {client_id}")
        
        try:
            # Send welcome message
            welcome = {
                "event": "CONNECTED",
                "message": "Connected to AAFR WebSocket server",
                "server_time": datetime.now().isoformat(),
                "client_id": client_id
            }
            await websocket.send(json.dumps(welcome))
            
            # Keep connection alive and listen for messages
            async for message in websocket:
                # Handle any client messages (if needed for future features)
                try:
                    data = json.loads(message)
                    self.logger.debug(f"Received from {client_id}: {data}")
                    
                    # Handle ping/pong for keepalive
                    if data.get("event") == "PING":
                        pong = {"event": "PONG", "timestamp": datetime.now().isoformat()}
                        await websocket.send(json.dumps(pong))
                        
                except json.JSONDecodeError:
                    self.logger.warning(f"Invalid JSON from {client_id}: {message}")
                    
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"Client disconnected: {client_id}")
            
        except Exception as e:
            self.logger.error(f"Error handling client {client_id}: {e}")
            
        finally:
            self.clients.discard(websocket)
            print(f"[INFO] GUI Bot client disconnected: {client_id} (Remaining: {len(self.clients)})")
    
    async def broadcast_event(self, event: Dict[str, Any]) -> None:
        """
        Broadcast event to all connected clients.
        
        Args:
            event: Event dictionary to broadcast
        """
        if not self.clients:
            self.logger.debug("No clients connected, skipping broadcast")
            return
        
        # Add timestamp if not present
        if "timestamp" not in event:
            event["timestamp"] = datetime.now().isoformat()
        
        message = json.dumps(event)
        self.logger.info(f"Broadcasting event: {event.get('event', 'UNKNOWN')} to {len(self.clients)} clients")
        print(f"[WS] Broadcasting {event.get('event', 'UNKNOWN')} event to {len(self.clients)} client(s)")
        
        # Broadcast to all clients
        disconnected = set()
        for client in self.clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
                self.logger.warning("Client connection closed during broadcast")
            except Exception as e:
                self.logger.error(f"Error broadcasting to client: {e}")
                disconnected.add(client)
        
        # Remove disconnected clients
        for client in disconnected:
            self.clients.discard(client)
    
    def broadcast_sync(self, event: Dict[str, Any]) -> None:
        """
        Synchronous wrapper for broadcast_event.
        Creates async task to broadcast event.
        
        Args:
            event: Event dictionary to broadcast
        """
        if not self.running:
            self.logger.warning("WebSocket server not running, cannot broadcast")
            return
        
        # Create task in the event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.broadcast_event(event))
            else:
                loop.run_until_complete(self.broadcast_event(event))
        except RuntimeError:
            # No event loop running
            self.logger.warning("No event loop available for broadcasting")
    
    async def stop(self) -> None:
        """Stop the WebSocket server."""
        self.running = False
        
        # Close all client connections
        if self.clients:
            await asyncio.gather(
                *[client.close() for client in self.clients],
                return_exceptions=True
            )
            self.clients.clear()
        
        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        print("[INFO] WebSocket server stopped")
        self.logger.info("WebSocket server stopped")


# Standalone test
if __name__ == "__main__":
    import logging
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    async def test_server():
        """Test the WebSocket server."""
        server = WebSocketServer("localhost", 8765)
        
        # Start server in background
        server_task = asyncio.create_task(server.start())
        
        # Wait a bit for server to start
        await asyncio.sleep(1)
        
        # Simulate broadcasting some events
        test_events = [
            {
                "event": "NEW_POSITION",
                "symbol": "NQ",
                "side": "LONG",
                "entry_price": 20150.00,
                "size": 3
            },
            {
                "event": "TP_FILLED",
                "symbol": "NQ",
                "tp_level": 1,
                "remaining_size": 2
            }
        ]
        
        for event in test_events:
            await asyncio.sleep(2)
            await server.broadcast_event(event)
        
        # Keep running
        await server_task
    
    try:
        print("Starting WebSocket server test...")
        print("Connect a client to ws://localhost:8765 to see events")
        print("Press Ctrl+C to stop")
        asyncio.run(test_server())
    except KeyboardInterrupt:
        print("\nServer stopped by user")

