"""
AI Supply Assistant - Main Application Entry Point
Version: 1.1.0

This module serves as a thin wrapper that initializes the Streamlit app
and delegates to modular GUI components.

SECURITY: All credentials must be loaded from .env file.
No hardcoded defaults for sensitive data.
"""

import streamlit as st
import pandas as pd

# Local imports
from src.db_connector import DatabaseConnector
from src.preprocessing import prepare_time_series, fill_missing_weeks
from src.gui.components.sidebar import render_sidebar
from src.gui.views.analysis import render_analysis_view
from src.gui.views.prediction import render_prediction_view
from src.gui.views.assistant import render_assistant_view
from src.forecasting import Forecaster


# Page Config
st.set_page_config(
    page_title="AI Supply Assistant",
    page_icon="🏭",
    layout="wide"
)

# Title
st.title("🏭 AI Supply Assistant (Produkcja by CTI)")


@st.cache_resource
def get_db_connection():
    """Creates cached database connection."""
    return DatabaseConnector()


def main():
    """Main application logic."""
    try:
        # Render Sidebar (handles connection and mode selection)
        sidebar_state = render_sidebar(
            db_connector=DatabaseConnector,
            rerun_callback=st.rerun
        )
        
        # Get DB Connection
        db = get_db_connection()
        
        # Global Data Fetch
        with st.spinner("Pobieranie danych globalnych..."):
            df_stock = db.get_current_stock()
            product_map = {}
            sorted_product_ids = []
            
            if not df_stock.empty:
                df_stock['TowarId'] = pd.to_numeric(
                    df_stock['TowarId'], errors='coerce'
                ).fillna(0).astype(int)
                df_stock['DisplayName'] = df_stock['Name'] + " (" + df_stock['Code'] + ")"
                product_map = dict(zip(df_stock['TowarId'], df_stock['DisplayName']))
                sorted_product_ids = df_stock['TowarId'].tolist()
        
        # Route to appropriate view based on mode
        app_mode = sidebar_state['app_mode']
        start_date = sidebar_state['start_date']
        end_date = sidebar_state['end_date']
        
        if app_mode == "Analiza Danych":
            render_analysis_view(
                db=db,
                product_map=product_map,
                sorted_product_ids=sorted_product_ids,
                start_date=start_date,
                end_date=end_date,
                prepare_time_series=prepare_time_series,
                fill_missing_weeks=fill_missing_weeks
            )
            
        elif app_mode == "Predykcja":
            render_prediction_view(
                db=db,
                product_map=product_map,
                sorted_product_ids=sorted_product_ids,
                start_date=start_date,
                end_date=end_date,
                prepare_time_series=prepare_time_series,
                fill_missing_weeks=fill_missing_weeks,
                Forecaster=Forecaster
            )
            
        elif app_mode == "AI Assistant (GenAI)":
            render_assistant_view(
                db=db,
                product_map=product_map,
                sorted_product_ids=sorted_product_ids,
                prepare_time_series=prepare_time_series
            )
            
    except Exception as e:
        st.error(f"Błąd krytyczny aplikacji: {e}")


# Run the app
if __name__ == "__main__":
    main()
