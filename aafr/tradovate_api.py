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
        # Construct auth URL from base_url (remove /v1 if present, then add /v1/auth/accesstokenrequest)
        base_domain = self.base_url.replace('/v1', '')
        self.auth_url = f"{base_domain}/v1/auth/accesstokenrequest"
        self.token = None  # Regular access token for trading operations
        self.md_token = None  # Market data access token
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
        Authenticate with Tradovate API and obtain access tokens.
        Uses Tradovate's official authentication format.
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Tradovate API authentication format
            app_id = self.api_config.get('app_id', 'AAFR Trading System')
            app_version = self.api_config.get('app_version', '1.0')
            device_id = self.api_config.get('device_id', 'aafr-device-001')
            password = self.api_config.get('password', '')
            
            auth_data = {
                'name': self.api_config['username'],
                'appId': app_id,
                'appVersion': app_version,
                'cid': int(self.api_config['client_id']),  # Convert to int
                'sec': self.api_config['client_secret'],
                'deviceId': device_id,
                'password': password
            }
            
            response = self.session.post(
                self.auth_url,
                json=auth_data,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                auth_response = response.json()
                
                # Check for rate limiting/security challenge response (p-ticket)
                if 'p-ticket' in auth_response:
                    p_time = auth_response.get('p-time', 0)
                    p_ticket = auth_response.get('p-ticket')
                    p_captcha = auth_response.get('p-captcha', False)
                    
                    print(f"[WARNING] Rate limiting/security challenge detected")
                    print(f"[WARNING] Wait time: {p_time} seconds")
                    if p_captcha:
                        print(f"[WARNING] Captcha may be required - check your Tradovate account")
                    
                    # Wait for the required time
                    if p_time > 0:
                        print(f"[INFO] Waiting {p_time} seconds before retry...")
                        time.sleep(p_time)
                    
                    # Retry authentication with p-ticket
                    print(f"[INFO] Retrying authentication with p-ticket...")
                    auth_data['p-ticket'] = p_ticket
                    
                    # Make retry request
                    retry_response = self.session.post(
                        self.auth_url,
                        json=auth_data,
                        headers={
                            'Content-Type': 'application/json',
                            'Accept': 'application/json'
                        },
                        timeout=10
                    )
                    
                    if retry_response.status_code == 200:
                        auth_response = retry_response.json()
                        # Check if we still have p-ticket (another challenge)
                        if 'p-ticket' in auth_response:
                            p_time = auth_response.get('p-time', 0)
                            print(f"[ERROR] Still rate limited. Wait {p_time} seconds and try again later.")
                            print(f"[ERROR] You may need to verify your account or wait longer.")
                            return False
                    else:
                        print(f"[ERROR] Retry authentication failed: HTTP {retry_response.status_code}")
                        return False
                
                # Check if response contains an error (even with HTTP 200)
                if 'errorText' in auth_response:
                    error_text = auth_response.get('errorText', 'Unknown error')
                    print(f"[ERROR] Authentication failed: {error_text}")
                    print(f"[ERROR] Request URL: {self.auth_url}")
                    print(f"[ERROR] Request body: {auth_data}")
                    print(f"[ERROR] Full response: {auth_response}")
                    return False
                
                # Check if we have an access token
                if 'accessToken' not in auth_response:
                    print(f"[ERROR] Authentication response missing accessToken")
                    print(f"[ERROR] Response keys: {list(auth_response.keys())}")
                    print(f"[ERROR] Full response: {auth_response}")
                    return False
                
                self.token = auth_response.get('accessToken')  # For trading operations
                self.md_token = auth_response.get('mdAccessToken')  # For market data operations
                
                # Parse expiration time
                expiration_time = auth_response.get('expirationTime')
                if expiration_time:
                    try:
                        # Parse ISO format: "2021-06-15T15:40:30.056Z"
                        # Handle both with and without timezone
                        if expiration_time.endswith('Z'):
                            expiration_time = expiration_time[:-1] + '+00:00'
                        elif '+' not in expiration_time and 'T' in expiration_time:
                            expiration_time = expiration_time + '+00:00'
                        exp_dt = datetime.fromisoformat(expiration_time)
                        self.token_expiry = exp_dt.timestamp()
                    except Exception as e:
                        # Fallback to 1 hour if parsing fails
                        print(f"[WARNING] Could not parse expiration time: {e}, using 1 hour default")
                        self.token_expiry = time.time() + 3600
                else:
                    self.token_expiry = time.time() + 3600  # Default 1 hour
                
                has_market_data = auth_response.get('hasMarketData', False)
                print(f"[OK] Authenticated with Tradovate {self.environment} API")
                if self.md_token:
                    print(f"[OK] Market data token obtained (hasMarketData: {has_market_data})")
                else:
                    print(f"[WARNING] No market data token received (hasMarketData: {has_market_data})")
                
                return True
            else:
                # Check if credentials are placeholder values
                if (str(self.api_config.get('client_id', '')).startswith('YOUR_') or 
                    self.api_config.get('username', '').startswith('YOUR_')):
                    print(f"[INFO] Using placeholder API credentials - switching to mock data mode")
                else:
                    print(f"[ERROR] Authentication failed: HTTP {response.status_code}")
                    print(f"[ERROR] Request URL: {self.auth_url}")
                    print(f"[ERROR] Request body: {auth_data}")
                    try:
                        error_response = response.json()
                        print(f"[ERROR] Full error response: {error_response}")
                        error_msg = error_response.get('error', error_response.get('message', error_response.get('errorMessage', 'Unknown error')))
                        print(f"[ERROR] Reason: {error_msg}")
                        # Check for time penalty response
                        if 'p-time' in error_response:
                            print(f"[WARNING] Time penalty: retry in {error_response.get('p-time')} seconds")
                    except Exception as e:
                        print(f"[ERROR] Could not parse error response: {e}")
                        print(f"[ERROR] Raw response text: {response.text[:500]}")
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
    
    def _make_request(self, method: str, endpoint: str, use_md_token: bool = False, **kwargs) -> Optional[Dict]:
        """
        Make authenticated API request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL, should not include /v1)
            use_md_token: If True, use market data token instead of regular token
            **kwargs: Additional arguments to pass to requests
        
        Returns:
            Response JSON or None if failed
        """
        if not self._ensure_authenticated():
            return None
        
        if self.use_mock_data:
            # Return mock response structure
            return None
        
        # Ensure endpoint starts with /v1 if not already present
        if not endpoint.startswith('/v1'):
            endpoint = f"/v1{endpoint}" if not endpoint.startswith('/') else f"/v1{endpoint}"
        
        url = f"{self.base_url.replace('/v1', '')}{endpoint}"
        
        # Use market data token for market data requests, regular token for trading operations
        token = self.md_token if use_md_token and self.md_token else self.token
        
        if not token:
            print(f"[ERROR] No access token available (use_md_token={use_md_token})")
            return None
        
        headers = kwargs.pop('headers', {})
        headers['Authorization'] = f"Bearer {token}"
        headers['Content-Type'] = 'application/json'
        headers['Accept'] = 'application/json'
        
        try:
            response = self.session.request(method, url, headers=headers, timeout=10, **kwargs)
            
            # Handle 401 Unauthorized - switch to mock data
            if response.status_code == 401:
                try:
                    error_detail = response.json()
                    print(f"[WARNING] API request unauthorized (401). Response: {error_detail}")
                except:
                    print(f"[WARNING] API request unauthorized (401). Response: {response.text[:200]}")
                print(f"[WARNING] Request URL: {url}")
                print(f"[WARNING] Using token type: {'mdAccessToken' if use_md_token else 'accessToken'}")
                self.use_mock_data = True
                return None
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 401:
                try:
                    error_detail = e.response.json()
                    print(f"[WARNING] API request unauthorized (401). Response: {error_detail}")
                except:
                    print(f"[WARNING] API request unauthorized (401). Response: {e.response.text[:200]}")
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
            interval: Candle interval (e.g., "5Min", "15Min", "1Hour", "1Day")
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
        
        # Parse interval to determine elementSize and underlyingType
        # Examples: "5Min" -> elementSize=5, "1Hour" -> elementSize=60, "1Day" -> elementSize=1
        interval_lower = interval.lower()
        if "day" in interval_lower or "d" in interval_lower:
            underlying_type = "DayBar"
            element_size = 1
        elif "hour" in interval_lower or "h" in interval_lower:
            underlying_type = "MinuteBar"
            # Extract number (e.g., "1Hour" -> 60, "2Hour" -> 120)
            hour_match = interval_lower.replace("hour", "").replace("h", "").strip()
            element_size = int(hour_match) * 60 if hour_match.isdigit() else 60
        elif "min" in interval_lower or "m" in interval_lower:
            underlying_type = "MinuteBar"
            # Extract number (e.g., "5Min" -> 5, "15Min" -> 15)
            min_match = interval_lower.replace("min", "").replace("m", "").strip()
            element_size = int(min_match) if min_match.isdigit() else 5
        else:
            # Default to 5-minute bars
            underlying_type = "MinuteBar"
            element_size = 5
        
        # Tradovate API requires POST with JSON body
        # Use market data token for historical data requests
        endpoint = "/chart/history"
        request_body = {
            "symbol": symbol,
            "chartDescription": {
                "underlyingType": underlying_type,
                "elementSize": element_size,
                "elementSizeUnit": "UnderlyingUnits"
            },
            "timeRange": {
                "asMuchAsElements": count
            }
        }
        
        # Try with market data token first, fall back to regular token if not available
        result = self._make_request('POST', endpoint, use_md_token=True, json=request_body)
        
        # If that failed and we have a regular token but no md_token, try with regular token
        if result is None and self.token and not self.md_token:
            print(f"[INFO] mdAccessToken not available, trying with regular accessToken for market data")
            result = self._make_request('POST', endpoint, use_md_token=False, json=request_body)
        
        if result is None:
            # If we're in mock mode, the message was already printed
            if not self.use_mock_data:
                print(f"Failed to fetch historical data, using mock data for {symbol}")
            return generate_mock_candles(count, symbol)
        
        # Transform API response to standard candle format
        # Tradovate API response structure may vary - adjust based on actual response
        candles = []
        
        # Try different possible response structures
        bars = result.get('bars', []) or result.get('data', []) or result.get('elements', [])
        
        for bar in bars:
            # Handle different possible field names in response
            candles.append({
                'timestamp': bar.get('time', bar.get('timestamp', bar.get('t', 0))),
                'open': float(bar.get('open', bar.get('o', 0))),
                'high': float(bar.get('high', bar.get('h', 0))),
                'low': float(bar.get('low', bar.get('l', 0))),
                'close': float(bar.get('close', bar.get('c', 0))),
                'volume': int(bar.get('volume', bar.get('v', 0))),
                'symbol': symbol
            })
        
        if candles:
            print(f"[OK] Retrieved {len(candles)} candles from Tradovate API for {symbol}")
        
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

