"""Specialist-Pattern Agent: Technical Analysis."""

import json
import logging
from datetime import datetime
from typing import Dict, List
from google.cloud import firestore
from google.cloud import bigquery
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

db = firestore.Client()
bq_client = bigquery.Client()


class SpecialistPattern:
    """Specialist-Pattern: Performs technical analysis on target universe."""

    def __init__(self):
        """Initialize Specialist-Pattern agent."""
        self.db = db
        self.bq_client = bq_client
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Load pattern specialist config from Firestore."""
        try:
            doc = self.db.collection('system_config').document('specialist_pattern').get()
            return doc.to_dict() or {}
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}

    def analyze_universe(self) -> Dict:
        """Analyze target universe for technical patterns.
        
        Returns:
            Dict with analysis results for each stock
        """
        try:
            # Fetch target universe
            universe_doc = self.db.collection('target_universe').document('current').get()
            if not universe_doc.exists:
                logger.warning("No target universe found")
                return {'status': 'no_universe', 'stocks_analyzed': 0}
            
            universe = universe_doc.to_dict()
            stocks = universe.get('stocks', [])
            
            results = {}
            for stock in stocks:
                ticker = stock['ticker']
                analysis = self._analyze_stock(ticker)
                if analysis:
                    results[ticker] = analysis
            
            # Store results in Firestore
            self.db.collection('specialist_analysis').document('pattern').set({
                'timestamp': datetime.utcnow(),
                'stocks_analyzed': len(results),
                'results': results
            })
            
            logger.info(f"Pattern analysis completed for {len(results)} stocks")
            return {
                'status': 'success',
                'stocks_analyzed': len(results),
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Error in analyze_universe: {e}")
            return {'status': 'error', 'error': str(e)}

    def _analyze_stock(self, ticker: str) -> Dict:
        """Perform technical analysis on a single stock."""
        try:
            # Fetch historical data (60 days)
            query = f"""
            SELECT 
                date,
                close_price,
                high_price,
                low_price,
                volume_lakhs
            FROM `{self.bq_client.project}.market_data.nse_daily`
            WHERE ticker = '{ticker}'
                AND date >= DATE_SUB(CURRENT_DATE(), INTERVAL 60 DAY)
            ORDER BY date DESC
            LIMIT 60
            """
            
            results = list(self.bq_client.query(query).result())
            if not results:
                return None
            
            df = pd.DataFrame([dict(row) for row in results])
            df = df.sort_values('date').reset_index(drop=True)
            
            # Calculate indicators
            indicators = self._calculate_indicators(df)
            
            # Generate conviction score (0-10)
            conviction = self._calculate_conviction(indicators)
            
            return {
                'ticker': ticker,
                'timestamp': datetime.utcnow().isoformat(),
                'indicators': indicators,
                'conviction_score': conviction,
                'technical_setup': self._describe_setup(indicators)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing {ticker}: {e}")
            return None

    def _calculate_indicators(self, df: pd.DataFrame) -> Dict:
        """Calculate technical indicators."""
        indicators = {}
        
        # Moving averages
        indicators['ma_20'] = df['close_price'].rolling(20).mean().iloc[-1]
        indicators['ma_50'] = df['close_price'].rolling(50).mean().iloc[-1]
        indicators['ma_200'] = df['close_price'].rolling(200).mean().iloc[-1] if len(df) >= 200 else None
        
        current_price = df['close_price'].iloc[-1]
        indicators['price'] = current_price
        
        # Price relative to MAs
        indicators['price_vs_ma20'] = (current_price - indicators['ma_20']) / indicators['ma_20'] if indicators['ma_20'] else 0
        indicators['price_vs_ma50'] = (current_price - indicators['ma_50']) / indicators['ma_50'] if indicators['ma_50'] else 0
        
        # RSI (14)
        indicators['rsi_14'] = self._calculate_rsi(df['close_price'], 14)
        
        # Volume analysis
        avg_volume = df['volume_lakhs'].rolling(20).mean().iloc[-1]
        current_volume = df['volume_lakhs'].iloc[-1]
        indicators['volume_ratio'] = current_volume / avg_volume if avg_volume > 0 else 1
        
        # ATR (Average True Range)
        indicators['atr'] = self._calculate_atr(df, 14)
        
        return indicators

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI (Relative Strength Index)."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss if loss.iloc[-1] != 0 else 0
        rsi = 100 - (100 / (1 + rs)) if rs != 0 else 50
        
        return float(rsi.iloc[-1])

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range."""
        high = df['high_price']
        low = df['low_price']
        close = df['close_price']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        
        return float(atr.iloc[-1])

    def _calculate_conviction(self, indicators: Dict) -> float:
        """Calculate conviction score (1-10) based on technical setup."""
        score = 5.0  # Base score
        
        # Price position relative to MAs
        if indicators.get('price_vs_ma20', 0) < -0.02:  # Below MA20
            score += 1.5
        elif indicators.get('price_vs_ma20', 0) > 0.02:  # Above MA20
            score += 0.5
        
        # RSI signals
        rsi = indicators.get('rsi_14', 50)
        if rsi < 30:  # Oversold
            score += 2
        elif rsi > 70:  # Overbought
            score -= 1
        
        # Volume confirmation
        vol_ratio = indicators.get('volume_ratio', 1)
        if vol_ratio > 1.5:
            score += 1
        
        return min(max(score, 1), 10)  # Clamp to 1-10

    def _describe_setup(self, indicators: Dict) -> str:
        """Generate human-readable technical setup description."""
        descriptions = []
        
        price_vs_ma = indicators.get('price_vs_ma20', 0)
        if price_vs_ma < -0.05:
            descriptions.append("Price significantly below 20-day MA")
        elif price_vs_ma > 0.05:
            descriptions.append("Price significantly above 20-day MA")
        
        rsi = indicators.get('rsi_14', 50)
        if rsi < 30:
            descriptions.append("RSI < 30 (oversold)")
        elif rsi > 70:
            descriptions.append("RSI > 70 (overbought)")
        
        vol = indicators.get('volume_ratio', 1)
        if vol > 1.5:
            descriptions.append(f"Volume spike {vol:.1f}x average")
        
        return ", ".join(descriptions) if descriptions else "Neutral technical setup"


def main(request):
    """Cloud Function entry point for pattern analysis."""
    specialist = SpecialistPattern()
    result = specialist.analyze_universe()
    return json.dumps(result, default=str), 200
