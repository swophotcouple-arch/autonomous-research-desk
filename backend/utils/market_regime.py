"""Utility module for market regime detection."""

from typing import Dict
import pandas as pd


class RegimeDetector:
    """Detects market regime from metrics."""

    REGIME_RULES = {
        'Trending Bull': {
            'nifty_return_min': 0.0,
            'vix_max': 1.0,
            'adr_min': 70
        },
        'Recovery / Relief Rally': {
            'nifty_return_min': 0.0,
            'vix_max': 1.5,
            'adr_min': 50,
            'adr_max': 70
        },
        'Choppy / Neutral': {
            'nifty_return_min': -0.01,
            'nifty_return_max': 0.01,
            'vix_min': 0.8,
            'vix_max': 1.2,
            'adr_min': 40,
            'adr_max': 60
        },
        'Stressed / Volatile': {
            'nifty_return_max': 0.0,
            'vix_min': 1.5,
            'adr_max': 40
        },
        'Panic / Extreme Volatility': {
            'nifty_return_max': -0.03,
            'vix_min': 2.0,
            'adr_max': 30
        }
    }

    @staticmethod
    def classify(nifty_return: float, vix_normalized: float, adr: float) -> str:
        """Classify regime based on metrics.
        
        Args:
            nifty_return: 20-day Nifty return
            vix_normalized: VIX / VIX_252d_mean
            adr: Advance-Decline Ratio
            
        Returns:
            Regime name (string)
        """
        # Check from most restrictive to least
        if (nifty_return <= -0.03 and 
            vix_normalized >= 2.0 and 
            adr < 30):
            return 'Panic / Extreme Volatility'
        
        if (nifty_return < 0 and 
            vix_normalized >= 1.5 and 
            adr < 40):
            return 'Stressed / Volatile'
        
        if (-0.01 <= nifty_return <= 0.01 and 
            0.8 <= vix_normalized <= 1.2 and 
            40 <= adr <= 60):
            return 'Choppy / Neutral'
        
        if (nifty_return > 0 and 
            vix_normalized < 1.5 and 
            50 <= adr <= 70):
            return 'Recovery / Relief Rally'
        
        if (nifty_return > 0 and 
            vix_normalized < 1.0 and 
            adr > 70):
            return 'Trending Bull'
        
        return 'Choppy / Neutral'  # Default
