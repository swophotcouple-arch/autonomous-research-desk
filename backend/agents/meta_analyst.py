"""Meta-Analyst Agent: Pre-market screener and post-market retrospective."""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from google.cloud import firestore
from google.cloud import bigquery
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

db = firestore.Client()
bq_client = bigquery.Client()


class MetaAnalyst:
    """Meta-Analyst: Screens universe pre-market and analyzes P&L post-market."""

    def __init__(self):
        """Initialize Meta-Analyst agent."""
        self.db = db
        self.bq_client = bq_client
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Load configuration from Firestore."""
        try:
            doc = self.db.collection('system_config').document('meta_analyst').get()
            return doc.to_dict() or {}
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}

    def pre_market_screener(self, universe_size: int = 300) -> Dict:
        """Screen NSE/BSE universe by liquidity and volatility.
        
        Args:
            universe_size: Target number of stocks to screen (default 300)
            
        Returns:
            Dict with target_universe and metadata
        """
        try:
            # Query BigQuery for liquid, volatile stocks
            query = f"""
            SELECT 
                ticker,
                avg_volume_lakhs,
                volatility_20d,
                market_cap_cr,
                sector,
                last_price
            FROM `{self.bq_client.project}.market_data.nse_daily_stats`
            WHERE date = CURRENT_DATE()
                AND avg_volume_lakhs >= 5.0
                AND volatility_20d >= 1.5
            ORDER BY avg_volume_lakhs * volatility_20d DESC
            LIMIT {universe_size}
            """
            
            results = self.bq_client.query(query).result()
            stocks = [dict(row) for row in results]
            
            # Store in Firestore
            universe_doc = {
                'timestamp': datetime.utcnow(),
                'stocks': stocks,
                'count': len(stocks),
                'universe_size': universe_size
            }
            
            self.db.collection('target_universe').document('current').set(universe_doc)
            
            logger.info(f"Screened {len(stocks)} stocks for target universe")
            return {'status': 'success', 'universe': stocks, 'count': len(stocks)}
            
        except Exception as e:
            logger.error(f"Error in pre_market_screener: {e}")
            return {'status': 'error', 'error': str(e)}

    def post_market_retrospective(self, window_days: int = 30) -> Dict:
        """Analyze mock trades and update strategy registry with self-correction.
        
        Args:
            window_days: Look-back window for P&L aggregation (default 30 days)
            
        Returns:
            Dict with analysis results and strategy updates
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=window_days)
            
            # Fetch all mock trades in window
            trades = []
            for doc in self.db.collection('mock_trades').where(
                'timestamp', '>=', cutoff_date
            ).stream():
                trades.append(doc.to_dict())
            
            if not trades:
                logger.warning(f"No trades found in last {window_days} days")
                return {'status': 'no_trades', 'trades_analyzed': 0}
            
            # Group by strategy and regime
            analysis = self._aggregate_performance(trades)
            
            # Update strategy registry with self-correction
            updates = self._apply_self_correction(analysis)
            
            logger.info(f"Post-market retrospective completed. Trades analyzed: {len(trades)}")
            return {
                'status': 'success',
                'trades_analyzed': len(trades),
                'analysis': analysis,
                'updates': updates
            }
            
        except Exception as e:
            logger.error(f"Error in post_market_retrospective: {e}")
            return {'status': 'error', 'error': str(e)}

    def _aggregate_performance(self, trades: List[Dict]) -> Dict:
        """Aggregate P&L metrics by strategy and regime."""
        analysis = {}
        
        for trade in trades:
            strategy_id = trade.get('thesis', {}).get('strategy_id', 'unknown')
            regime = trade.get('thesis', {}).get('market_regime', 'unknown')
            pnl = trade.get('pnl_pct', 0)
            key = f"{strategy_id}_{regime}"
            
            if key not in analysis:
                analysis[key] = {
                    'strategy_id': strategy_id,
                    'regime': regime,
                    'trades': [],
                    'total_pnl': 0,
                    'win_count': 0,
                    'loss_count': 0
                }
            
            analysis[key]['trades'].append(trade)
            analysis[key]['total_pnl'] += pnl
            
            if pnl > 0:
                analysis[key]['win_count'] += 1
            else:
                analysis[key]['loss_count'] += 1
        
        # Compute metrics
        for key, data in analysis.items():
            total_trades = len(data['trades'])
            data['win_rate'] = data['win_count'] / total_trades if total_trades > 0 else 0
            data['avg_pnl'] = data['total_pnl'] / total_trades if total_trades > 0 else 0
        
        return analysis

    def _apply_self_correction(self, analysis: Dict) -> Dict:
        """Apply self-correction rules to strategy registry."""
        updates = {}
        
        for key, metrics in analysis.items():
            strategy_id = metrics['strategy_id']
            
            try:
                # Fetch strategy from registry
                strat_doc = self.db.collection('strategy_registry').document(strategy_id).get()
                if not strat_doc.exists:
                    continue
                
                strategy = strat_doc.to_dict()
                
                # Check if self-correction is enabled
                if not strategy.get('enable_self_correction', False):
                    continue
                
                rules = strategy.get('self_correction_rules', {})
                min_sample = rules.get('min_sample_size', 10)
                score_delta = rules.get('score_delta_on_failure', -0.5)
                
                # Check if sample size threshold met
                if len(metrics['trades']) < min_sample:
                    continue
                
                # If win rate is low, adjust conviction threshold
                win_rate_threshold = 0.4  # 40% is minimum acceptable
                if metrics['win_rate'] < win_rate_threshold:
                    old_threshold = strategy.get('conviction_threshold', 7)
                    new_threshold = max(old_threshold + score_delta, 5)  # Floor at 5
                    
                    strategy['conviction_threshold'] = new_threshold
                    strategy['timestamp_updated'] = datetime.utcnow()
                    
                    # Write back to Firestore
                    self.db.collection('strategy_registry').document(strategy_id).update(strategy)
                    
                    updates[strategy_id] = {
                        'old_threshold': old_threshold,
                        'new_threshold': new_threshold,
                        'win_rate': metrics['win_rate']
                    }
                    
                    logger.info(f"Updated {strategy_id}: conviction {old_threshold} -> {new_threshold}")
            
            except Exception as e:
                logger.error(f"Error applying self-correction to {strategy_id}: {e}")
        
        return updates


def main_pre_market(request):
    """Cloud Function entry point for pre-market screening."""
    analyst = MetaAnalyst()
    result = analyst.pre_market_screener(universe_size=300)
    return json.dumps(result), 200


def main_post_market(request):
    """Cloud Function entry point for post-market retrospective."""
    analyst = MetaAnalyst()
    result = analyst.post_market_retrospective(window_days=30)
    return json.dumps(result), 200
