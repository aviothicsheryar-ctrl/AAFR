"""
Indication-Correction-Continuation (ICC) detection module.
Identifies high-probability trade setups based on smart money concepts.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime

from aafr.utils import detect_displacement, calculate_atr
from aafr.cvd_module import CVDCalculator


class ICCDetector:
    """
    Detect ICC trade structures in market data.
    Tracks indication, correction, and continuation phases.
    """
    
    def __init__(self, min_atr_for_displacement: float = 1.5):
        """
        Initialize ICC Detector.
        
        Args:
            min_atr_for_displacement: ATR multiplier for displacement detection
        """
        self.min_atr_for_displacement = min_atr_for_displacement
        self.cvd_calculator = CVDCalculator()
        self.current_phase = None
        self.indication_candle_idx = None
        self.correction_start_idx = None
        self.correction_end_idx = None
        self.continuation_candle_idx = None
    
    def detect_icc_structure(self, candles: List[Dict], 
                           require_all_phases: bool = True) -> Optional[Dict]:
        """
        Detect complete ICC structure in candle history.
        
        Args:
            candles: List of candle dictionaries
            require_all_phases: Require all three phases (Indication, Correction, Continuation)
        
        Returns:
            Dictionary with ICC structure details or None
        """
        if len(candles) < 20:
            return None
        
        # Calculate CVD for the entire series
        self.cvd_calculator.calculate_cvd(candles)
        
        # Detect Indication phase
        indication = self._detect_indication(candles)
        if not indication:
            return None
        
        # Detect Correction phase
        correction = self._detect_correction(candles, indication['idx'])
        if not correction:
            if require_all_phases:
                return None
            # Return partial structure if correction not yet found
            return {
                'indication': indication,
                'correction': None,
                'continuation': None,
                'complete': False
            }
        
        # Detect Continuation phase
        continuation = self._detect_continuation(candles, correction['end_idx'])
        if not continuation:
            if require_all_phases:
                return None
            return {
                'indication': indication,
                'correction': correction,
                'continuation': None,
                'complete': False
            }
        
        # Full ICC structure detected
        return {
            'indication': indication,
            'correction': correction,
            'continuation': continuation,
            'complete': True
        }
    
    def _detect_indication(self, candles: List[Dict]) -> Optional[Dict]:
        """
        Detect Indication phase (impulsive displacement).
        
        Args:
            candles: Candle history
        
        Returns:
            Indication details dictionary or None
        """
        if len(candles) < 15:
            return None
        
        # Calculate ATR for displacement detection
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        closes = [c['close'] for c in candles]
        atr = calculate_atr(highs, lows, closes)
        
        if atr is None:
            return None
        
        # Look for displacement in recent candles
        lookback = min(20, len(candles))
        for i in range(len(candles) - lookback, len(candles)):
            candle = candles[i]
            body_size = abs(candle['close'] - candle['open'])
            
            # Check for displacement
            if body_size >= atr * self.min_atr_for_displacement:
                # Check CVD alignment
                cvd_valid, cvd_msg = self.cvd_calculator.analyze_indication_phase(candles, i)
                
                if cvd_valid:
                    direction = 'LONG' if candle['close'] > candle['open'] else 'SHORT'
                    self.indication_candle_idx = i
                    
                    return {
                        'idx': i,
                        'candle': candle,
                        'direction': direction,
                        'atr': atr,
                        'cvd_valid': True,
                        'message': cvd_msg
                    }
        
        return None
    
    def _detect_correction(self, candles: List[Dict], 
                          indication_idx: int) -> Optional[Dict]:
        """
        Detect Correction phase (retracement into value zone).
        
        Args:
            candles: Candle history
            indication_idx: Index of indication candle
        
        Returns:
            Correction details dictionary or None
        """
        if indication_idx >= len(candles) - 3:
            return None
        
        indication_candle = candles[indication_idx]
        direction = 'LONG' if indication_candle['close'] > indication_candle['open'] else 'SHORT'
        
        # Find correction start and end
        correction_start = None
        correction_end = None
        
        # Look ahead from indication
        for i in range(indication_idx + 1, min(indication_idx + 20, len(candles))):
            candle = candles[i]
            
            if direction == 'LONG':
                # Looking for retracement down
                if correction_start is None and candle['close'] < candle['open']:
                    correction_start = i
                elif correction_start is not None and candle['close'] > candle['open']:
                    correction_end = i
                    break
            else:  # SHORT
                # Looking for retracement up
                if correction_start is None and candle['close'] > candle['open']:
                    correction_start = i
                elif correction_start is not None and candle['close'] < candle['open']:
                    correction_end = i
                    break
        
        if correction_start is None or correction_end is None:
            return None
        
        # Check CVD neutralizing
        cvd_valid, cvd_msg = self.cvd_calculator.analyze_correction_phase(
            candles, correction_start, correction_end
        )
        
        if cvd_valid:
            self.correction_start_idx = correction_start
            self.correction_end_idx = correction_end
            
            return {
                'start_idx': correction_start,
                'end_idx': correction_end,
                'cvd_valid': True,
                'message': cvd_msg
            }
        
        return None
    
    def _detect_continuation(self, candles: List[Dict], 
                           correction_end_idx: int) -> Optional[Dict]:
        """
        Detect Continuation phase (resume in indication direction).
        
        Args:
            candles: Candle history
            correction_end_idx: Index of correction end
        
        Returns:
            Continuation details dictionary or None
        """
        if correction_end_idx >= len(candles):
            return None
        
        # The continuation candle is the first after correction
        continuation_idx = correction_end_idx
        
        candle = candles[continuation_idx]
        indication_candle = candles[self.indication_candle_idx]
        
        direction = 'LONG' if indication_candle['close'] > indication_candle['open'] else 'SHORT'
        
        # Check if continuation aligns with indication direction
        candle_direction = 'LONG' if candle['close'] > candle['open'] else 'SHORT'
        
        if candle_direction != direction:
            return None
        
        # Check CVD alignment
        cvd_valid, cvd_msg = self.cvd_calculator.analyze_continuation_phase(
            candles, continuation_idx
        )
        
        if cvd_valid:
            self.continuation_candle_idx = continuation_idx
            
            return {
                'idx': continuation_idx,
                'candle': candle,
                'cvd_valid': True,
                'message': cvd_msg
            }
        
        return None
    
    def calculate_r_multiple(self, entry: float, stop: float, 
                           candles: List[Dict], 
                           preferred_r: float = 3.0) -> float:
        """
        Calculate R multiple based on structure analysis.
        
        Args:
            entry: Entry price
            stop: Stop loss price
            candles: Candle history
            preferred_r: Preferred R multiple (default 3.0)
        
        Returns:
            Calculated R multiple
        """
        risk_distance = abs(entry - stop)
        
        if risk_distance == 0:
            return 0.0
        
        # Use recent price structure to project target
        # Simple approach: use ATR for projection
        highs = [c['high'] for c in candles[-20:]]
        lows = [c['low'] for c in candles[-20:]]
        closes = [c['close'] for c in candles[-20:]]
        atr = calculate_atr(highs, lows, closes)
        
        if atr is None:
            return preferred_r  # Default fallback
        
        # Project using ATR multiplier
        reward_distance = atr * preferred_r
        r_multiple = reward_distance / risk_distance
        
        return max(r_multiple, preferred_r)  # Minimum preferred R
    
    def calculate_trade_levels(self, icc_structure: Dict, 
                              candles: List[Dict], symbol: str) -> Tuple[float, float, float, float]:
        """
        Calculate entry, stop, take profit, and R multiple for trade setup.
        
        Args:
            icc_structure: ICC structure dictionary
            candles: Candle history
            symbol: Trading symbol
        
        Returns:
            Tuple of (entry, stop, tp, r_multiple)
        """
        # Entry: continuation candle close
        continuation_candle = icc_structure['continuation']['candle']
        entry = continuation_candle['close']
        direction = icc_structure['indication']['direction']
        
        # Stop: beyond invalidation (correction low for LONG, high for SHORT)
        correction_candles = candles[
            icc_structure['correction']['start_idx']:
            icc_structure['correction']['end_idx']+1
        ]
        
        if direction == 'LONG':
            stop = min(c['low'] for c in correction_candles) - (entry * 0.001)  # Small buffer
        else:
            stop = max(c['high'] for c in correction_candles) + (entry * 0.001)
        
        # R multiple
        r_multiple = self.calculate_r_multiple(entry, stop, candles, 3.0)
        
        # Take profit based on R multiple
        risk_distance = abs(entry - stop)
        reward_distance = risk_distance * r_multiple
        
        if direction == 'LONG':
            tp = entry + reward_distance
        else:
            tp = entry - reward_distance
        
        return (entry, stop, tp, r_multiple)
    
    def validate_full_setup(self, icc_structure: Dict, candles: List[Dict]) -> Tuple[bool, List[str]]:
        """
        Validate complete ICC setup against all five conditions.
        
        Conditions:
        1. Correction retraces into value zone
        2. Continuation candle confirms displacement
        3. CVD aligns with direction (no divergence)
        4. R multiple >= 2.0
        5. Risk <= 1% of account
        
        Args:
            icc_structure: ICC structure dictionary
            candles: Candle history
        
        Returns:
            Tuple of (is_valid, list_of_violations)
        """
        violations = []
        
        if not icc_structure or not icc_structure.get('complete'):
            violations.append("Incomplete ICC structure")
            return (False, violations)
        
        # Condition 1: Correction in value zone
        if not icc_structure.get('correction'):
            violations.append("No correction detected")
        # TODO: Add more sophisticated value zone detection (FVG, breaker, OB)
        
        # Condition 2: Continuation confirms displacement
        if not icc_structure.get('continuation'):
            violations.append("No continuation confirmation")
        elif not icc_structure['continuation'].get('cvd_valid'):
            violations.append("Continuation CVD not valid")
        
        # Condition 3: CVD alignment (no divergence)
        has_divergence, div_msg = self.cvd_calculator.check_divergence(candles)
        if has_divergence:
            violations.append(f"CVD divergence: {div_msg}")
        
        # Conditions 4 & 5 are handled by RiskEngine
        # This validation focuses on ICC-specific logic
        
        return (len(violations) == 0, violations)
    
    def reset(self) -> None:
        """Reset ICC detector state."""
        self.current_phase = None
        self.indication_candle_idx = None
        self.correction_start_idx = None
        self.correction_end_idx = None
        self.continuation_candle_idx = None
        self.cvd_calculator.reset()


# Example usage
if __name__ == "__main__":
    from aafr.utils import generate_mock_candles
    
    # Generate mock data
    candles = generate_mock_candles(100, "MNQ")
    
    # Initialize ICC detector
    icc = ICCDetector()
    
    # Detect ICC structure
    icc_structure = icc.detect_icc_structure(candles)
    
    if icc_structure:
        print("ICC Structure Detected!")
        print(f"Indication: {icc_structure['indication']['direction']} at index {icc_structure['indication']['idx']}")
        if icc_structure.get('correction'):
            print(f"Correction: {icc_structure['correction']['start_idx']} to {icc_structure['correction']['end_idx']}")
        if icc_structure.get('continuation'):
            print(f"Continuation: {icc_structure['continuation']['idx']}")
        
        # Validate setup
        is_valid, violations = icc.validate_full_setup(icc_structure, candles)
        print(f"\nSetup valid: {is_valid}")
        if violations:
            print(f"Violations: {violations}")
    else:
        print("No ICC structure detected")

