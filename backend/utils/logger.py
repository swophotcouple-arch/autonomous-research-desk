"""Utilities for logging and monitoring."""

import logging
import json
from datetime import datetime
from google.cloud import firestore
from typing import Dict, Any

logger = logging.getLogger(__name__)


class SystemLogger:
    """System-wide logging to Firestore."""

    def __init__(self):
        """Initialize system logger."""
        self.db = firestore.Client()

    def log_event(self, event_type: str, data: Dict[str, Any], severity: str = 'INFO') -> None:
        """Log event to Firestore.
        
        Args:
            event_type: Type of event (e.g., 'trade_approved', 'regime_changed')
            data: Event data
            severity: Log level (INFO, WARNING, ERROR)
        """
        try:
            log_entry = {
                'timestamp': datetime.utcnow(),
                'event_type': event_type,
                'severity': severity,
                'data': data
            }
            
            self.db.collection('system_logs').add(log_entry)
        except Exception as e:
            logger.error(f"Error logging event: {e}")

    def log_trade(self, trade_data: Dict[str, Any]) -> None:
        """Log mock trade execution."""
        self.log_event('mock_trade_executed', trade_data, 'INFO')

    def log_veto(self, veto_reason: str, proposal: Dict) -> None:
        """Log trade veto by Supervisor."""
        self.log_event('trade_vetoed', {
            'reason': veto_reason,
            'proposal': proposal
        }, 'WARNING')

    def log_regime_change(self, old_regime: str, new_regime: str) -> None:
        """Log regime change detection."""
        self.log_event('regime_changed', {
            'old_regime': old_regime,
            'new_regime': new_regime
        }, 'INFO')

    def log_cost_warning(self, service: str, current_usage: float, limit: float) -> None:
        """Log GCP cost/quota warning."""
        self.log_event('cost_warning', {
            'service': service,
            'current_usage': current_usage,
            'limit': limit
        }, 'WARNING')
