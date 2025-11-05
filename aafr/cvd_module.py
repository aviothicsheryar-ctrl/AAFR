"""
Cumulative Volume Delta (CVD) module for order flow analysis.
Detects buying and selling pressure through volume imbalance.
"""

from typing import Dict, List, Optional, Tuple
from aafr.utils import generate_mock_volume_data


class CVDCalculator:
    """
    Calculate and analyze Cumulative Volume Delta for trade confirmation.
    CVD tracks cumulative buy volume vs sell volume over time.
    """
    
    def __init__(self):
        """Initialize CVD Calculator."""
        self.cvd_values = []  # Cumulative volume delta history
        self.current_cvd = 0.0
    
    def calculate_cvd(self, candles: List[Dict], 
                     volume_deltas: Optional[List[int]] = None) -> List[int]:
        """
        Calculate Cumulative Volume Delta from candle data.
        
        Args:
            candles: List of candle dictionaries with volume data
            volume_deltas: Optional pre-calculated volume deltas
        
        Returns:
            List of cumulative CVD values
        """
        if volume_deltas is None:
            volume_deltas = self._calculate_volume_deltas(candles)
        
        cvd_values = []
        cumulative = 0
        
        for delta in volume_deltas:
            cumulative += delta
            cvd_values.append(cumulative)
        
        self.cvd_values = cvd_values
        if cvd_values:
            self.current_cvd = cvd_values[-1]
        
        return cvd_values
    
    def _calculate_volume_deltas(self, candles: List[Dict]) -> List[int]:
        """
        Calculate buy/sell volume delta for each candle.
        
        Args:
            candles: List of candle dictionaries
        
        Returns:
            List of volume deltas (buy - sell)
        """
        deltas = []
        
        for candle in candles:
            # Simple heuristic: bullish candle = more buy volume
            # In production, use actual bid/ask volume or Level II data
            close = candle.get('close', 0)
            open_price = candle.get('open', 0)
            volume = candle.get('volume', 0)
            
            if close > open_price:
                # Bullish candle: assume 52% buy volume
                buy_vol = int(volume * 0.52)
                sell_vol = volume - buy_vol
            elif close < open_price:
                # Bearish candle: assume 48% buy volume
                buy_vol = int(volume * 0.48)
                sell_vol = volume - buy_vol
            else:
                # Doji: 50/50 split
                buy_vol = int(volume * 0.50)
                sell_vol = volume - buy_vol
            
            delta = buy_vol - sell_vol
            deltas.append(delta)
        
        return deltas
    
    def check_divergence(self, candles: List[Dict], lookback: int = 5) -> Tuple[bool, str]:
        """
        Check for CVD divergence (price vs volume misalignment).
        
        Args:
            candles: Recent candle data
            lookback: Number of candles to analyze
        
        Returns:
            Tuple of (has_divergence, description)
        """
        if len(candles) < lookback or len(self.cvd_values) < lookback:
            return (False, "Insufficient data")
        
        # Get recent slices
        recent_candles = candles[-lookback:]
        recent_cvd = self.cvd_values[-lookback:]
        
        # Identify trend direction
        first_close = recent_candles[0]['close']
        last_close = recent_candles[-1]['close']
        price_trend = 'UP' if last_close > first_close else 'DOWN'
        
        # Identify CVD trend
        first_cvd = recent_cvd[0]
        last_cvd = recent_cvd[-1]
        cvd_trend = 'UP' if last_cvd > first_cvd else 'DOWN'
        
        # Divergence detection
        if price_trend == 'UP' and cvd_trend == 'DOWN':
            return (True, f"Bearish divergence: Price up, CVD down")
        elif price_trend == 'DOWN' and cvd_trend == 'UP':
            return (True, f"Bullish divergence: Price down, CVD up")
        else:
            return (False, f"No divergence: Price {price_trend}, CVD {cvd_trend}")
    
    def analyze_indication_phase(self, candles: List[Dict], 
                                indication_candle_idx: int) -> Tuple[bool, str]:
        """
        Analyze CVD behavior during Indication phase.
        Indication: CVD should increase in same direction as displacement.
        
        Args:
            candles: Full candle history
            indication_candle_idx: Index of indication candle
        
        Returns:
            Tuple of (is_valid, description)
        """
        if indication_candle_idx < 0 or indication_candle_idx >= len(candles):
            return (False, "Invalid indication candle index")
        
        indication_candle = candles[indication_candle_idx]
        close = indication_candle['close']
        open_price = indication_candle['open']
        
        # Determine price direction
        price_direction = 'UP' if close > open_price else 'DOWN'
        
        # Get CVD delta for indication candle
        cvd_before = self.cvd_values[indication_candle_idx - 1] if indication_candle_idx > 0 else 0
        cvd_after = self.cvd_values[indication_candle_idx]
        cvd_delta = cvd_after - cvd_before
        
        # CVD should align with price direction
        cvd_direction = 'UP' if cvd_delta > 0 else 'DOWN'
        
        if price_direction == cvd_direction:
            return (True, f"Valid indication: Price {price_direction}, CVD {cvd_direction}")
        else:
            return (False, f"Invalid indication: Price {price_direction}, CVD {cvd_direction}")
    
    def analyze_correction_phase(self, candles: List[Dict], 
                                correction_start: int, correction_end: int) -> Tuple[bool, str]:
        """
        Analyze CVD behavior during Correction phase.
        Correction: CVD should neutralize (reduce momentum).
        
        Args:
            candles: Full candle history
            correction_start: Start index of correction
            correction_end: End index of correction
        
        Returns:
            Tuple of (is_valid, description)
        """
        if correction_start >= correction_end or correction_end >= len(self.cvd_values):
            return (False, "Invalid correction range")
        
        cvd_start = self.cvd_values[correction_start]
        cvd_end = self.cvd_values[correction_end]
        cvd_change = cvd_end - cvd_start
        
        # CVD should show reduced momentum (neutralize)
        abs_change = abs(cvd_change)
        
        # Compare to prior move
        if correction_start > 0:
            prev_cvd_change = abs(self.cvd_values[correction_start] - 
                                 self.cvd_values[max(0, correction_start - 5)])
            
            if abs_change < prev_cvd_change * 0.6:
                return (True, "Valid correction: CVD neutralizing")
            else:
                return (False, "Invalid correction: CVD still strong")
        
        return (True, "Correction CVD valid")
    
    def analyze_continuation_phase(self, candles: List[Dict], 
                                  continuation_candle_idx: int) -> Tuple[bool, str]:
        """
        Analyze CVD behavior during Continuation phase.
        Continuation: CVD resumes in same direction as indication.
        
        Args:
            candles: Full candle history
            continuation_candle_idx: Index of continuation candle
        
        Returns:
            Tuple of (is_valid, description)
        """
        if continuation_candle_idx >= len(candles) or continuation_candle_idx >= len(self.cvd_values):
            return (False, "Invalid continuation candle index")
        
        continuation_candle = candles[continuation_candle_idx]
        close = continuation_candle['close']
        open_price = continuation_candle['open']
        
        # Determine price direction
        price_direction = 'UP' if close > open_price else 'DOWN'
        
        # Get CVD delta for continuation candle
        cvd_before = self.cvd_values[continuation_candle_idx - 1] if continuation_candle_idx > 0 else 0
        cvd_after = self.cvd_values[continuation_candle_idx]
        cvd_delta = cvd_after - cvd_before
        
        cvd_direction = 'UP' if cvd_delta > 0 else 'DOWN'
        
        if price_direction == cvd_direction:
            return (True, f"Valid continuation: Price {price_direction}, CVD {cvd_direction}")
        else:
            return (False, f"Invalid continuation: Price {price_direction}, CVD {cvd_direction}")
    
    def get_cvd_slope(self, lookback: int = 5) -> float:
        """
        Calculate CVD slope (trend strength).
        
        Args:
            lookback: Number of candles to analyze
        
        Returns:
            CVD slope value
        """
        if len(self.cvd_values) < lookback:
            return 0.0
        
        recent_cvd = self.cvd_values[-lookback:]
        
        # Simple linear regression slope
        n = len(recent_cvd)
        x_sum = sum(range(n))
        y_sum = sum(recent_cvd)
        xy_sum = sum(i * recent_cvd[i] for i in range(n))
        x2_sum = sum(i * i for i in range(n))
        
        denominator = n * x2_sum - x_sum * x_sum
        if denominator == 0:
            return 0.0
        
        slope = (n * xy_sum - x_sum * y_sum) / denominator
        return slope
    
    def reset(self) -> None:
        """Reset CVD history."""
        self.cvd_values = []
        self.current_cvd = 0.0


# Example usage
if __name__ == "__main__":
    from aafr.utils import generate_mock_candles
    
    # Generate mock data
    candles = generate_mock_candles(50, "MNQ")
    cvd = CVDCalculator()
    
    # Calculate CVD
    cvd_values = cvd.calculate_cvd(candles)
    print(f"Calculated {len(cvd_values)} CVD values")
    print(f"Latest CVD: {cvd_values[-1]}")
    
    # Check divergence
    has_div, div_msg = cvd.check_divergence(candles)
    print(f"\nDivergence check: {has_div}")
    print(f"Message: {div_msg}")
    
    # Analyze phases (mock indices)
    ind_valid, ind_msg = cvd.analyze_indication_phase(candles, 25)
    print(f"\nIndication phase: {ind_valid}")
    print(f"Message: {ind_msg}")
    
    cont_valid, cont_msg = cvd.analyze_continuation_phase(candles, 30)
    print(f"\nContinuation phase: {cont_valid}")
    print(f"Message: {cont_msg}")
    
    # Get CVD slope
    slope = cvd.get_cvd_slope()
    print(f"\nCVD slope: {slope:.2f}")

