"""
Test suite for Tradovate API integration module.
Tests authentication, data fetching, and mock fallback behavior.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from unittest.mock import patch, Mock
from aafr.tradovate_api import TradovateAPI
from aafr.utils import generate_mock_candles


class TestTradovateAPI(unittest.TestCase):
    """Test cases for Tradovate API module."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.api = TradovateAPI()
        self.symbol = 'MNQ'
    
    def test_api_initialization(self):
        """Test API client initialization."""
        self.assertIsNotNone(self.api)
        self.assertEqual(self.api.environment, 'demo')
        self.assertIsNotNone(self.api.base_url)
        self.assertIsNotNone(self.api.auth_url)
    
    def test_get_account_list_mock(self):
        """Test account list retrieval (with mock fallback)."""
        accounts = self.api.get_account_list()
        
        self.assertIsInstance(accounts, list)
        if len(accounts) > 0:
            account = accounts[0]
            self.assertIn('accountId', account)
            self.assertIn('accountName', account)
    
    def test_get_historical_candles_mock(self):
        """Test historical candle retrieval (with mock fallback)."""
        # Force mock mode
        self.api.use_mock_data = True
        
        candles = self.api.get_historical_candles(self.symbol, count=50)
        
        self.assertIsNotNone(candles)
        self.assertIsInstance(candles, list)
        self.assertEqual(len(candles), 50)
        
        if len(candles) > 0:
            candle = candles[0]
            self.assertIn('timestamp', candle)
            self.assertIn('open', candle)
            self.assertIn('high', candle)
            self.assertIn('low', candle)
            self.assertIn('close', candle)
            self.assertIn('volume', candle)
            self.assertIn('symbol', candle)
            self.assertEqual(candle['symbol'], self.symbol)
    
    def test_get_historical_candles_different_counts(self):
        """Test historical candle retrieval with different counts."""
        self.api.use_mock_data = True
        
        for count in [10, 50, 100, 200]:
            candles = self.api.get_historical_candles(self.symbol, count=count)
            self.assertEqual(len(candles), count)
    
    def test_get_instrument_specs(self):
        """Test instrument specifications retrieval."""
        specs = self.api.get_instrument_specs(self.symbol)
        
        self.assertIsNotNone(specs)
        self.assertIsInstance(specs, dict)
        self.assertIn('tick_size', specs)
        self.assertIn('tick_value', specs)
        self.assertIn('symbol', specs)
        self.assertEqual(specs['symbol'], self.symbol)
    
    def test_get_instrument_specs_unknown(self):
        """Test instrument specs for unknown symbol."""
        specs = self.api.get_instrument_specs('UNKNOWN_SYMBOL')
        
        self.assertIsNone(specs)
    
    def test_is_using_mock_data(self):
        """Test mock data mode detection."""
        initial_state = self.api.is_using_mock_data()
        self.assertIsInstance(initial_state, bool)
        
        self.api.use_mock_data = True
        self.assertTrue(self.api.is_using_mock_data())
        
        self.api.use_mock_data = False
        self.assertFalse(self.api.is_using_mock_data())
    
    def test_subscribe_live_data_mock(self):
        """Test live data subscription (mock mode)."""
        self.api.use_mock_data = True
        
        callback = Mock()
        result = self.api.subscribe_live_data(self.symbol, callback)
        
        self.assertTrue(result)
    
    def test_place_order_mock(self):
        """Test order placement (mock mode)."""
        self.api.use_mock_data = True
        
        order_details = {
            'accountId': 'test_account',
            'action': 'Buy',
            'symbol': self.symbol,
            'orderQty': 1,
            'orderType': 'Market',
            'route': 'Default'
        }
        
        result = self.api.place_order(order_details)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)
        self.assertIn('orderId', result)
        self.assertIn('status', result)
    
    def test_authenticate_fallback_to_mock(self):
        """Test authentication fallback to mock data."""
        # Mock authentication failure
        with patch.object(self.api.session, 'post', side_effect=Exception("Connection error")):
            result = self.api.authenticate()
            
            self.assertFalse(result)
            self.assertTrue(self.api.use_mock_data)
    
    def test_ensure_authenticated(self):
        """Test authentication check."""
        # Set to mock mode
        self.api.use_mock_data = True
        self.assertTrue(self.api._ensure_authenticated())
        
        # Without mock mode, should attempt authentication
        self.api.use_mock_data = False
        self.api.token = None
        # Will fail and fall back to mock
        with patch.object(self.api, 'authenticate', return_value=False):
            self.assertFalse(self.api._ensure_authenticated())
    
    def test_make_request_mock_mode(self):
        """Test API request in mock mode."""
        self.api.use_mock_data = True
        
        result = self.api._make_request('GET', '/test/endpoint')
        
        self.assertIsNone(result)  # Mock mode returns None
    
    def test_get_historical_candles_multiple_symbols(self):
        """Test historical data for multiple symbols."""
        self.api.use_mock_data = True
        
        symbols = ['MNQ', 'MES', 'MGC']
        
        for symbol in symbols:
            candles = self.api.get_historical_candles(symbol, count=20)
            self.assertEqual(len(candles), 20)
            
            if len(candles) > 0:
                self.assertEqual(candles[0]['symbol'], symbol)


if __name__ == '__main__':
    unittest.main()

