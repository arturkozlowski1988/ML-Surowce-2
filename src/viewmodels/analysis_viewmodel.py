"""
Analysis ViewModel - MVVM layer for data analysis functionality.
Encapsulates data loading, filtering, and summary calculations.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
import logging

from src.viewmodels.base_viewmodel import BaseViewModel, ViewModelState, LoadingState

logger = logging.getLogger('AnalysisViewModel')


@dataclass
class AnalysisSummary:
    """Summary statistics for analysis view."""
    total_quantity: float = 0.0
    total_products: int = 0
    avg_per_product: float = 0.0
    top_products: List[Dict] = field(default_factory=list)
    trend_direction: str = "stable"  # "up", "down", "stable"
    query_time_ms: float = 0.0


@dataclass
class AnalysisState(ViewModelState):
    """State for Analysis ViewModel."""
    df_stock: Optional[pd.DataFrame] = None
    df_historical: Optional[pd.DataFrame] = None
    df_filtered: Optional[pd.DataFrame] = None
    product_map: Dict[int, str] = field(default_factory=dict)
    summary: Optional[AnalysisSummary] = None
    
    # Filter state
    start_date: Optional[Any] = None
    end_date: Optional[Any] = None
    selected_products: List[int] = field(default_factory=list)


class AnalysisViewModel(BaseViewModel):
    """
    ViewModel for Data Analysis module.
    
    Responsibilities:
    - Load stock and historical data
    - Filter by date range and products
    - Calculate summary statistics
    - Generate product rankings
    """
    
    def __init__(self, db, prepare_time_series=None, fill_missing_weeks=None):
        super().__init__(db)
        self.prepare_time_series = prepare_time_series
        self.fill_missing_weeks = fill_missing_weeks
        self._state = AnalysisState()
    
    @property
    def analysis_state(self) -> AnalysisState:
        return self._state
    
    def load_all_data(self, force_refresh: bool = False) -> bool:
        """
        Load all data for analysis view.
        
        Returns:
            True if successful
        """
        try:
            # Step 1: Load stock
            self._set_loading(0.2, "Pobieranie stanów magazynowych...")
            df_stock = self._load_stock(force_refresh)
            
            # Step 2: Load historical
            self._set_loading(0.5, "Pobieranie danych historycznych...")
            df_historical = self._load_historical(force_refresh)
            
            # Step 3: Build product map
            self._set_loading(0.8, "Przygotowywanie mapy produktów...")
            self._build_product_map()
            
            # Step 4: Calculate initial summary
            self._set_loading(0.9, "Obliczanie statystyk...")
            self._calculate_summary()
            
            self._set_success()
            return True
            
        except Exception as e:
            self._set_error(str(e))
            return False
    
    def _load_stock(self, force_refresh: bool) -> pd.DataFrame:
        """Load current stock data."""
        cache_key = "stock_data"
        
        if not force_refresh:
            cached = self._get_cached(cache_key)
            if cached is not None:
                self._state.df_stock = cached
                return cached
        
        df = self.db.get_current_stock()
        self._state.df_stock = df
        self._set_cached(cache_key, df)
        
        return df
    
    def _load_historical(self, force_refresh: bool) -> pd.DataFrame:
        """Load and preprocess historical data."""
        cache_key = "historical_data"
        
        if not force_refresh:
            cached = self._get_cached(cache_key)
            if cached is not None:
                self._state.df_historical = cached
                return cached
        
        df_raw = self.db.get_historical_data()
        
        if df_raw.empty:
            self._state.df_historical = df_raw
            return df_raw
        
        # Preprocess
        if self.prepare_time_series and self.fill_missing_weeks:
            df_clean = self.prepare_time_series(df_raw)
            df_full = self.fill_missing_weeks(df_clean)
        else:
            df_full = df_raw
        
        self._state.df_historical = df_full
        self._set_cached(cache_key, df_full)
        
        return df_full
    
    def _build_product_map(self):
        """Build product ID to display name map."""
        if self._state.df_stock is None or self._state.df_stock.empty:
            self._state.product_map = {}
            return
        
        df = self._state.df_stock
        
        # Create display name from Name and Code
        if 'Name' in df.columns and 'Code' in df.columns:
            df = df.copy()
            df['DisplayName'] = df['Name'].astype(str) + " (" + df['Code'].astype(str) + ")"
            self._state.product_map = dict(zip(df['TowarId'], df['DisplayName']))
        elif 'Name' in df.columns:
            self._state.product_map = dict(zip(df['TowarId'], df['Name']))
        else:
            self._state.product_map = {pid: str(pid) for pid in df['TowarId'].unique()}
    
    def apply_date_filter(self, start_date, end_date):
        """Apply date range filter."""
        self._state.start_date = start_date
        self._state.end_date = end_date
        
        if self._state.df_historical is None or self._state.df_historical.empty:
            self._state.df_filtered = pd.DataFrame()
            return
        
        df = self._state.df_historical
        
        if 'Date' in df.columns:
            mask = (df['Date'].dt.date >= start_date) & (df['Date'].dt.date <= end_date)
            self._state.df_filtered = df[mask]
        else:
            self._state.df_filtered = df
        
        # Recalculate summary
        self._calculate_summary()
    
    def _calculate_summary(self):
        """Calculate summary statistics."""
        df = self._state.df_filtered if self._state.df_filtered is not None else self._state.df_historical
        
        if df is None or df.empty:
            self._state.summary = AnalysisSummary()
            return
        
        summary = AnalysisSummary()
        
        # Total quantity
        if 'Quantity' in df.columns:
            summary.total_quantity = float(df['Quantity'].sum())
        
        # Unique products
        if 'TowarId' in df.columns:
            summary.total_products = df['TowarId'].nunique()
            
            if summary.total_products > 0:
                summary.avg_per_product = summary.total_quantity / summary.total_products
        
        # Top products
        if 'TowarId' in df.columns and 'Quantity' in df.columns:
            top_df = df.groupby('TowarId')['Quantity'].sum().nlargest(5)
            summary.top_products = [
                {
                    'id': pid,
                    'name': self._state.product_map.get(pid, str(pid)),
                    'quantity': qty
                }
                for pid, qty in top_df.items()
            ]
        
        # Trend direction
        if 'Date' in df.columns and 'Quantity' in df.columns:
            weekly = df.groupby(pd.Grouper(key='Date', freq='W'))['Quantity'].sum()
            if len(weekly) >= 4:
                first_half = weekly.iloc[:len(weekly)//2].mean()
                second_half = weekly.iloc[len(weekly)//2:].mean()
                
                if second_half > first_half * 1.1:
                    summary.trend_direction = "up"
                elif second_half < first_half * 0.9:
                    summary.trend_direction = "down"
                else:
                    summary.trend_direction = "stable"
        
        self._state.summary = summary
    
    def get_sorted_product_ids(self) -> List[int]:
        """Get product IDs sorted by usage (most used first)."""
        if self._state.df_historical is None or self._state.df_historical.empty:
            return []
        
        df = self._state.df_historical
        
        if 'TowarId' not in df.columns or 'Quantity' not in df.columns:
            return list(df['TowarId'].unique()) if 'TowarId' in df.columns else []
        
        # Sum by product and sort descending
        usage = df.groupby('TowarId')['Quantity'].sum().sort_values(ascending=False)
        return list(usage.index)
    
    def get_product_details(self, product_id: int) -> Dict[str, Any]:
        """Get detailed information about a specific product."""
        details = {
            'id': product_id,
            'name': self._state.product_map.get(product_id, str(product_id))
        }
        
        # Stock info
        if self._state.df_stock is not None:
            stock_row = self._state.df_stock[self._state.df_stock['TowarId'] == product_id]
            if not stock_row.empty:
                row = stock_row.iloc[0]
                details['current_stock'] = row.get('Stock', 0)
                details['code'] = row.get('Code', '')
        
        # Usage info
        if self._state.df_historical is not None:
            hist = self._state.df_historical[self._state.df_historical['TowarId'] == product_id]
            if not hist.empty:
                details['total_usage'] = hist['Quantity'].sum()
                details['avg_weekly'] = hist['Quantity'].mean()
                details['weeks_count'] = len(hist)
        
        return details
