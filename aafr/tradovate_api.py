"""
Tradovate API integration module for live and historical market data.
Supports both demo and live environments with graceful fallback to mock data.
"""

import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from aafr.utils import load_config, generate_mock_candles, generate_mock_volume_data


class TradovateAPI:
    """
    Wrapper for Tradovate Demo/Live API.
    Handles authentication, market data requests, and order placement.
    """
    
    def __init__(self, config_path: str = "config.json"):
        """
        Initialize Tradovate API client.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = load_config(config_path)
        self.environment = self.config['environment']
        self.api_config = self.config['tradovate'][self.environment]
        
        self.base_url = self.api_config['base_url']
        self.auth_url = self.api_config['auth_url']
        self.token = None
        self.token_expiry = None
        
        # Set up retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        self.session = requests.Session()
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        
        # Mock data fallback
        self.use_mock_data = False
    
    def authenticate(self) -> bool:
        """
        Authenticate with Tradovate API and obtain access token.
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            auth_data = {
                'grant_type': 'password',
                'client_id': self.api_config['client_id'],
                'client_secret': self.api_config['client_secret'],
                'username': self.api_config['username'],
                'password': self.api_config['password']
            }
            
            response = self.session.post(
                self.auth_url,
                json=auth_data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                auth_response = response.json()
                self.token = auth_response.get('access_token')
                expires_in = auth_response.get('expires_in', 3600)
                self.token_expiry = time.time() + expires_in - 60  # 1 min buffer
                
                print(f"[OK] Authenticated with Tradovate {self.environment} API")
                return True
            else:
                # Check if credentials are placeholder values
                if (self.api_config.get('client_id', '').startswith('YOUR_') or 
                    self.api_config.get('username', '').startswith('YOUR_')):
                    print(f"[INFO] Using placeholder API credentials - switching to mock data mode")
                else:
                    print(f"[ERROR] Authentication failed: HTTP {response.status_code}")
                    try:
                        error_msg = response.json().get('error', 'Unknown error')
                        print(f"[ERROR] Reason: {error_msg}")
                    except:
                        pass
                print("[INFO] Falling back to mock data for testing")
                self.use_mock_data = True
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Authentication error: {e}")
            print("Falling back to mock data for testing")
            self.use_mock_data = True
            return False
        except Exception as e:
            print(f"[ERROR] Unexpected auth error: {e}")
            self.use_mock_data = True
            return False
    
    def _ensure_authenticated(self) -> bool:
        """
        Ensure we have a valid authentication token.
        
        Returns:
            True if authenticated or using mock data
        """
        if self.use_mock_data:
            return True
        
        if self.token is None or (self.token_expiry and time.time() > self.token_expiry):
            return self.authenticate()
        return True
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """
        Make authenticated API request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            **kwargs: Additional arguments to pass to requests
        
        Returns:
            Response JSON or None if failed
        """
        if not self._ensure_authenticated():
            return None
        
        if self.use_mock_data:
            # Return mock response structure
            return None
        
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.pop('headers', {})
        headers['Authorization'] = f"Bearer {self.token}"
        headers['Content-Type'] = 'application/json'
        
        try:
            response = self.session.request(method, url, headers=headers, timeout=10, **kwargs)
            
            # Handle 401 Unauthorized - switch to mock data
            if response.status_code == 401:
                print(f"[WARNING] API request unauthorized (401). Switching to mock data mode.")
                self.use_mock_data = True
                return None
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 401:
                print(f"[WARNING] API request unauthorized (401). Switching to mock data mode.")
                self.use_mock_data = True
            else:
                print(f"[ERROR] API request failed: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] API request failed: {e}")
            return None
    
    def get_account_list(self) -> List[Dict]:
        """
        Retrieve list of trading accounts.
        
        Returns:
            List of account dictionaries
        """
        result = self._make_request('GET', '/account/list')
        
        if result is None:
            # Return mock account for testing
            return [{
                'accountId': 'mock_account',
                'accountName': 'Demo Account',
                'userId': 'mock_user',
                'status': 'active'
            }]
        
        return result if isinstance(result, list) else []
    
    def get_historical_candles(self, symbol: str, interval: str = "5Min", 
                               count: int = 100) -> List[Dict]:
        """
        Retrieve historical candle data for backtesting.
        
        Args:
            symbol: Trading instrument symbol (e.g., "MNQ")
            interval: Candle interval (e.g., "5Min", "15Min", "1Hour")
            count: Number of candles to retrieve
        
        Returns:
            List of candle dictionaries
        """
        if self.use_mock_data:
            # Don't print every time to avoid spam, only on first call
            if not hasattr(self, '_mock_data_notified'):
                print(f"[INFO] Using mock historical data for {symbol}")
                self._mock_data_notified = True
            return generate_mock_candles(count, symbol)
        
        # Historical data endpoint structure (adjust based on actual API docs)
        endpoint = f"/md/historicalBars"
        params = {
            'symbol': symbol,
            'interval': interval,
            'barCount': count
        }
        
        result = self._make_request('GET', endpoint, params=params)
        
        if result is None:
            # If we're in mock mode, the message was already printed
            if not self.use_mock_data:
                print(f"Failed to fetch historical data, using mock data for {symbol}")
            return generate_mock_candles(count, symbol)
        
        # Transform API response to standard candle format
        candles = []
        for bar in result.get('bars', []):
            candles.append({
                'timestamp': bar.get('time', 0),
                'open': float(bar.get('open', 0)),
                'high': float(bar.get('high', 0)),
                'low': float(bar.get('low', 0)),
                'close': float(bar.get('close', 0)),
                'volume': int(bar.get('volume', 0)),
                'symbol': symbol
            })
        
        return candles
    
    def subscribe_live_data(self, symbol: str, callback) -> bool:
        """
        Subscribe to live market data stream.
        Note: WebSocket implementation required for live streaming.
        
        Args:
            symbol: Trading instrument symbol
            callback: Function to call with new candle data
        
        Returns:
            True if subscription successful
        """
        if self.use_mock_data:
            print(f"Mock live data mode for {symbol}")
            # TODO: Implement mock streaming for testing
            return True
        
        # TODO: Implement WebSocket connection for live data
        # This would require websocket-client library
        print("Live data streaming not yet implemented")
        return False
    
    def place_order(self, order_details: Dict) -> Optional[Dict]:
        """
        Place a simulated order (paper trading in demo environment).
        
        Args:
            order_details: Dictionary containing order parameters
        
        Returns:
            Order confirmation dictionary or None
        """
        if self.use_mock_data:
            print(f"Mock order placement: {order_details}")
            return {
                'orderId': f"mock_{int(time.time())}",
                'status': 'filled',
                'filledQty': order_details.get('quantity', 0),
                'timestamp': datetime.now().isoformat()
            }
        
        endpoint = "/order/placeorder"
        result = self._make_request('POST', endpoint, json=order_details)
        return result
    
    def get_instrument_specs(self, symbol: str) -> Optional[Dict]:
        """
        Get instrument specifications (tick size, tick value, etc.).
        
        Args:
            symbol: Trading instrument symbol
        
        Returns:
            Instrument specs dictionary
        """
        # Use config data since it's static
        instruments = self.config.get('instruments', {})
        return instruments.get(symbol)
    
    def is_using_mock_data(self) -> bool:
        """
        Check if API is using mock data fallback.
        
        Returns:
            True if in mock mode
        """
        return self.use_mock_data


# Example usage
if __name__ == "__main__":
    api = TradovateAPI()
    
    # Attempt authentication
    api.authenticate()
    
    # Test account list
    accounts = api.get_account_list()
    print(f"\nAccounts: {accounts}")
    
    # Test historical data
    candles = api.get_historical_candles("MNQ", count=50)
    print(f"\nRetrieved {len(candles)} candles for MNQ")
    if candles:
        print(f"Sample candle: {candles[0]}")
    
    # Test instrument specs
    specs = api.get_instrument_specs("MNQ")
    print(f"\nMNQ Specs: {specs}")

