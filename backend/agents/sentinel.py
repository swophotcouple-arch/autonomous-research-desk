"""Sentinel Agent: Market Regime Detector."""

import json
import logging
from datetime import datetime
from typing import Dict, Tuple
from google.cloud import firestore
from google.cloud import bigquery
import numpy as np

logger = logging.getLogger(__name__)

db = firestore.Client()
bq_client = bigquery.Client()


class Sentinel:
    """Sentinel: Detects market regime using Nifty, VIX, and ADR."""

    # Regime thresholds
    REGIMES = {
        'Trending Bull': {
            'nifty_return_min': 0.0,
            'nifty_trend': 'positive',
            'vix_threshold': 1.0,
            'adr_threshold': 70
        },
        'Recovery / Relief Rally': {
            'nifty_return_min': 0.0,
            'nifty_trend': 'mixed',
            'vix_threshold': 1.5,
            'adr_threshold_min': 50,
            'adr_threshold_max': 70
        },
        'Choppy / Neutral': {
            'nifty_return_range': (-0.01, 0.01),
            'vix_threshold': 1.0,
            'adr_threshold_min': 40,
            'adr_threshold_max': 60
        },
        'Stressed / Volatile': {
            'nifty_return_max': 0.0,
            'vix_threshold': 1.5,
            'adr_threshold_max': 40
        },
        'Panic / Extreme Volatility': {
            'nifty_return_max': -0.03,
            'vix_threshold': 2.0,
            'adr_threshold_max': 30
        }
    }

    def __init__(self):
        """Initialize Sentinel agent."""
        self.db = db
        self.bq_client = bq_client

    def compute_regime(self) -> Dict:
        """Compute current market regime based on Nifty, VIX, and ADR.
        
        Returns:
            Dict with detected regime and supporting metrics
        """
        try:
            # Fetch market metrics
            nifty_metrics = self._get_nifty_metrics()
            vix_metrics = self._get_vix_metrics()
            adr_metrics = self._get_adr_metrics()
            
            if not all([nifty_metrics, vix_metrics, adr_metrics]):
                logger.error("Failed to fetch market metrics")
                return {'status': 'error', 'regime': None}
            
            # Determine regime
            regime = self._classify_regime(nifty_metrics, vix_metrics, adr_metrics)
            
            # Store in Firestore
            regime_doc = {
                'timestamp': datetime.utcnow(),
                'regime': regime,
                'nifty_metrics': nifty_metrics,
                'vix_metrics': vix_metrics,
                'adr_metrics': adr_metrics
            }
            
            self.db.collection('system_state').document('regime').set(regime_doc)
            
            logger.info(f"Regime detected: {regime}")
            return {
                'status': 'success',
                'regime': regime,
                'metrics': regime_doc
            }
            
        except Exception as e:
            logger.error(f"Error in compute_regime: {e}")
            return {'status': 'error', 'error': str(e), 'regime': None}

    def _get_nifty_metrics(self) -> Dict:
        """Fetch Nifty 20-day return and trend."""
        try:
            query = f"""
            SELECT 
                CURRENT_DATE() as date,
                close_price,
                LAG(close_price, 20) OVER (ORDER BY date) as close_20d_ago,
                (close_price - LAG(close_price, 20) OVER (ORDER BY date)) / 
                  LAG(close_price, 20) OVER (ORDER BY date) as return_20d
            FROM `{self.bq_client.project}.market_data.nifty_daily`
            WHERE date <= CURRENT_DATE()
            ORDER BY date DESC
            LIMIT 1
            """
            
            results = list(self.bq_client.query(query).result())
            if results:
                row = results[0]
                return {
                    'return_20d': float(row['return_20d'] or 0),
                    'close_price': float(row['close_price'])
                }
        except Exception as e:
            logger.error(f"Error fetching Nifty metrics: {e}")
        
        return {}

    def _get_vix_metrics(self) -> Dict:
        """Fetch India VIX and normalized level."""
        try:
            query = f"""
            SELECT 
                vix_value,
                AVG(vix_value) OVER (ORDER BY date ROWS BETWEEN 251 PRECEDING AND CURRENT ROW) as vix_mean_252d,
                STDDEV(vix_value) OVER (ORDER BY date ROWS BETWEEN 251 PRECEDING AND CURRENT ROW) as vix_std_252d
            FROM `{self.bq_client.project}.market_data.india_vix_daily`
            WHERE date = CURRENT_DATE()
            """
            
            results = list(self.bq_client.query(query).result())
            if results:
                row = results[0]
                vix = float(row['vix_value'])
                mean = float(row['vix_mean_252d'] or vix)
                normalized = vix / mean if mean > 0 else 1.0
                
                return {
                    'vix_value': vix,
                    'vix_mean_252d': mean,
                    'vix_normalized': normalized
                }
        except Exception as e:
            logger.error(f"Error fetching VIX metrics: {e}")
        
        return {}

    def _get_adr_metrics(self) -> Dict:
        """Fetch Advance-Decline Ratio for NSE."""
        try:
            query = f"""
            SELECT 
                advancing_stocks,
                declining_stocks,
                (advancing_stocks / NULLIF(declining_stocks, 0)) * 100 as adr
            FROM `{self.bq_client.project}.market_data.nse_adr_daily`
            WHERE date = CURRENT_DATE()
            ORDER BY date DESC
            LIMIT 1
            """
            
            results = list(self.bq_client.query(query).result())
            if results:
                row = results[0]
                return {
                    'advancing': int(row['advancing_stocks']),
                    'declining': int(row['declining_stocks']),
                    'adr': float(row['adr'] or 50)
                }
        except Exception as e:
            logger.error(f"Error fetching ADR metrics: {e}")
        
        return {}

    def _classify_regime(self, nifty: Dict, vix: Dict, adr: Dict) -> str:
        """Classify market regime based on metrics."""
        nifty_return = nifty.get('return_20d', 0)
        vix_normalized = vix.get('vix_normalized', 1.0)
        adr_value = adr.get('adr', 50)
        
        # Check Panic first (most restrictive)
        if nifty_return <= -0.03 and vix_normalized >= 2.0 and adr_value < 30:
            return 'Panic / Extreme Volatility'
        
        # Check Stressed
        if nifty_return < 0 and vix_normalized >= 1.5 and adr_value < 40:
            return 'Stressed / Volatile'
        
        # Check Choppy
        if -0.01 <= nifty_return <= 0.01 and 0.8 <= vix_normalized <= 1.2 and 40 <= adr_value <= 60:
            return 'Choppy / Neutral'
        
        # Check Recovery
        if nifty_return > 0 and vix_normalized < 1.5 and 50 <= adr_value <= 70:
            return 'Recovery / Relief Rally'
        
        # Check Trending Bull
        if nifty_return > 0 and vix_normalized < 1.0 and adr_value > 70:
            return 'Trending Bull'
        
        # Default to Choppy if no clear match
        return 'Choppy / Neutral'


def main(request):
    """Cloud Function entry point for regime detection."""
    sentinel = Sentinel()
    result = sentinel.compute_regime()
    return json.dumps(result), 200
