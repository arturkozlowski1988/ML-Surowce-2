"""
Sidebar component for the AI Supply Assistant.
Handles connection settings, filters, and mode selection.
"""

import streamlit as st
import pandas as pd
import os
import urllib.parse
from typing import Callable, Optional


def render_connection_settings(on_connect: Optional[Callable] = None):
    """
    Renders the database connection settings expander.
    
    SECURITY: No default credentials are pre-filled.
    User must explicitly enter credentials or rely on .env file.
    """
    with st.expander("🔌 Ustawienia Połączenia"):
        st.caption("Jeśli połączenie z .env nie działa, wprowadź dane ręcznie.")
        
        # SECURITY FIX: Empty defaults - no hardcoded credentials
        manual_server = st.text_input(
            "Server", 
            value="",  # Was: "DESKTOP-JHQ03JE\\SQL" - REMOVED for security
            placeholder="np. SERVER\\INSTANCE",
            help="Nazwa serwera SQL (np. DESKTOP-JHQ03JE\\SQL)"
        )
        manual_db = st.text_input(
            "Database", 
            value="",  # Was: "cdn_test" - REMOVED for security
            placeholder="np. cdn_test",
            help="Nazwa bazy danych"
        )
        manual_user = st.text_input(
            "User", 
            value="",  # Was: "sa" - REMOVED for security
            placeholder="np. sa",
            help="Nazwa użytkownika bazy danych"
        )
        manual_pass = st.text_input(
            "Password", 
            type="password",
            value="",
            help="Hasło użytkownika"
        )
        
        if st.button("Połącz Ręcznie"):
            # Validate all fields are filled
            if not all([manual_server, manual_db, manual_user, manual_pass]):
                st.error("⚠️ Wszystkie pola są wymagane do połączenia ręcznego.")
                return False
            
            try:
                conn_str = (
                    f"mssql+pyodbc://{manual_user}:{urllib.parse.quote_plus(manual_pass)}"
                    f"@{manual_server}/{manual_db}"
                    f"?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes"
                )
                # Update Env Var for this session
                os.environ['DB_CONN_STR'] = conn_str
                
                if on_connect:
                    on_connect()
                    
                return True
            except Exception as e:
                st.error(f"Błąd: {e}")
                return False
    
    return None


def render_connection_status(is_connected: bool):
    """Renders the connection status indicator."""
    if is_connected:
        st.success("🟢 Utworzono połączenie z bazą")
    else:
        st.error("🔴 Błąd połączenia z bazą")


def render_mode_selector() -> str:
    """Renders the application mode selector."""
    return st.selectbox(
        "Wybierz tryb:", 
        ["Analiza Danych", "Predykcja", "AI Assistant (GenAI)"]
    )


def render_date_filters() -> tuple:
    """
    Renders date filter inputs.
    Returns (start_date, end_date) tuple.
    """
    st.header("Filtry")
    today = pd.Timestamp.now().date()
    start_date = st.date_input(
        "Od daty:", 
        value=today - pd.Timedelta(weeks=26)
    )
    end_date = st.date_input(
        "Do daty:", 
        value=today + pd.Timedelta(weeks=8)
    )
    return start_date, end_date


def render_sidebar(db_connector, rerun_callback: Callable) -> dict:
    """
    Main sidebar rendering function.
    
    Args:
        db_connector: Database connector class (not instance)
        rerun_callback: Function to call for page rerun (st.rerun)
    
    Returns:
        dict with keys: app_mode, start_date, end_date, db_status, database_name, selected_warehouses
    """
    with st.sidebar:
        st.markdown("### 📦 Konfiguracja")
        
        # Database Selector (NEW)
        st.markdown("**🗄️ Baza Danych**")
        available_databases = ["cdn_test", "cdn_mietex"]
        
        if "selected_database" not in st.session_state:
            st.session_state["selected_database"] = "cdn_test"
        
        selected_db = st.selectbox(
            "Wybierz bazę:",
            available_databases,
            index=available_databases.index(st.session_state["selected_database"]),
            key="database_selector"
        )
        
        # Track database change for rerun
        if selected_db != st.session_state["selected_database"]:
            st.session_state["selected_database"] = selected_db
            st.session_state["db_status"] = False  # Reset connection
            st.session_state.pop("selected_warehouses", None)  # Clear warehouse selection
            st.session_state.pop("analysis_viewmodel", None)  # Clear cached viewmodel
            # Clear DB connection cache for all databases
            keys_to_remove = [k for k in st.session_state.keys() if k.startswith("db_connection_")]
            for key in keys_to_remove:
                st.session_state.pop(key, None)
            rerun_callback()
        
        # Connection Status
        if "db_status" not in st.session_state:
            st.session_state["db_status"] = False
        
        # Connection Settings
        def handle_connect():
            try:
                db_conn = db_connector(database_name=st.session_state["selected_database"])
                if db_conn.test_connection():
                    st.session_state["db_status"] = True
                    st.success("Połączono!")
                    rerun_callback()
                else:
                    st.error("Nieudane połączenie.")
            except Exception as e:
                st.error(f"Błąd: {e}")
        
        render_connection_settings(on_connect=handle_connect)
        
        # Auto-connect if not connected
        if not st.session_state["db_status"]:
            try:
                db_conn = db_connector(database_name=st.session_state["selected_database"])
                if db_conn.test_connection():
                    st.session_state["db_status"] = True
            except:
                pass
        
        render_connection_status(st.session_state["db_status"])
        
        # Warehouse Selector (NEW)
        st.divider()
        st.markdown("**🏭 Magazyny**")
        
        if "selected_warehouses" not in st.session_state:
            st.session_state["selected_warehouses"] = []
        
        if st.session_state["db_status"]:
            try:
                db_conn = db_connector(database_name=st.session_state["selected_database"])
                df_warehouses = db_conn.get_warehouses(only_with_stock=True)
                
                if not df_warehouses.empty:
                    warehouse_options = dict(zip(
                        df_warehouses['MagId'], 
                        df_warehouses['Symbol'] + " - " + df_warehouses['Name']
                    ))
                    
                    selected_wh = st.multiselect(
                        "Filtruj po magazynach:",
                        options=list(warehouse_options.keys()),
                        default=st.session_state.get("selected_warehouses", []),
                        format_func=lambda x: warehouse_options.get(x, str(x)),
                        help="Zostaw puste, aby pokazać wszystkie magazyny"
                    )
                    st.session_state["selected_warehouses"] = selected_wh
                    
                    # Warehouse summary
                    if selected_wh:
                        total_stock = df_warehouses[df_warehouses['MagId'].isin(selected_wh)]['TotalStock'].sum()
                        st.caption(f"📦 Wybrano: {len(selected_wh)} mag. | Stan: {total_stock:,.0f}")
                    else:
                        st.caption(f"📦 Wszystkie magazyny ({len(df_warehouses)})")
                else:
                    st.info("Brak magazynów ze stanem > 0")
            except Exception as e:
                st.warning(f"Nie można pobrać magazynów: {e}")
        else:
            st.info("Połącz się z bazą, aby wybrać magazyny")
        
        st.divider()
        app_mode = render_mode_selector()
        
        # Date Filters
        start_date, end_date = render_date_filters()
        
        st.markdown("---")
        st.caption(f"v1.2.0 | {st.session_state['selected_database']}")
        
        return {
            'app_mode': app_mode,
            'start_date': start_date,
            'end_date': end_date,
            'db_status': st.session_state["db_status"],
            'database_name': st.session_state["selected_database"],
            'selected_warehouses': st.session_state.get("selected_warehouses", [])
        }
