"""
Database Connection Wizard View.
First-run setup wizard for configuring SQL Server connection.

This component guides users through:
1. Selecting/entering SQL Server instance
2. Authentication (SQL or Windows)
3. Database selection
4. Connection testing and saving
"""

import streamlit as st
from typing import Optional

from src.sql_server_discovery import (
    discover_sql_servers,
    get_odbc_drivers,
    list_databases,
    test_connection,
    save_connection_to_env,
    is_configured,
    get_current_config
)


def render_connection_wizard(on_complete: Optional[callable] = None) -> bool:
    """
    Renders the database connection wizard.
    
    Args:
        on_complete: Callback function to call when wizard completes successfully
        
    Returns:
        True if configuration was completed successfully
    """
    
    # Initialize wizard state
    if "wizard_step" not in st.session_state:
        st.session_state.wizard_step = 1
    if "wizard_server" not in st.session_state:
        st.session_state.wizard_server = ""
    if "wizard_user" not in st.session_state:
        st.session_state.wizard_user = "sa"
    if "wizard_password" not in st.session_state:
        st.session_state.wizard_password = ""
    if "wizard_database" not in st.session_state:
        st.session_state.wizard_database = ""
    if "wizard_use_windows_auth" not in st.session_state:
        st.session_state.wizard_use_windows_auth = False
    if "wizard_databases_list" not in st.session_state:
        st.session_state.wizard_databases_list = []
    if "wizard_error" not in st.session_state:
        st.session_state.wizard_error = ""
    
    # Header
    st.markdown("# 🔌 Kreator Połączenia z Bazą Danych")
    st.markdown("---")
    
    # Progress indicator
    steps = ["🖥️ Serwer", "🔐 Logowanie", "🗄️ Baza danych", "✅ Potwierdzenie"]
    cols = st.columns(4)
    for i, (col, step_name) in enumerate(zip(cols, steps), 1):
        with col:
            if i < st.session_state.wizard_step:
                st.success(step_name)
            elif i == st.session_state.wizard_step:
                st.info(f"**{step_name}**")
            else:
                st.markdown(f"<span style='color:gray'>{step_name}</span>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Render current step
    if st.session_state.wizard_step == 1:
        return _render_step_server()
    elif st.session_state.wizard_step == 2:
        return _render_step_login()
    elif st.session_state.wizard_step == 3:
        return _render_step_database()
    elif st.session_state.wizard_step == 4:
        return _render_step_confirm(on_complete)
    
    return False


def _render_step_server() -> bool:
    """Step 1: Server selection"""
    
    st.markdown("## 🖥️ Krok 1: Wybierz Serwer SQL")
    st.markdown("Aplikacja wykrywa lokalne instancje SQL Server automatycznie.")
    
    # Discover servers
    with st.spinner("Wykrywanie serwerów SQL..."):
        discovered_servers = discover_sql_servers()
    
    if discovered_servers:
        st.success(f"🔍 Wykryto {len(discovered_servers)} serwer(y) SQL")
    else:
        st.warning("⚠️ Nie wykryto żadnych lokalnych serwerów SQL. Wprowadź adres ręcznie.")
    
    # Server selection
    server_options = ["-- Wprowadź ręcznie --"] + discovered_servers
    
    selected_option = st.selectbox(
        "Wybierz serwer:",
        server_options,
        index=0 if not st.session_state.wizard_server else (
            server_options.index(st.session_state.wizard_server) 
            if st.session_state.wizard_server in server_options 
            else 0
        ),
        help="Wybierz wykryty serwer lub wprowadź adres ręcznie"
    )
    
    if selected_option == "-- Wprowadź ręcznie --":
        manual_server = st.text_input(
            "Adres serwera:",
            value=st.session_state.wizard_server if st.session_state.wizard_server not in server_options else "",
            placeholder="np. SERWER\\INSTANCJA lub localhost\\SQL",
            help="Format: NAZWA_KOMPUTERA\\INSTANCJA lub adres IP\\INSTANCJA"
        )
        server = manual_server
    else:
        server = selected_option
    
    # Show available ODBC drivers
    with st.expander("ℹ️ Dostępne sterowniki ODBC"):
        drivers = get_odbc_drivers()
        if drivers:
            for driver in drivers:
                st.markdown(f"• {driver}")
        else:
            st.warning("Nie znaleziono sterowników ODBC dla SQL Server!")
    
    # Error display
    if st.session_state.wizard_error:
        st.error(st.session_state.wizard_error)
        st.session_state.wizard_error = ""
    
    # Navigation
    col1, col2 = st.columns([1, 1])
    
    with col2:
        if st.button("Dalej ➡️", type="primary", use_container_width=True):
            if server and server != "-- Wprowadź ręcznie --":
                st.session_state.wizard_server = server
                st.session_state.wizard_step = 2
                st.rerun()
            else:
                st.session_state.wizard_error = "⚠️ Wprowadź adres serwera"
                st.rerun()
    
    return False


def _render_step_login() -> bool:
    """Step 2: Authentication"""
    
    st.markdown("## 🔐 Krok 2: Uwierzytelnianie")
    st.markdown(f"Serwer: **{st.session_state.wizard_server}**")
    
    # Auth type selection
    auth_type = st.radio(
        "Typ uwierzytelniania:",
        ["SQL Server Authentication", "Windows Authentication"],
        index=1 if st.session_state.wizard_use_windows_auth else 0,
        help="Windows Auth używa poświadczeń aktualnie zalogowanego użytkownika"
    )
    
    st.session_state.wizard_use_windows_auth = (auth_type == "Windows Authentication")
    
    # Credentials input (only for SQL Auth)
    if not st.session_state.wizard_use_windows_auth:
        user = st.text_input(
            "Użytkownik:",
            value=st.session_state.wizard_user,
            placeholder="np. sa",
            help="Nazwa użytkownika SQL Server"
        )
        
        password = st.text_input(
            "Hasło:",
            type="password",
            value=st.session_state.wizard_password,
            help="Hasło użytkownika SQL Server"
        )
        
        st.session_state.wizard_user = user
        st.session_state.wizard_password = password
    else:
        st.info("🔑 Zostanie użyte konto Windows: " + st.session_state.get('windows_user', 'bieżący użytkownik'))
    
    # Error display
    if st.session_state.wizard_error:
        st.error(st.session_state.wizard_error)
        st.session_state.wizard_error = ""
    
    # Navigation
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("⬅️ Wstecz", use_container_width=True):
            st.session_state.wizard_step = 1
            st.rerun()
    
    with col3:
        if st.button("Połącz i kontynuuj ➡️", type="primary", use_container_width=True):
            # Validate inputs
            if not st.session_state.wizard_use_windows_auth:
                if not st.session_state.wizard_user:
                    st.session_state.wizard_error = "⚠️ Wprowadź nazwę użytkownika"
                    st.rerun()
                    return False
                if not st.session_state.wizard_password:
                    st.session_state.wizard_error = "⚠️ Wprowadź hasło"
                    st.rerun()
                    return False
            
            # Try to list databases
            with st.spinner("Łączenie z serwerem..."):
                databases, error = list_databases(
                    st.session_state.wizard_server,
                    st.session_state.wizard_user,
                    st.session_state.wizard_password,
                    st.session_state.wizard_use_windows_auth
                )
            
            if error:
                st.session_state.wizard_error = f"❌ Błąd połączenia: {error}"
                st.rerun()
            elif not databases:
                st.session_state.wizard_error = "⚠️ Nie znaleziono żadnych baz danych (oprócz systemowych)"
                st.rerun()
            else:
                st.session_state.wizard_databases_list = databases
                st.session_state.wizard_step = 3
                st.rerun()
    
    return False


def _render_step_database() -> bool:
    """Step 3: Database selection"""
    
    st.markdown("## 🗄️ Krok 3: Wybierz Bazę Danych")
    st.markdown(f"Serwer: **{st.session_state.wizard_server}**")
    
    databases = st.session_state.wizard_databases_list
    
    if databases:
        st.success(f"✅ Połączono! Znaleziono {len(databases)} baz(y) danych.")
        
        # Highlight common databases
        common_dbs = ['cdn_test', 'cdn_mietex', 'cdn_optima']
        highlighted = [db for db in databases if any(c in db.lower() for c in ['cdn', 'optima', 'test'])]
        others = [db for db in databases if db not in highlighted]
        
        # Reorder: highlighted first
        sorted_databases = highlighted + others
        
        selected_db = st.selectbox(
            "Wybierz bazę danych:",
            sorted_databases,
            index=sorted_databases.index(st.session_state.wizard_database) if st.session_state.wizard_database in sorted_databases else 0,
            help="Wybierz bazę danych, z którą chcesz pracować"
        )
        
        st.session_state.wizard_database = selected_db
        
        # Show database hint
        if 'cdn' in selected_db.lower():
            st.info("💡 Wykryto bazę Comarch ERP Optima")
    else:
        st.error("❌ Brak dostępnych baz danych")
    
    # Error display
    if st.session_state.wizard_error:
        st.error(st.session_state.wizard_error)
        st.session_state.wizard_error = ""
    
    # Navigation
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("⬅️ Wstecz", use_container_width=True):
            st.session_state.wizard_step = 2
            st.rerun()
    
    with col3:
        if st.button("Dalej ➡️", type="primary", use_container_width=True, disabled=not databases):
            st.session_state.wizard_step = 4
            st.rerun()
    
    return False


def _render_step_confirm(on_complete: Optional[callable] = None) -> bool:
    """Step 4: Confirmation and save"""
    
    st.markdown("## ✅ Krok 4: Potwierdzenie")
    
    # Summary
    st.markdown("### Podsumowanie konfiguracji:")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**🖥️ Serwer:** `{st.session_state.wizard_server}`")
        st.markdown(f"**🗄️ Baza danych:** `{st.session_state.wizard_database}`")
    with col2:
        auth_type = "Windows" if st.session_state.wizard_use_windows_auth else "SQL Server"
        st.markdown(f"**🔐 Uwierzytelnianie:** {auth_type}")
        if not st.session_state.wizard_use_windows_auth:
            st.markdown(f"**👤 Użytkownik:** `{st.session_state.wizard_user}`")
    
    st.markdown("---")
    
    # Test connection
    st.markdown("### Test połączenia:")
    
    if st.button("🔄 Testuj połączenie", use_container_width=True):
        with st.spinner("Testowanie połączenia..."):
            success, message = test_connection(
                st.session_state.wizard_server,
                st.session_state.wizard_database,
                st.session_state.wizard_user,
                st.session_state.wizard_password,
                st.session_state.wizard_use_windows_auth
            )
        
        if success:
            st.success(message)
            st.session_state.wizard_connection_tested = True
        else:
            st.error(message)
            st.session_state.wizard_connection_tested = False
    
    # Error display
    if st.session_state.wizard_error:
        st.error(st.session_state.wizard_error)
        st.session_state.wizard_error = ""
    
    st.markdown("---")
    
    # Navigation
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("⬅️ Wstecz", use_container_width=True):
            st.session_state.wizard_step = 3
            st.rerun()
    
    with col3:
        save_disabled = not st.session_state.get('wizard_connection_tested', False)
        
        if st.button(
            "💾 Zapisz i uruchom aplikację", 
            type="primary", 
            use_container_width=True,
            disabled=save_disabled,
            help="Najpierw przetestuj połączenie"
        ):
            with st.spinner("Zapisywanie konfiguracji..."):
                success, message = save_connection_to_env(
                    st.session_state.wizard_server,
                    st.session_state.wizard_database,
                    st.session_state.wizard_user,
                    st.session_state.wizard_password,
                    st.session_state.wizard_use_windows_auth
                )
            
            if success:
                st.success(message)
                st.balloons()
                
                # Clear wizard state
                for key in list(st.session_state.keys()):
                    if key.startswith('wizard_'):
                        del st.session_state[key]
                
                # Trigger callback
                if on_complete:
                    on_complete()
                
                st.info("🔄 Aplikacja zostanie przeładowana...")
                st.rerun()
                return True
            else:
                st.session_state.wizard_error = message
                st.rerun()
    
    if save_disabled:
        st.caption("💡 Kliknij 'Testuj połączenie' aby odblokować zapis")
    
    return False


def render_reconfigure_button():
    """
    Renders a small button to reconfigure database connection.
    Can be placed in sidebar or settings.
    """
    if st.button("🔧 Rekonfiguruj połączenie", help="Uruchom kreator połączenia ponownie"):
        # Reset wizard state to trigger wizard on next load
        for key in list(st.session_state.keys()):
            if key.startswith('wizard_'):
                del st.session_state[key]
        st.session_state.wizard_step = 1
        st.session_state.force_wizard = True
        st.rerun()
