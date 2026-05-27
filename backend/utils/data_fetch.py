"""Data fetching utilities for market data."""

from google.cloud import bigquery
from typing import Dict, List
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class DataFetcher:
    """Fetches market data from BigQuery."""

    def __init__(self, project_id: str):
        """Initialize data fetcher.
        
        Args:
            project_id: GCP project ID
        """
        self.client = bigquery.Client(project=project_id)
        self.project_id = project_id

    def fetch_nse_daily_data(self, ticker: str, days: int = 60) -> pd.DataFrame:
        """Fetch daily OHLCV data for NSE stock.
        
        Args:
            ticker: Stock ticker
            days: Number of days to fetch
            
        Returns:
            DataFrame with OHLCV data
        """
        query = f"""
        SELECT 
            date,
            close_price,
            high_price,
            low_price,
            open_price,
            volume_lakhs,
            adjusted_close
        FROM `{self.project_id}.market_data.nse_daily`
        WHERE ticker = '{ticker}'
            AND date >= DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY)
        ORDER BY date ASC
        """
        
        try:
            df = self.client.query(query).to_pandas()
            return df
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")
            return pd.DataFrame()

    def fetch_nifty_data(self, days: int = 60) -> pd.DataFrame:
        """Fetch Nifty index data."""
        query = f"""
        SELECT 
            date,
            close_price,
            high_price,
            low_price
        FROM `{self.project_id}.market_data.nifty_daily`
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY)
        ORDER BY date ASC
        """
        
        try:
            df = self.client.query(query).to_pandas()
            return df
        except Exception as e:
            logger.error(f"Error fetching Nifty data: {e}")
            return pd.DataFrame()

    def fetch_vix_data(self, days: int = 60) -> pd.DataFrame:
        """Fetch India VIX data."""
        query = f"""
        SELECT 
            date,
            vix_value,
            open_value,
            high_value,
            low_value
        FROM `{self.project_id}.market_data.india_vix_daily`
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY)
        ORDER BY date ASC
        """
        
        try:
            df = self.client.query(query).to_pandas()
            return df
        except Exception as e:
            logger.error(f"Error fetching VIX data: {e}")
            return pd.DataFrame()

    def fetch_sector_data(self, sector: str, days: int = 60) -> pd.DataFrame:
        """Fetch aggregated sector performance data."""
        query = f"""
        SELECT 
            date,
            AVG(close_price) as avg_price,
            SUM(volume_lakhs) as total_volume
        FROM `{self.project_id}.market_data.nse_daily`
        WHERE sector = '{sector}'
            AND date >= DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY)
        GROUP BY date
        ORDER BY date ASC
        """
        
        try:
            df = self.client.query(query).to_pandas()
            return df
        except Exception as e:
            logger.error(f"Error fetching sector data for {sector}: {e}")
            return pd.DataFrame()
