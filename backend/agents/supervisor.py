"""Supervisor Agent: Risk Veto Layer and Trade Approval."""

import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple
from google.cloud import firestore

logger = logging.getLogger(__name__)

db = firestore.Client()


class Supervisor:
    """Supervisor: Evaluates trade proposals and enforces risk constraints."""

    def __init__(self):
        """Initialize Supervisor agent."""
        self.db = db
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Load supervisor config from Firestore."""
        try:
            doc = self.db.collection('system_config').document('supervisor').get()
            return doc.to_dict() or {}
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}

    def evaluate_trade_proposal(self, proposal: Dict) -> Tuple[bool, str, Dict]:
        """Evaluate a trade proposal and approve/veto.
        
        Args:
            proposal: Trade proposal with thesis, ticker, size, etc.
            
        Returns:
            Tuple of (approved: bool, reason: str, details: dict)
        """
        checks = {}
        
        # 1. Regime check
        regime_approved, regime_reason = self._check_regime_compliance(proposal)
        checks['regime'] = {'approved': regime_approved, 'reason': regime_reason}
        
        # 2. Conviction check
        conviction_approved, conviction_reason = self._check_conviction_threshold(proposal)
        checks['conviction'] = {'approved': conviction_approved, 'reason': conviction_reason}
        
        # 3. News sentiment check
        sentiment_approved, sentiment_reason = self._check_news_sentiment(proposal)
        checks['sentiment'] = {'approved': sentiment_approved, 'reason': sentiment_reason}
        
        # 4. Exposure check
        exposure_approved, exposure_reason = self._check_exposure_limits(proposal)
        checks['exposure'] = {'approved': exposure_approved, 'reason': exposure_reason}
        
        # 5. Daily trade limit check
        daily_approved, daily_reason = self._check_daily_trade_limit(proposal)
        checks['daily_limit'] = {'approved': daily_approved, 'reason': daily_reason}
        
        # Overall decision
        all_approved = all(check['approved'] for check in checks.values())
        
        if all_approved:
            final_reason = "Trade approved: All risk checks passed"
            final_details = {'veto_reason': None, 'checks_passed': list(checks.keys())}
        else:
            failed_checks = [k for k, v in checks.items() if not v['approved']]
            final_reason = f"Trade vetoed: Failed checks: {', '.join(failed_checks)}"
            final_details = {
                'veto_reason': final_reason,
                'failed_checks': failed_checks,
                'all_checks': checks
            }
        
        logger.info(f"Trade evaluation: {final_reason}")
        return all_approved, final_reason, final_details

    def _check_regime_compliance(self, proposal: Dict) -> Tuple[bool, str]:
        """Check if trade is allowed in current market regime."""
        try:
            # Fetch current regime
            regime_doc = self.db.collection('system_state').document('regime').get()
            if not regime_doc.exists:
                return False, "Regime not detected"
            
            current_regime = regime_doc.to_dict().get('regime', 'Unknown')
            
            # Fetch strategy config
            strategy_id = proposal.get('thesis', {}).get('strategy_id')
            strat_doc = self.db.collection('strategy_registry').document(strategy_id).get()
            if not strat_doc.exists:
                return False, f"Strategy {strategy_id} not found"
            
            allowed_regimes = strat_doc.to_dict().get('allowed_regimes', [])
            
            if current_regime in allowed_regimes:
                return True, f"Regime {current_regime} is allowed"
            else:
                return False, f"Regime {current_regime} not in allowed list: {allowed_regimes}"
        
        except Exception as e:
            logger.error(f"Error checking regime compliance: {e}")
            return False, f"Error: {str(e)}"

    def _check_conviction_threshold(self, proposal: Dict) -> Tuple[bool, str]:
        """Check if conviction score meets minimum threshold."""
        try:
            conviction = proposal.get('thesis', {}).get('conviction_score', 0)
            strategy_id = proposal.get('thesis', {}).get('strategy_id')
            
            strat_doc = self.db.collection('strategy_registry').document(strategy_id).get()
            if not strat_doc.exists:
                return False, "Strategy not found"
            
            min_conviction = strat_doc.to_dict().get('min_conviction_for_trade', 6)
            
            if conviction >= min_conviction:
                return True, f"Conviction {conviction} >= threshold {min_conviction}"
            else:
                return False, f"Conviction {conviction} below threshold {min_conviction}"
        
        except Exception as e:
            logger.error(f"Error checking conviction: {e}")
            return False, f"Error: {str(e)}"

    def _check_news_sentiment(self, proposal: Dict) -> Tuple[bool, str]:
        """Check if news sentiment meets minimum threshold."""
        try:
            sentiment = proposal.get('thesis', {}).get('news_sentiment', 0)
            strategy_id = proposal.get('thesis', {}).get('strategy_id')
            
            strat_doc = self.db.collection('strategy_registry').document(strategy_id).get()
            if not strat_doc.exists:
                return False, "Strategy not found"
            
            min_sentiment = strat_doc.to_dict().get('news_sentiment_min', -1.0)
            
            if sentiment >= min_sentiment:
                return True, f"Sentiment {sentiment:.2f} >= threshold {min_sentiment}"
            else:
                return False, f"Sentiment {sentiment:.2f} below threshold {min_sentiment}"
        
        except Exception as e:
            logger.error(f"Error checking sentiment: {e}")
            return False, f"Error: {str(e)}"

    def _check_exposure_limits(self, proposal: Dict) -> Tuple[bool, str]:
        """Check per-ticker and per-sector exposure limits."""
        try:
            ticker = proposal.get('ticker')
            strategy_id = proposal.get('thesis', {}).get('strategy_id')
            
            strat_doc = self.db.collection('strategy_registry').document(strategy_id).get()
            if not strat_doc.exists:
                return False, "Strategy not found"
            
            strategy = strat_doc.to_dict()
            max_exposure_pct = strategy.get('max_exposure_per_ticker_pct', 2.0)
            max_sector_pct = strategy.get('max_exposure_per_sector_pct', 10.0)
            
            # For MVP, assume no current exposure (would calculate from mock trades)
            current_ticker_exposure = 0.0
            current_sector_exposure = 0.0
            
            if current_ticker_exposure >= max_exposure_pct:
                return False, f"Ticker exposure {current_ticker_exposure:.1f}% >= limit {max_exposure_pct:.1f}%"
            
            if current_sector_exposure >= max_sector_pct:
                return False, f"Sector exposure {current_sector_exposure:.1f}% >= limit {max_sector_pct:.1f}%"
            
            return True, f"Exposure limits OK: ticker {current_ticker_exposure:.1f}%, sector {current_sector_exposure:.1f}%"
        
        except Exception as e:
            logger.error(f"Error checking exposure: {e}")
            return False, f"Error: {str(e)}"

    def _check_daily_trade_limit(self, proposal: Dict) -> Tuple[bool, str]:
        """Check if daily trade count limit is respected."""
        try:
            strategy_id = proposal.get('thesis', {}).get('strategy_id')
            
            strat_doc = self.db.collection('strategy_registry').document(strategy_id).get()
            if not strat_doc.exists:
                return False, "Strategy not found"
            
            max_trades = strat_doc.to_dict().get('max_trades_per_day', 10)
            
            # Count today's trades
            from datetime import date
            today = date.today()
            
            trades_today = 0
            for doc in self.db.collection('mock_trades').where(
                'strategy_id', '==', strategy_id
            ).where(
                'date', '==', today
            ).stream():
                trades_today += 1
            
            if trades_today >= max_trades:
                return False, f"Daily limit {max_trades} reached ({trades_today} trades today)"
            
            return True, f"Daily trade count: {trades_today}/{max_trades}"
        
        except Exception as e:
            logger.error(f"Error checking daily limit: {e}")
            return False, f"Error: {str(e)}"

    def execute_mock_trade(self, approved_proposal: Dict) -> Dict:
        """Execute approved mock trade and log to Firestore."""
        try:
            mock_trade = {
                'timestamp': datetime.utcnow(),
                'ticker': approved_proposal.get('ticker'),
                'thesis': approved_proposal.get('thesis'),
                'entry_price': approved_proposal.get('entry_price'),
                'quantity': approved_proposal.get('quantity'),
                'status': 'open',
                'pnl_pct': 0.0,  # Will be updated post-market
                'approval_reason': approved_proposal.get('approval_reason')
            }
            
            # Write to Firestore
            self.db.collection('mock_trades').add(mock_trade)
            
            logger.info(f"Mock trade executed: {mock_trade['ticker']}")
            return {'status': 'success', 'trade': mock_trade}
        
        except Exception as e:
            logger.error(f"Error executing mock trade: {e}")
            return {'status': 'error', 'error': str(e)}


def main(request):
    """Cloud Function entry point for supervisor."""
    request_json = request.get_json(silent=True)
    
    supervisor = Supervisor()
    approved, reason, details = supervisor.evaluate_trade_proposal(request_json)
    
    result = {
        'approved': approved,
        'reason': reason,
        'details': details
    }
    
    return json.dumps(result), 200
