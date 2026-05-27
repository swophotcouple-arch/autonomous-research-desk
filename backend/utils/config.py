"""Configuration management utilities."""

from google.cloud import firestore
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages system configuration from Firestore."""

    def __init__(self):
        """Initialize config manager."""
        self.db = firestore.Client()
        self._cache = {}

    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """Get configuration for specific agent.
        
        Args:
            agent_name: Name of agent (e.g., 'meta_analyst', 'sentinel')
            
        Returns:
            Config dictionary
        """
        if agent_name in self._cache:
            return self._cache[agent_name]
        
        try:
            doc = self.db.collection('system_config').document(agent_name).get()
            if doc.exists:
                config = doc.to_dict()
                self._cache[agent_name] = config
                return config
        except Exception as e:
            logger.error(f"Error loading config for {agent_name}: {e}")
        
        return {}

    def get_strategy_config(self, strategy_id: str) -> Dict[str, Any]:
        """Get strategy configuration from registry.
        
        Args:
            strategy_id: Strategy identifier
            
        Returns:
            Strategy config dictionary
        """
        try:
            doc = self.db.collection('strategy_registry').document(strategy_id).get()
            if doc.exists:
                return doc.to_dict()
        except Exception as e:
            logger.error(f"Error loading strategy {strategy_id}: {e}")
        
        return {}

    def update_strategy_config(self, strategy_id: str, updates: Dict[str, Any]) -> bool:
        """Update strategy configuration.
        
        Args:
            strategy_id: Strategy identifier
            updates: Dictionary of updates
            
        Returns:
            True if successful
        """
        try:
            self.db.collection('strategy_registry').document(strategy_id).update(updates)
            return True
        except Exception as e:
            logger.error(f"Error updating strategy {strategy_id}: {e}")
            return False
