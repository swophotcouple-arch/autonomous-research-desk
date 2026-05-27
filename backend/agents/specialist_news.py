"""Specialist-News Agent: News Sentiment Analysis."""

import json
import logging
from datetime import datetime
from typing import Dict, List
from google.cloud import firestore

logger = logging.getLogger(__name__)

db = firestore.Client()


class SpecialistNews:
    """Specialist-News: Analyzes news sentiment for stocks."""

    def __init__(self):
        """Initialize Specialist-News agent."""
        self.db = db
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Load news specialist config from Firestore."""
        try:
            doc = self.db.collection('system_config').document('specialist_news').get()
            return doc.to_dict() or {}
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}

    def analyze_news_sentiment(self) -> Dict:
        """Analyze news sentiment for target universe.
        
        Returns:
            Dict with sentiment scores for each stock
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
                sentiment = self._get_sentiment_for_stock(ticker)
                if sentiment is not None:
                    results[ticker] = sentiment
            
            # Store results
            self.db.collection('specialist_analysis').document('news').set({
                'timestamp': datetime.utcnow(),
                'stocks_analyzed': len(results),
                'results': results
            })
            
            logger.info(f"News sentiment analysis completed for {len(results)} stocks")
            return {
                'status': 'success',
                'stocks_analyzed': len(results),
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Error in analyze_news_sentiment: {e}")
            return {'status': 'error', 'error': str(e)}

    def _get_sentiment_for_stock(self, ticker: str) -> Dict:
        """Get sentiment score for a single stock.
        
        In production, this would call a news API (NewsAPI, etc.)
        For now, returning synthetic data.
        """
        try:
            # Check if sentiment already cached in Firestore
            sentiment_doc = self.db.collection('news_sentiment').document(ticker).get()
            if sentiment_doc.exists:
                cached = sentiment_doc.to_dict()
                # Return if recent (< 1 hour)
                if (datetime.utcnow() - cached.get('timestamp', datetime.utcnow())).seconds < 3600:
                    return cached
            
            # In production: Call news API here
            # sentiment_score = call_news_api(ticker)
            # For MVP: Return neutral sentiment
            sentiment_score = 0.0
            
            result = {
                'ticker': ticker,
                'sentiment_score': sentiment_score,  # -1 to +1
                'timestamp': datetime.utcnow(),
                'source': 'synthetic',  # Will be 'news_api' in production
                'confidence': 0.5
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting sentiment for {ticker}: {e}")
            return None

    def aggregate_sector_sentiment(self) -> Dict:
        """Aggregate sentiment by sector."""
        try:
            # Fetch all news sentiment results
            results = {}
            for doc in self.db.collection('news_sentiment').stream():
                results[doc.id] = doc.to_dict()
            
            # Group by sector (requires ticker-to-sector mapping)
            sector_sentiments = {}
            for ticker, data in results.items():
                # Fetch sector from universe
                universe_doc = self.db.collection('target_universe').document('current').get()
                stocks = universe_doc.to_dict().get('stocks', [])
                sector = next((s['sector'] for s in stocks if s['ticker'] == ticker), 'Unknown')
                
                if sector not in sector_sentiments:
                    sector_sentiments[sector] = []
                sector_sentiments[sector].append(data['sentiment_score'])
            
            # Calculate averages
            sector_averages = {
                sector: sum(scores) / len(scores)
                for sector, scores in sector_sentiments.items()
            }
            
            return {
                'timestamp': datetime.utcnow(),
                'sector_sentiments': sector_averages
            }
            
        except Exception as e:
            logger.error(f"Error aggregating sector sentiment: {e}")
            return {}


def main(request):
    """Cloud Function entry point for news sentiment analysis."""
    specialist = SpecialistNews()
    result = specialist.analyze_news_sentiment()
    return json.dumps(result, default=str), 200
