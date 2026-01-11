"""
Admin Panel View.
Provides user management, settings, dashboard and audit interface for administrators.

Extended in v1.6.0 with:
- Dashboard KPI tab
- Audit Log tab
- Alerts Configuration tab
"""

from datetime import datetime
from pathlib import Path

import streamlit as st

# Project root for model scanning
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
MODELS_DIR = PROJECT_ROOT / "models"


def render_admin_view():
    """
    Renders the admin panel for user management and settings.
    Only accessible by admin users.
    """
    from src.gui.views.login_view import get_current_user

    # Check permissions
    user = get_current_user()
    if not user or not user.get("can_manage_users"):
        st.error("🚫 Brak uprawnień do zarządzania użytkownikami")
        return

    st.subheader("⚙️ Panel Administracyjny")

    # Create tabs for different admin functions - expanded with new tabs
    tabs = st.tabs(
        [
            "📊 Dashboard",
            "👥 Użytkownicy",
            "🤖 Ustawienia LLM",
            "📥 Pobieranie Modeli",
            "⚙️ Konfiguracja ML",
            "🗄️ Uprawnienia Baz",
            "🔔 Alerty",
            "📝 Edycja Promptów",
            "📋 Audyt",
            "🔧 Ustawienia Systemowe",
        ]
    )

    with tabs[0]:
        _render_dashboard_tab()

    with tabs[1]:
        _render_users_tab()

    with tabs[2]:
        _render_llm_settings_tab()

    with tabs[3]:
        _render_model_download_tab()

    with tabs[4]:
        _render_ml_config_tab()

    with tabs[5]:
        _render_database_permissions_tab()

    with tabs[6]:
        _render_alerts_tab()

    with tabs[7]:
        _render_prompts_tab()

    with tabs[8]:
        _render_audit_tab()

    with tabs[9]:
        _render_system_settings_tab()


# =============================================================================
# DASHBOARD TAB
# =============================================================================


def _render_dashboard_tab():
    """Renders the admin dashboard with KPIs."""
    from src.security.auth import get_auth_manager
    from src.services.audit_service import get_audit_service

    st.markdown("### 📊 Dashboard Administracyjny")

    audit = get_audit_service()
    auth = get_auth_manager()

    # Get statistics
    stats = audit.get_user_stats(days_back=7)
    users = auth.get_all_users()

    # KPI metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("👥 Użytkownicy", len(users), help="Łączna liczba zarejestrowanych użytkowników")

    with col2:
        st.metric("📈 Akcje (7 dni)", stats["total_actions"], help="Liczba akcji wykonanych w ostatnim tygodniu")

    with col3:
        st.metric("🔄 Aktywni (7 dni)", stats["unique_users"], help="Unikalnych użytkowników w ostatnim tygodniu")

    with col4:
        ai_requests = stats["by_action"].get("ANALYSIS_RAW", 0) + stats["by_action"].get("ANALYSIS_BOM", 0)
        st.metric("🤖 Zapytań AI", ai_requests, help="Analizy AI w ostatnim tygodniu")

    st.markdown("---")

    # Activity breakdown
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("**Aktywność wg użytkownika:**")
        if stats["by_user"]:
            user_df = [{"Użytkownik": k, "Akcje": v} for k, v in stats["by_user"].items()]
            user_df.sort(key=lambda x: x["Akcje"], reverse=True)
            st.dataframe(user_df[:10], use_container_width=True)
        else:
            st.info("Brak danych")

    with col_right:
        st.markdown("**Typy akcji:**")
        if stats["by_action"]:
            action_df = [{"Typ": k, "Liczba": v} for k, v in stats["by_action"].items()]
            action_df.sort(key=lambda x: x["Liczba"], reverse=True)
            st.dataframe(action_df[:10], use_container_width=True)
        else:
            st.info("Brak danych")

    # Last logins
    st.markdown("---")
    st.markdown("**Ostatnie logowania:**")
    recent_logins = audit.get_entries(limit=5, action_filter="LOGIN")
    if recent_logins:
        for entry in recent_logins:
            ts = entry.timestamp[:19].replace("T", " ")
            st.caption(f"🔐 {entry.username} - {ts}")
    else:
        st.info("Brak logowań w historii")


# =============================================================================
# USERS TAB
# =============================================================================


def _render_users_tab():
    """Renders the user management tab."""
    from src.gui.views.login_view import get_current_user
    from src.security.auth import get_auth_manager

    auth = get_auth_manager()
    user = get_current_user()

    # Current users table
    st.markdown("### Lista użytkowników")

    users = auth.get_all_users()

    if users:
        # Create display data
        user_data = []
        for u in users:
            role_display = "🔑 Administrator" if u.role == "admin" else "📊 Zakupowiec"
            db_display = u.assigned_database or "Wszystkie"
            llm_display = u.llm_engine or "Globalny"
            user_data.append(
                {
                    "Użytkownik": u.username,
                    "Nazwa": u.display_name or u.username,
                    "Rola": role_display,
                    "Baza": db_display,
                    "LLM": llm_display,
                }
            )

        st.dataframe(user_data, use_container_width=True)
    else:
        st.info("Brak użytkowników")

    st.markdown("---")

    # Subtabs for user operations
    subtab1, subtab2, subtab3 = st.tabs(["➕ Dodaj", "🔑 Zmień hasło", "🗑️ Usuń"])

    with subtab1:
        _render_add_user_form(auth)

    with subtab2:
        _render_change_password_form(auth, users)

    with subtab3:
        _render_delete_user_form(auth, users, user["username"])


def _render_add_user_form(auth):
    """Renders form to add new user."""
    from src.security.auth import UserRole

    with st.form("add_user_form"):
        new_username = st.text_input("Nazwa użytkownika", placeholder="np. jan.kowalski")
        new_display_name = st.text_input("Imię i nazwisko", placeholder="np. Jan Kowalski")
        new_password = st.text_input("Hasło", type="password", placeholder="Min. 6 znaków")
        new_password_confirm = st.text_input("Potwierdź hasło", type="password")
        new_role = st.selectbox(
            "Rola",
            options=["purchaser", "admin"],
            format_func=lambda x: "📊 Zakupowiec" if x == "purchaser" else "🔑 Administrator",
        )

        if st.form_submit_button("➕ Dodaj użytkownika", use_container_width=True):
            if not new_username:
                st.error("⚠️ Wprowadź nazwę użytkownika")
            elif len(new_password) < 6:
                st.error("⚠️ Hasło musi mieć minimum 6 znaków")
            elif new_password != new_password_confirm:
                st.error("⚠️ Hasła nie są identyczne")
            else:
                role_enum = UserRole.ADMIN if new_role == "admin" else UserRole.PURCHASER
                success = auth.create_user(
                    username=new_username,
                    password=new_password,
                    role=role_enum,
                    display_name=new_display_name or new_username,
                )

                if success:
                    st.success(f"✅ Użytkownik '{new_username}' został utworzony")
                    st.rerun()
                else:
                    st.error(f"❌ Użytkownik '{new_username}' już istnieje")


def _render_change_password_form(auth, users):
    """Renders form to change user password."""
    if not users:
        st.info("Brak użytkowników")
        return

    with st.form("change_password_form"):
        usernames = [u.username for u in users]
        selected_user = st.selectbox("Użytkownik", usernames)
        new_pass = st.text_input("Nowe hasło", type="password")
        new_pass_confirm = st.text_input("Potwierdź nowe hasło", type="password")

        if st.form_submit_button("🔑 Zmień hasło", use_container_width=True):
            if len(new_pass) < 6:
                st.error("⚠️ Hasło musi mieć minimum 6 znaków")
            elif new_pass != new_pass_confirm:
                st.error("⚠️ Hasła nie są identyczne")
            else:
                if auth.change_password(selected_user, new_pass):
                    st.success(f"✅ Hasło dla '{selected_user}' zostało zmienione")
                else:
                    st.error("❌ Nie udało się zmienić hasła")


def _render_delete_user_form(auth, users, current_username):
    """Renders form to delete user."""
    deletable_users = [u for u in users if u.username != current_username]

    if not deletable_users:
        st.info("Brak użytkowników do usunięcia")
        return

    with st.form("delete_user_form"):
        usernames = [u.username for u in deletable_users]
        user_to_delete = st.selectbox("Użytkownik do usunięcia", usernames)
        st.warning("⚠️ Ta operacja jest nieodwracalna!")
        confirm = st.checkbox("Potwierdzam usunięcie użytkownika")

        if st.form_submit_button("🗑️ Usuń użytkownika", use_container_width=True):
            if not confirm:
                st.error("⚠️ Potwierdź usunięcie zaznaczając checkbox")
            else:
                if auth.delete_user(user_to_delete):
                    st.success(f"✅ Użytkownik '{user_to_delete}' został usunięty")
                    st.rerun()
                else:
                    st.error("❌ Nie można usunąć ostatniego administratora")


# =============================================================================
# MODEL DOWNLOAD TAB
# =============================================================================


def _render_model_download_tab():
    """
    Renders model download and management tab.
    Allows downloading LLM models from HuggingFace and managing local models.
    """
    st.markdown("### 📥 Pobieranie Modeli LLM")
    st.info(
        """
    **Zarządzanie modelami AI** - pobieraj modele językowe z HuggingFace Hub.
    Modele są zapisywane lokalnie w folderze `models/`.
    """
    )

    try:
        from src.services.model_downloader import AVAILABLE_MODELS, ModelInfo, get_model_downloader
    except ImportError as e:
        st.error(f"Nie można załadować modułu pobierania: {e}")
        return

    downloader = get_model_downloader()

    # Section 1: Local Models
    st.markdown("---")
    st.markdown("#### 💾 Zainstalowane modele")

    local_models = downloader.get_local_models()

    if local_models:
        for model in local_models:
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                st.markdown(f"**{model['name']}**")
                st.caption(f"{model['description']} | {model['size_gb']:.1f} GB")
            with col2:
                st.success("✅ Zainstalowany")
            with col3:
                if st.button("🗑️", key=f"del_{model['filename']}", help="Usuń model"):
                    if downloader.delete_model(model["filename"]):
                        st.success(f"Usunięto: {model['filename']}")
                        st.rerun()
                    else:
                        st.error("Błąd usuwania")
    else:
        st.warning("Brak zainstalowanych modeli. Pobierz model poniżej.")

    # Section 2: Available Models
    st.markdown("---")
    st.markdown("#### 📦 Dostępne modele do pobrania")

    # Check for huggingface_hub
    try:
        import huggingface_hub

        hf_available = True
    except ImportError:
        hf_available = False
        st.error("⚠️ Brak biblioteki `huggingface_hub`. Zainstaluj:")
        st.code("pip install huggingface_hub", language="bash")

    # Group models by family
    recommended = [m for m in AVAILABLE_MODELS if m.recommended]
    others = [m for m in AVAILABLE_MODELS if not m.recommended]

    # Recommended models
    if recommended:
        st.markdown("##### ⭐ Zalecane")
        for model in recommended:
            _render_model_card(model, downloader, hf_available)

    # Other models
    st.markdown("##### 📋 Inne modele")
    for model in others:
        _render_model_card(model, downloader, hf_available)

    # Section 3: Custom model download
    st.markdown("---")
    with st.expander("🔧 Pobierz niestandardowy model"):
        st.markdown(
            """
        Podaj dane modelu GGUF z HuggingFace Hub:
        - Otwórz stronę modelu na HuggingFace
        - Znajdź plik `.gguf` w zakładce "Files"
        - Skopiuj nazwę repozytorium i nazwę pliku
        """
        )

        custom_repo = st.text_input("Repozytorium (repo_id)", placeholder="np. TheBloke/Llama-2-7B-GGUF")
        custom_file = st.text_input("Nazwa pliku", placeholder="np. llama-2-7b.Q4_K_M.gguf")

        if st.button("📥 Pobierz niestandardowy model", disabled=not hf_available):
            if custom_repo and custom_file:
                custom_model = ModelInfo(
                    name=custom_file,
                    repo_id=custom_repo,
                    filename=custom_file,
                    size_gb=0,
                    description="Niestandardowy model",
                )
                _download_model_with_progress(custom_model, downloader)
            else:
                st.warning("Podaj repozytorium i nazwę pliku")


def _render_model_card(model: "ModelInfo", downloader: "ModelDownloader", hf_available: bool):
    """Render a single model card with download button."""
    is_installed = (downloader.models_dir / model.filename).exists()

    with st.container():
        col1, col2, col3 = st.columns([3, 1, 1.5])

        with col1:
            badge = "⭐ " if model.recommended else ""
            st.markdown(f"**{badge}{model.name}**")
            st.caption(f"{model.description}")

            # Direct links
            st.markdown(
                f"""
            <a href="{model.hf_url}" style="text-decoration:none; margin-right: 10px;">💾 Pobierz plik</a>
            <a href="{model.hf_page_url}" style="text-decoration:none;">🌐 Strona modelu</a>
            """,
                unsafe_allow_html=True,
            )

        with col2:
            st.markdown(f"**{model.size_gb:.1f} GB**")

        with col3:
            if is_installed:
                st.success("✅ Zainstalowany")
            elif hf_available:
                if st.button("📥 Pobierz", key=f"download_{model.filename}"):
                    _download_model_with_progress(model, downloader)
            else:
                st.button("📥 Pobierz", key=f"download_{model.filename}", disabled=True)


def _download_model_with_progress(model: "ModelInfo", downloader: "ModelDownloader"):
    """Download a model with progress bar."""
    import time

    progress_bar = st.progress(0, text=f"Rozpoczynam pobieranie: {model.name}")
    status_text = st.empty()

    def update_progress(progress):
        pct = progress.progress_percent / 100
        progress_bar.progress(
            pct,
            text=f"Pobieranie: {progress.downloaded_gb:.2f} / {progress.total_gb:.2f} GB ({progress.progress_percent:.1f}%)",
        )

    try:
        result = downloader.download_model(model, progress_callback=update_progress)

        if result.is_complete:
            progress_bar.progress(1.0, text="✅ Pobieranie zakończone!")
            status_text.success(f"Model {model.name} został pobrany pomyślnie!")
            time.sleep(2)
            st.rerun()
        elif result.is_error:
            progress_bar.empty()
            status_text.error(f"❌ Błąd pobierania: {result.error_message}")
        else:
            progress_bar.empty()
            status_text.warning("Pobieranie anulowane")
    except Exception as e:
        progress_bar.empty()
        status_text.error(f"❌ Błąd: {e}")


# =============================================================================
# ML CONFIGURATION TAB
# =============================================================================


def _render_ml_config_tab():
    """
    Renders ML hyperparameter configuration tab.
    Allows administrators to tune ML model parameters.
    """
    try:
        from src.forecasting import Forecaster
        from src.ml_config import MLConfig, load_config, reset_to_defaults, save_config
    except ImportError as e:
        st.error(f"Nie można załadować modułu ml_config: {e}")
        return

    st.markdown("### ⚙️ Konfiguracja Modeli ML")
    st.info(
        """
    **Tuning hiperparametrów** - dostosuj parametry modeli uczenia maszynowego.
    Zmiany wpływają na dokładność i czas treningu prognoz.
    """
    )

    config = load_config()

    with st.form("ml_config_form"):
        # Random Forest
        st.markdown("---")
        st.markdown("### 🌲 Random Forest")
        st.caption("Ensemble drzew decyzyjnych - dobry balans dokładności i szybkości.")

        col1, col2 = st.columns(2)
        with col1:
            rf_n_estimators = st.slider(
                "Liczba drzew",
                min_value=10,
                max_value=500,
                value=config.random_forest.n_estimators,
                step=10,
                help="Więcej drzew = lepsza dokładność, dłuższy trening",
            )
            rf_max_depth = st.slider(
                "Maksymalna głębokość",
                min_value=1,
                max_value=50,
                value=config.random_forest.max_depth or 20,
                help="Ogranicza złożoność drzewa, zapobiega przeuczeniu",
            )
        with col2:
            rf_min_samples_split = st.slider(
                "Min próbek do podziału",
                min_value=2,
                max_value=20,
                value=config.random_forest.min_samples_split,
                help="Wyższa wartość = prostszy, bardziej uogólniony model",
            )
            rf_min_samples_leaf = st.slider(
                "Min próbek w liściu",
                min_value=1,
                max_value=10,
                value=config.random_forest.min_samples_leaf,
                help="Zapobiega tworzeniu zbyt szczegółowych reguł",
            )

        # Gradient Boosting
        st.markdown("---")
        st.markdown("### 📈 Gradient Boosting")
        st.caption("Sekwencyjne uczenie na błędach - często najdokładniejszy.")

        col3, col4 = st.columns(2)
        with col3:
            gb_n_estimators = st.slider(
                "Liczba estymatorów",
                min_value=10,
                max_value=500,
                value=config.gradient_boosting.n_estimators,
                step=10,
                help="Więcej etapów = lepsza dokładność, dłuższy trening",
                key="gb_n_est",
            )
            gb_learning_rate = st.slider(
                "Współczynnik uczenia",
                min_value=0.01,
                max_value=1.0,
                value=config.gradient_boosting.learning_rate,
                step=0.01,
                help="Niższy = stabilniejsze wyniki, wymaga więcej estymatorów",
            )
        with col4:
            gb_max_depth = st.slider(
                "Głębokość drzewa",
                min_value=1,
                max_value=10,
                value=config.gradient_boosting.max_depth,
                help="Zalecane 3-5 dla gradient boosting",
                key="gb_depth",
            )
            gb_subsample = st.slider(
                "Frakcja próbkowania",
                min_value=0.5,
                max_value=1.0,
                value=config.gradient_boosting.subsample,
                step=0.1,
                help="Mniej niż 1.0 = stochastyczny gradient boosting",
            )

        # LSTM Deep Learning
        st.markdown("---")
        st.markdown("### 🧠 LSTM (Deep Learning)")

        # Check if TensorFlow is available
        lstm_available = Forecaster.is_lstm_available()
        if lstm_available:
            st.caption("Sieć neuronowa z pamięcią długoterminową - rozpoznaje złożone wzorce.")
        else:
            st.warning("⚠️ TensorFlow nie jest zainstalowany. LSTM niedostępny.")
            st.code("pip install tensorflow", language="bash")

        col5, col6 = st.columns(2)
        with col5:
            lstm_units = st.slider(
                "Neurony LSTM (warstwa 1)",
                min_value=16,
                max_value=256,
                value=config.lstm.units,
                step=16,
                help="Więcej neuronów = większa pojemność modelu",
                disabled=not lstm_available,
            )
            lstm_units_second = st.slider(
                "Neurony LSTM (warstwa 2)",
                min_value=8,
                max_value=128,
                value=config.lstm.units_second,
                step=8,
                help="Zazwyczaj mniej niż warstwa 1",
                disabled=not lstm_available,
            )
            lstm_lookback = st.slider(
                "Okno historyczne (tygodnie)",
                min_value=4,
                max_value=52,
                value=config.lstm.lookback,
                help="Ile tygodni wstecz analizujemy",
                disabled=not lstm_available,
            )
        with col6:
            lstm_epochs = st.slider(
                "Epoki treningu",
                min_value=10,
                max_value=200,
                value=config.lstm.epochs,
                step=10,
                help="Więcej = lepsze dopasowanie, ryzyko przeuczenia",
                disabled=not lstm_available,
            )
            lstm_dropout = st.slider(
                "Dropout (regularyzacja)",
                min_value=0.0,
                max_value=0.5,
                value=config.lstm.dropout,
                step=0.05,
                help="Zapobiega przeuczeniu (0.1-0.3 zalecane)",
                disabled=not lstm_available,
            )
            lstm_batch_size = st.slider(
                "Rozmiar batcha",
                min_value=8,
                max_value=128,
                value=config.lstm.batch_size,
                step=8,
                help="Większy = szybszy trening, mniej stabilny",
                disabled=not lstm_available,
            )

        # Global settings
        st.markdown("---")
        st.markdown("### 🎯 Ustawienia globalne")

        col7, col8 = st.columns(2)
        with col7:
            weeks_ahead = st.slider(
                "Domyślny horyzont prognozy (tygodnie)",
                min_value=1,
                max_value=12,
                value=config.weeks_ahead,
                help="Ile tygodni do przodu prognozować",
            )
        with col8:
            enable_cv = st.checkbox(
                "Włącz walidację krzyżową",
                value=config.enable_cross_validation,
                help="Oceniaj model na danych historycznych przed prognozą",
            )

        # Action buttons
        st.markdown("---")
        col_save, col_reset = st.columns(2)

        with col_save:
            save_clicked = st.form_submit_button("💾 Zapisz konfigurację", use_container_width=True)
        with col_reset:
            reset_clicked = st.form_submit_button("🔄 Przywróć domyślne", use_container_width=True)

        if save_clicked:
            # Update config with new values
            config.random_forest.n_estimators = rf_n_estimators
            config.random_forest.max_depth = rf_max_depth if rf_max_depth < 50 else None
            config.random_forest.min_samples_split = rf_min_samples_split
            config.random_forest.min_samples_leaf = rf_min_samples_leaf

            config.gradient_boosting.n_estimators = gb_n_estimators
            config.gradient_boosting.learning_rate = gb_learning_rate
            config.gradient_boosting.max_depth = gb_max_depth
            config.gradient_boosting.subsample = gb_subsample

            config.lstm.units = lstm_units
            config.lstm.units_second = lstm_units_second
            config.lstm.epochs = lstm_epochs
            config.lstm.dropout = lstm_dropout
            config.lstm.lookback = lstm_lookback
            config.lstm.batch_size = lstm_batch_size

            config.weeks_ahead = weeks_ahead
            config.enable_cross_validation = enable_cv

            if save_config(config):
                st.success("✅ Konfiguracja ML zapisana!")
                st.rerun()
            else:
                st.error("❌ Błąd zapisu konfiguracji")

        if reset_clicked:
            reset_to_defaults()
            st.success("✅ Przywrócono ustawienia domyślne")
            st.rerun()


# =============================================================================
# LLM SETTINGS TAB
# =============================================================================


def _render_llm_settings_tab():
    """Renders LLM settings tab."""
    from src.config_manager import get_config_manager

    # Pre-load OpenRouter models (outside form)
    try:
        from src.ai_engine.openrouter_client import OpenRouterClient

        has_openrouter = True
    except ImportError:
        has_openrouter = False

    if has_openrouter and "openrouter_models_list" not in st.session_state:
        st.session_state.openrouter_models_list = OpenRouterClient.get_available_models()

    config = get_config_manager()
    llm_settings = config.get_llm_settings()

    st.markdown("### Globalne Ustawienia AI")

    col_head, col_btn = st.columns([0.75, 0.25])
    with col_head:
        st.info("Ustawienia stosowane dla użytkowników bez indywidualnych przypisań.")
    with col_btn:
        if has_openrouter:
            if st.button("🔄 Odśwież OpenRouter", help="Pobierz świeżą listę modeli"):
                with st.spinner("Pobieranie..."):
                    st.session_state.openrouter_models_list = OpenRouterClient.get_available_models(force_refresh=True)
                st.rerun()

    with st.form("llm_settings_form"):
        # Default AI Engine - now includes OpenRouter
        engine_options = [
            "Local LLM (Embedded)",
            "Ollama (Local Server)",
            "Google Gemini (Cloud)",
            "OpenRouter (Cloud - 100+ modeli)",
        ]
        current_engine_idx = 0
        for i, opt in enumerate(engine_options):
            if opt == llm_settings.default_engine:
                current_engine_idx = i
                break

        new_engine = st.selectbox("Domyślny silnik AI", engine_options, index=current_engine_idx)

        # Local LLM Model
        st.markdown("**Local LLM**")
        available_models = []
        if MODELS_DIR.exists():
            for f in MODELS_DIR.glob("*.gguf"):
                size_mb = f.stat().st_size / (1024**2)
                if size_mb >= 500:
                    available_models.append(f.name)

        if available_models:
            current_model_idx = 0
            for i, m in enumerate(available_models):
                if m == llm_settings.default_model:
                    current_model_idx = i
                    break
            new_model = st.selectbox("Domyślny model lokalny", available_models, index=current_model_idx)
        else:
            new_model = llm_settings.default_model
            st.warning("Brak modeli .gguf w folderze /models")

        # Gemini API Key
        st.markdown("**Gemini (Cloud)**")
        new_gemini_key = st.text_input("Klucz API Gemini", value=llm_settings.gemini_api_key, type="password")
        st.caption("Pobierz klucz: [Google AI Studio](https://aistudio.google.com/apikey)")

        # OpenRouter Settings (NEW)
        st.markdown("**OpenRouter (Cloud - 100+ modeli)**")
        st.caption(
            "🆓 Dostępne modele darmowe i płatne. Pobierz klucz: [openrouter.ai/keys](https://openrouter.ai/keys)"
        )

        new_openrouter_key = st.text_input(
            "Klucz API OpenRouter", value=getattr(llm_settings, "openrouter_api_key", ""), type="password"
        )

        # OpenRouter model selection
        # OpenRouter model selection
        if has_openrouter:
            models_list = st.session_state.openrouter_models_list
            or_model_options = [(m.id, m.display_name) for m in models_list]
            or_ids = [m[0] for m in or_model_options]
            or_names = [m[1] for m in or_model_options]

            current_or_model = getattr(llm_settings, "openrouter_model", "meta-llama/llama-3.2-3b-instruct:free")

            # Check if current model exists in list
            if current_or_model in or_ids:
                current_or_idx = or_ids.index(current_or_model)
            else:
                current_or_idx = 0

            new_or_model = st.selectbox(
                "Model OpenRouter",
                options=or_ids,
                format_func=lambda x: or_names[or_ids.index(x)] if x in or_ids else x,
                index=current_or_idx,
                help="🆓 = darmowy, 💰 = płatny",
            )
        else:
            new_or_model = "meta-llama/llama-3.2-3b-instruct:free"
            st.warning("Biblioteka OpenRouterClient niedostępna")

        # Ollama Settings
        st.markdown("**Ollama**")
        new_ollama_host = st.text_input("Host Ollama", value=llm_settings.ollama_host)
        new_ollama_model = st.text_input("Model Ollama", value=llm_settings.ollama_model)

        if st.form_submit_button("💾 Zapisz ustawienia", use_container_width=True):
            config.update_llm_settings(
                default_engine=new_engine,
                default_model=new_model,
                gemini_api_key=new_gemini_key,
                ollama_host=new_ollama_host,
                ollama_model=new_ollama_model,
                openrouter_api_key=new_openrouter_key,
                openrouter_model=new_or_model,
            )
            st.success("✅ Ustawienia LLM zapisane!")
            st.rerun()


# =============================================================================
# DATABASE PERMISSIONS TAB
# =============================================================================


def _render_database_permissions_tab():
    """Renders database permissions tab."""
    from src.config_manager import get_config_manager
    from src.security.auth import get_auth_manager

    auth = get_auth_manager()
    config = get_config_manager()
    users = auth.get_all_users()

    st.markdown("### Przypisanie Baz Danych do Użytkowników")

    available_dbs = config.get_available_databases()
    db_options = ["(Wszystkie dostępne)"] + available_dbs
    engine_options = ["(Globalny)", "Local LLM (Embedded)", "Ollama (Local Server)", "Google Gemini (Cloud)"]

    for user in users:
        with st.expander(f"👤 {user.display_name or user.username} ({user.role})"):
            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                current_db_idx = 0
                if user.assigned_database:
                    try:
                        current_db_idx = db_options.index(user.assigned_database)
                    except ValueError:
                        current_db_idx = 0

                new_db = st.selectbox("Baza", db_options, index=current_db_idx, key=f"db_{user.username}")

            with col2:
                current_engine_idx = 0
                if user.llm_engine:
                    try:
                        current_engine_idx = engine_options.index(user.llm_engine)
                    except ValueError:
                        current_engine_idx = 0

                new_llm = st.selectbox(
                    "Silnik AI", engine_options, index=current_engine_idx, key=f"llm_{user.username}"
                )

            with col3:
                if st.button("💾", key=f"save_{user.username}"):
                    user.assigned_database = None if new_db == "(Wszystkie dostępne)" else new_db
                    user.llm_engine = None if new_llm == "(Globalny)" else new_llm
                    auth._save_users()
                    st.success("✅")
                    st.rerun()


# =============================================================================
# ALERTS TAB
# =============================================================================


def _render_alerts_tab():
    """Renders alerts configuration tab."""
    from src.config_manager import get_config_manager

    config = get_config_manager()
    alerts = config.get_alerts()

    st.markdown("### 🔔 Konfiguracja Alertów")
    st.info("Ustaw progi dla alertów magazynowych i powiadomień.")

    with st.form("alerts_form"):
        st.markdown("**Progi alertów (dni zapasu):**")

        col1, col2 = st.columns(2)
        with col1:
            new_critical = st.number_input(
                "🔴 Próg KRYTYCZNY (dni)",
                min_value=1,
                max_value=30,
                value=alerts.critical_days_threshold,
                help="Produkty z zapasem poniżej tej liczby dni",
            )
        with col2:
            new_low = st.number_input(
                "🟡 Próg NISKI (dni)",
                min_value=1,
                max_value=60,
                value=alerts.low_days_threshold,
                help="Produkty z zapasem poniżej tej liczby dni",
            )

        st.markdown("**Wykrywanie anomalii:**")
        new_anomaly = st.slider(
            "Próg anomalii zużycia (%)",
            min_value=10,
            max_value=200,
            value=alerts.anomaly_percent_threshold,
            help="Zmiana zużycia większa niż X% zostanie oznaczona jako anomalia",
        )

        st.markdown("---")
        st.markdown("**Raporty automatyczne:**")

        col3, col4 = st.columns(2)
        with col3:
            new_daily = st.checkbox("📅 Raport dzienny", value=alerts.daily_report_enabled)
        with col4:
            new_weekly = st.checkbox("📆 Raport tygodniowy", value=alerts.weekly_report_enabled)

        st.markdown("**Powiadomienia email:**")
        new_email_enabled = st.checkbox("📧 Włącz powiadomienia email", value=alerts.enable_email_notifications)

        current_recipients = ", ".join(alerts.email_recipients) if alerts.email_recipients else ""
        new_recipients = st.text_input(
            "Odbiorcy (oddzieleni przecinkiem)", value=current_recipients, placeholder="jan@firma.pl, maria@firma.pl"
        )

        if st.form_submit_button("💾 Zapisz konfigurację alertów", use_container_width=True):
            recipients_list = [r.strip() for r in new_recipients.split(",") if r.strip()]
            config.update_alerts(
                critical_days_threshold=new_critical,
                low_days_threshold=new_low,
                anomaly_percent_threshold=new_anomaly,
                enable_email_notifications=new_email_enabled,
                email_recipients=recipients_list,
                daily_report_enabled=new_daily,
                weekly_report_enabled=new_weekly,
            )
            st.success("✅ Konfiguracja alertów zapisana!")
            st.rerun()


# =============================================================================
# PROMPTS TAB
# =============================================================================


def _render_prompts_tab():
    """Renders prompt editor tab."""
    from src.config_manager import get_config_manager

    config = get_config_manager()
    prompts = config.get_prompts()

    st.markdown("### Edycja Promptów AI")
    st.info("Zmienne w `{nawiasach}` zostaną zastąpione danymi.")

    with st.form("prompts_form"):
        st.markdown("**Prompt Analizy Surowca**")
        st.caption("Zmienne: {product_name}, {mag_context}, {current_stock}, {last_4_weeks}, {avg_consumption}")
        new_raw_prompt = st.text_area("Szablon", value=prompts.raw_material_analysis, height=150, key="raw")

        st.markdown("**Prompt Analizy BOM**")
        st.caption("Zmienne: {product_name}, {plan_qty}, {selected_mag_info}, {bom_summary}, {warehouse_context}")
        new_bom_prompt = st.text_area("Szablon", value=prompts.bom_analysis, height=150, key="bom")

        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("💾 Zapisz prompty", use_container_width=True):
                config.update_prompts(raw_material_analysis=new_raw_prompt, bom_analysis=new_bom_prompt)
                st.success("✅ Prompty zapisane!")
        with col2:
            if st.form_submit_button("🔄 Przywróć domyślne", use_container_width=True):
                config.reset_prompts_to_default()
                st.success("✅ Prompty przywrócone")
                st.rerun()


# =============================================================================
# AUDIT TAB
# =============================================================================


def _render_audit_tab():
    """Renders audit log tab."""
    from src.services.audit_service import get_audit_service

    audit = get_audit_service()

    st.markdown("### 📋 Historia Działań")

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        days_filter = st.selectbox("Okres", [7, 14, 30, 90], format_func=lambda x: f"Ostatnie {x} dni")
    with col2:
        action_filter = st.text_input("Filtr akcji", placeholder="np. LOGIN, ANALYSIS")
    with col3:
        user_filter = st.text_input("Filtr użytkownika", placeholder="np. admin")

    # Get entries
    entries = audit.get_entries(
        limit=200,
        days_back=days_filter,
        action_filter=action_filter if action_filter else None,
        username=user_filter if user_filter else None,
    )

    st.caption(f"Znaleziono: {len(entries)} wpisów")

    if entries:
        # Display as table
        data = []
        for e in entries:
            data.append(
                {
                    "Data/Czas": e.timestamp[:19].replace("T", " "),
                    "Użytkownik": e.username,
                    "Akcja": e.action,
                    "Szczegóły": e.details[:50] + "..." if len(e.details) > 50 else e.details,
                    "Moduł": e.module,
                }
            )

        st.dataframe(data, use_container_width=True, height=400)

        # Export button
        csv = audit.export_to_csv(entries)
        st.download_button("📥 Eksportuj do CSV", csv, f"audit_log_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
    else:
        st.info("Brak wpisów audytu dla wybranych filtrów")


# =============================================================================
# SYSTEM SETTINGS TAB
# =============================================================================


def _render_system_settings_tab():
    """Renders system settings tab."""
    from src.config_manager import get_config_manager

    config = get_config_manager()
    system = config.get_system_settings()

    st.markdown("### Ustawienia Systemowe")

    with st.form("system_settings_form"):
        new_cache_ttl = st.number_input(
            "Cache TTL (sekundy)", min_value=60, max_value=3600, value=system.cache_ttl_seconds
        )
        new_forecast_weeks = st.number_input(
            "Horyzont prognozy (tygodnie)", min_value=4, max_value=52, value=system.max_forecast_weeks
        )
        new_retention = st.number_input(
            "Retencja audytu (dni)", min_value=30, max_value=365, value=system.audit_retention_days
        )

        st.markdown("**Dostępne bazy danych**")
        new_databases = st.text_input("Lista baz (przecinek)", value=", ".join(system.available_databases))

        if st.form_submit_button("💾 Zapisz", use_container_width=True):
            db_list = [db.strip() for db in new_databases.split(",") if db.strip()]
            config.update_system_settings(
                cache_ttl_seconds=new_cache_ttl, max_forecast_weeks=new_forecast_weeks, available_databases=db_list
            )
            st.success("✅ Ustawienia zapisane!")
            st.rerun()

    st.markdown("---")
    st.caption(f"📁 Konfiguracja: `{config.config_file}`")
