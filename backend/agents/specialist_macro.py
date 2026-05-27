"""Specialist-Macro Agent: Macro Analysis and Headwind Detection."""

import json
import logging
from datetime import datetime
from typing import Dict
from google.cloud import firestore

logger = logging.getLogger(__name__)

db = firestore.Client()


class SpecialistMacro:
    """Specialist-Macro: Detects macro headwinds and economic indicators."""

    def __init__(self):
        """Initialize Specialist-Macro agent."""
        self.db = db
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Load macro specialist config from Firestore."""
        try:
            doc = self.db.collection('system_config').document('specialist_macro').get()
            return doc.to_dict() or {}
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}

    def analyze_macro_environment(self) -> Dict:
        """Analyze current macro environment and detect headwinds.
        
        Returns:
            Dict with macro metrics and alignment scores
        """
        try:
            # Fetch latest macro indicators
            macro_doc = self.db.collection('macro_indicators').document('latest').get()
            if not macro_doc.exists:
                logger.warning("No macro indicators found")
                macro_state = self._get_default_macro_state()
            else:
                macro_state = macro_doc.to_dict()
            
            # Calculate alignment scores
            analysis = {
                'timestamp': datetime.utcnow(),
                'macro_state': macro_state,
                'rate_environment': self._assess_rate_environment(macro_state),
                'inflation_environment': self._assess_inflation(macro_state),
                'liquidity_environment': self._assess_liquidity(macro_state),
                'overall_headwind_score': 0.0  # Will be calculated below
            }
            
            # Combine scores
            scores = [
                analysis['rate_environment'].get('alignment_score', 0.5),
                analysis['inflation_environment'].get('alignment_score', 0.5),
                analysis['liquidity_environment'].get('alignment_score', 0.5)
            ]
            analysis['overall_headwind_score'] = sum(scores) / len(scores)
            
            # Store in Firestore
            self.db.collection('specialist_analysis').document('macro').set(
                analysis,
                merge=True
            )
            
            logger.info(f"Macro analysis completed. Headwind score: {analysis['overall_headwind_score']:.2f}")
            return {'status': 'success', 'analysis': analysis}
            
        except Exception as e:
            logger.error(f"Error in analyze_macro_environment: {e}")
            return {'status': 'error', 'error': str(e)}

    def _get_default_macro_state(self) -> Dict:
        """Return default macro state if none available."""
        return {
            'rbi_repo_rate': 6.5,
            'inflation_rate': 4.5,
            'liquidity_adjusted_rate': 5.8,
            'foreign_inflows': 'neutral',
            'oil_price_usd': 85,
            'usd_inr': 83.5
        }

    def _assess_rate_environment(self, macro_state: Dict) -> Dict:
        """Assess RBI rate and rate-hike expectations."""
        repo_rate = macro_state.get('rbi_repo_rate', 6.5)
        lar = macro_state.get('liquidity_adjusted_rate', 5.8)
        
        # Higher rates = headwind for equities
        if repo_rate >= 7.0:
            alignment_score = 0.3  # Strong headwind
            description = "High rates environment (RBI tightening)"
        elif repo_rate >= 6.0:
            alignment_score = 0.5  # Moderate headwind
            description = "Elevated rates environment"
        else:
            alignment_score = 0.7  # Supportive
            description = "Accommodative rates environment"
        
        return {
            'repo_rate': repo_rate,
            'alignment_score': alignment_score,
            'description': description,
            'allow_trading': alignment_score >= 0.4
        }

    def _assess_inflation(self, macro_state: Dict) -> Dict:
        """Assess inflation levels and trajectory."""
        inflation = macro_state.get('inflation_rate', 4.5)
        
        # RBI target is typically 4% +/- 2%
        rbi_target = 4.0
        
        if inflation > 6.0:
            alignment_score = 0.2  # Strong headwind
            description = "High inflation (above RBI target band)"
        elif inflation > 4.5:
            alignment_score = 0.4  # Moderate headwind
            description = "Elevated inflation"
        else:
            alignment_score = 0.7  # Supportive
            description = "Inflation within RBI target band"
        
        return {
            'inflation_rate': inflation,
            'alignment_score': alignment_score,
            'description': description,
            'allow_trading': alignment_score >= 0.4
        }

    def _assess_liquidity(self, macro_state: Dict) -> Dict:
        """Assess liquidity conditions (forex, oil, etc.)."""
        # Check multiple factors
        oil_price = macro_state.get('oil_price_usd', 85)
        inflows = macro_state.get('foreign_inflows', 'neutral')
        
        # Oil > $100 is headwind; < $70 is supportive
        if oil_price > 100:
            score_oil = 0.3
        elif oil_price > 85:
            score_oil = 0.5
        else:
            score_oil = 0.7
        
        # Foreign inflows
        inflow_scores = {'negative': 0.2, 'neutral': 0.5, 'positive': 0.8}
        score_inflows = inflow_scores.get(inflows, 0.5)
        
        alignment_score = (score_oil + score_inflows) / 2
        description = f"Oil ${oil_price}, FII inflows {inflows}"
        
        return {
            'oil_price': oil_price,
            'foreign_inflows': inflows,
            'alignment_score': alignment_score,
            'description': description,
            'allow_trading': alignment_score >= 0.3
        }


def main(request):
    """Cloud Function entry point for macro analysis."""
    specialist = SpecialistMacro()
    result = specialist.analyze_macro_environment()
    return json.dumps(result, default=str), 200
