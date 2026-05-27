"""Backtesting engine using vectorbt."""

import numpy as np
import pandas as pd
from typing import Dict, Tuple

try:
    import vectorbt as vbt
    HAS_VECTORBT = True
except ImportError:
    HAS_VECTORBT = False


class BacktestEngine:
    """Backtesting engine for strategy validation."""

    def __init__(self, slippage_bps: float = 20, commission_bps: float = 50):
        """Initialize backtest engine.
        
        Args:
            slippage_bps: Slippage in basis points
            commission_bps: Commission rate in basis points
        """
        if not HAS_VECTORBT:
            raise ImportError("vectorbt not installed. Run: pip install vectorbt")
        
        self.slippage_bps = slippage_bps
        self.commission_bps = commission_bps

    def backtest_strategy(self, 
                         prices: pd.DataFrame,
                         signals: pd.Series,
                         initial_capital: float = 100000) -> Dict:
        """Run backtest on strategy signals.
        
        Args:
            prices: DataFrame with OHLCV data
            signals: Series with trade signals (1=buy, -1=sell, 0=hold)
            initial_capital: Starting capital
            
        Returns:
            Dict with backtest results
        """
        try:
            # Prepare data for vectorbt
            close_prices = prices['close_price'].values
            
            # Calculate returns
            returns = pd.Series(close_prices).pct_change().fillna(0)
            
            # Apply slippage and commission
            adjusted_returns = returns - (self.slippage_bps / 10000) - (self.commission_bps / 10000)
            
            # Calculate cumulative P&L
            cumulative_pnl = (1 + adjusted_returns).cumprod() * initial_capital
            
            # Metrics
            total_return = (cumulative_pnl.iloc[-1] / initial_capital - 1) * 100
            max_dd = self._calculate_max_drawdown(cumulative_pnl)
            sharpe = self._calculate_sharpe(adjusted_returns)
            win_rate = (adjusted_returns > 0).sum() / len(adjusted_returns) * 100
            
            return {
                'initial_capital': initial_capital,
                'final_capital': float(cumulative_pnl.iloc[-1]),
                'total_return_pct': total_return,
                'max_drawdown_pct': max_dd,
                'sharpe_ratio': sharpe,
                'win_rate_pct': win_rate,
                'trade_count': int((signals != 0).sum())
            }
        
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def _calculate_max_drawdown(cumulative_pnl: pd.Series) -> float:
        """Calculate maximum drawdown."""
        running_max = cumulative_pnl.expanding().max()
        drawdown = (cumulative_pnl - running_max) / running_max
        return float(drawdown.min() * 100)

    @staticmethod
    def _calculate_sharpe(returns: pd.Series, risk_free_rate: float = 0.05) -> float:
        """Calculate Sharpe ratio (annualized)."""
        excess_returns = returns - (risk_free_rate / 252)
        sharpe = np.sqrt(252) * excess_returns.mean() / excess_returns.std()
        return float(sharpe) if not np.isnan(sharpe) else 0.0
