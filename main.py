"""
AI Supply Assistant - Main Application Entry Point
Version: 1.4.0

This module serves as a thin wrapper that initializes the Streamlit app
and delegates to modular GUI components.

SECURITY: All credentials must be loaded from .env file.
No hardcoded defaults for sensitive data.

NEW in 1.3.0: First-run connection wizard for easy setup.
NEW in 1.4.0: User authentication and role-based access control.
"""

import pandas as pd
import streamlit as st
import traceback

# Local imports
from src.db_connector import DatabaseConnector
from src.forecasting import Forecaster
from src.gui.components.sidebar import render_sidebar
from src.gui.views.admin_view import render_admin_view
from src.gui.views.analysis import render_analysis_view
from src.gui.views.assistant import render_assistant_view
from src.gui.views.connection_wizard import render_connection_wizard
from src.gui.views.login_view import get_current_user, render_login_view
from src.gui.views.mrp_view import render_mrp_view
from src.gui.views.prediction import render_prediction_view
from src.preprocessing import fill_missing_weeks, prepare_time_series
from src.sql_server_discovery import is_configured

# Page Config
st.set_page_config(page_title="AI Supply Assistant", page_icon="🏭", layout="wide")


def get_db_connection(database_name: str = None, use_demo: bool = False):
    """Creates database connection with optional database name or demo mode.

    OPTIMIZATION: Disposes old connections when switching databases to free resources.
    """
    if use_demo:
        # Use demo connector for test data
        from src.demo_connector import DemoDataConnector

        cache_key = "db_connection_demo"

        # Dispose non-demo connection if switching to demo mode
        old_key = st.session_state.get("_current_db_cache_key")
        if old_key and old_key != cache_key and old_key in st.session_state:
            try:
                st.session_state[old_key].dispose()
            except Exception:
                pass  # Ignore errors during dispose

        st.session_state["_current_db_cache_key"] = cache_key

        if cache_key not in st.session_state:
            st.session_state[cache_key] = DemoDataConnector()
        return st.session_state[cache_key]

    cache_key = f"db_connection_{database_name or 'default'}"

    # Dispose old connection if switching databases
    old_key = st.session_state.get("_current_db_cache_key")
    if old_key and old_key != cache_key and old_key in st.session_state:
        try:
            st.session_state[old_key].dispose()
        except Exception:
            pass  # Ignore errors during dispose

    st.session_state["_current_db_cache_key"] = cache_key

    if cache_key not in st.session_state:
        st.session_state[cache_key] = DatabaseConnector(database_name=database_name)

    return st.session_state[cache_key]


def main():
    """Main application logic."""

    # STEP 1: Check authentication
    if not render_login_view():
        return  # Not logged in, login form is displayed

    # Get current user info
    user = get_current_user()

    # STEP 2: Check if this is first run or wizard was requested (Admin only)
    force_wizard = st.session_state.get("force_wizard", False)

    if not is_configured():
        if user and user.get("can_access_wizard"):
            render_connection_wizard(on_complete=st.rerun)
        else:
            st.error("🚫 Baza danych nie jest skonfigurowana. Skontaktuj się z administratorem.")
        return

    if force_wizard and user and user.get("can_access_wizard"):
        st.session_state.force_wizard = False
        render_connection_wizard(on_complete=st.rerun)
        return

    # Normal app flow - show title
    st.title("🏭 AI Supply Assistant (Produkcja by CTI)")

    try:
        # Render Sidebar (handles connection and mode selection)
        # Pass user permissions to sidebar
        sidebar_state = render_sidebar(
            db_connector=DatabaseConnector,
            rerun_callback=st.rerun,
            user_permissions={
                "can_change_database": user.get("can_change_database", False) if user else False,
                "can_access_wizard": user.get("can_access_wizard", False) if user else False,
                "can_manage_users": user.get("can_manage_users", False) if user else False,
            },
        )

        # Get DB Connection with selected database or demo mode
        demo_mode = st.session_state.get("demo_mode", False)
        database_name = sidebar_state.get("database_name", "cdn_test")
        selected_warehouses = sidebar_state.get("selected_warehouses", [])

        db = get_db_connection(database_name, use_demo=demo_mode)

        # Show active database and warehouse info
        if demo_mode:
            st.info("🎓 **Tryb Demo** - dane testowe (zanonimizowane)")
        elif selected_warehouses:
            st.info(f"🗄️ Baza: **{database_name}** | 🏭 Magazyny: {len(selected_warehouses)} wybranych")
        else:
            st.info(f"🗄️ Baza: **{database_name}** | 🏭 Wszystkie magazyny")

        # Route to appropriate view based on mode
        app_mode = sidebar_state["app_mode"]

        # Handle Admin Panel separately
        if app_mode == "Panel Admina":
            render_admin_view()
            return

        # Global Data Fetch (with warehouse filtering)
        with st.spinner("Pobieranie danych globalnych..."):
            warehouse_ids = selected_warehouses if selected_warehouses else None
            df_stock = db.get_current_stock(warehouse_ids=warehouse_ids)
            product_map = {}
            sorted_product_ids = []

            if not df_stock.empty:
                df_stock["TowarId"] = pd.to_numeric(df_stock["TowarId"], errors="coerce").fillna(0).astype(int)
                df_stock["DisplayName"] = df_stock["Name"] + " (" + df_stock["Code"] + ")"
                # strict=False removed for Python 3.9 compatibility and safe assumption of equal length
                product_map = dict(zip(df_stock["TowarId"], df_stock["DisplayName"]))
                sorted_product_ids = df_stock["TowarId"].tolist()

        start_date = sidebar_state["start_date"]
        end_date = sidebar_state["end_date"]

        if app_mode == "Analiza Danych":
            render_analysis_view(
                db=db,
                product_map=product_map,
                sorted_product_ids=sorted_product_ids,
                start_date=start_date,
                end_date=end_date,
                prepare_time_series=prepare_time_series,
                fill_missing_weeks=fill_missing_weeks,
                warehouse_ids=warehouse_ids,
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
                Forecaster=Forecaster,
            )

        elif app_mode == "MRP Lite":
            render_mrp_view(
                db=db, product_map=product_map, sorted_product_ids=sorted_product_ids, warehouse_ids=warehouse_ids
            )

        elif app_mode == "AI Assistant (GenAI)":
            render_assistant_view(
                db=db,
                product_map=product_map,
                sorted_product_ids=sorted_product_ids,
                prepare_time_series=prepare_time_series,
                warehouse_ids=warehouse_ids,
            )

    except Exception as e:
        st.error(f"Błąd krytyczny aplikacji: {e}")
        st.error(traceback.format_exc())


# Run the app
if __name__ == "__main__":
    main()
