"""
Configuration Manager for AI Supply Assistant.
Provides centralized management of application settings including LLM configuration,
prompts, and system parameters.

Settings are stored in config/app_settings.json and can be modified by administrators.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger("ConfigManager")


@dataclass
class LLMSettings:
    """LLM configuration settings."""

    default_engine: str = "Local LLM (Embedded)"
    default_model: str = "qwen2.5-7b-instruct-q3_k_m.gguf"
    gemini_api_key: str = ""
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.2-3b-instruct:free"


@dataclass
class PromptSettings:
    """AI prompt templates."""

    raw_material_analysis: str = ""
    bom_analysis: str = ""


@dataclass
class SystemSettings:
    """System configuration."""

    cache_ttl_seconds: int = 300
    max_forecast_weeks: int = 12
    available_databases: list[str] = field(default_factory=lambda: ["cdn_test", "cdn_mietex"])
    audit_retention_days: int = 90


@dataclass
class AlertSettings:
    """Alert configuration."""

    critical_days_threshold: int = 7
    low_days_threshold: int = 14
    anomaly_percent_threshold: int = 50
    enable_email_notifications: bool = False
    email_recipients: list[str] = field(default_factory=list)
    daily_report_enabled: bool = False
    weekly_report_enabled: bool = True


@dataclass
class AppConfig:
    """Complete application configuration."""

    llm: LLMSettings = field(default_factory=LLMSettings)
    prompts: PromptSettings = field(default_factory=PromptSettings)
    alerts: AlertSettings = field(default_factory=AlertSettings)
    system: SystemSettings = field(default_factory=SystemSettings)


class ConfigManager:
    """
    Manages application configuration with persistence.
    Singleton pattern for app-wide access.
    """

    DEFAULT_CONFIG_FILE = "config/app_settings.json"

    def __init__(self, config_file: str = None):
        """
        Initialize ConfigManager.

        Args:
            config_file: Path to config JSON file. Defaults to config/app_settings.json
        """
        if config_file is None:
            project_root = Path(__file__).parent.parent
            self.config_file = project_root / self.DEFAULT_CONFIG_FILE
        else:
            self.config_file = Path(config_file)

        self._config: AppConfig = AppConfig()
        self._load_config()

    def _ensure_config_dir(self):
        """Ensures config directory exists."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_config(self):
        """Loads configuration from JSON file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, encoding="utf-8") as f:
                    data = json.load(f)

                    # Parse LLM settings
                    if "llm" in data:
                        self._config.llm = LLMSettings(**data["llm"])

                    # Parse prompt settings
                    if "prompts" in data:
                        self._config.prompts = PromptSettings(**data["prompts"])

                    # Parse alerts settings
                    if "alerts" in data:
                        self._config.alerts = AlertSettings(**data["alerts"])

                    # Parse system settings
                    if "system" in data:
                        self._config.system = SystemSettings(**data["system"])

                logger.info(f"Loaded configuration from {self.config_file}")
            except Exception as e:
                logger.error(f"Error loading config: {e}")
                self._create_default_config()
        else:
            self._create_default_config()

    def _create_default_config(self):
        """Creates default configuration file."""
        logger.info("Creating default configuration")
        self._config = AppConfig()
        self._set_default_prompts()
        self.save()

    def _set_default_prompts(self):
        """Sets default AI prompts."""
        self._config.prompts.raw_material_analysis = """Jesteś ekspertem ds. łańcucha dostaw. Przeanalizuj sytuację dla surowca: {product_name}.

DANE:
- Obecny stan magazynowy {mag_context}: {current_stock:.2f}
- Ostatnie 4 tygodnie zużycia: {last_4_weeks}
- Średnie zużycie tygodniowe: {avg_consumption:.2f}

PYTANIA:
1. Czy trend zużycia jest rosnący czy malejący?
2. Na ile tygodni wystarczy obecny zapas (Coverage)?
3. Czy sugerujesz zwiększenie zapasów?
4. Jakie mogą być przyczyny anomalii (jeśli występują)?

Odpowiedz krótko i konkretnie w języku polskim."""

        self._config.prompts.bom_analysis = """Jesteś asystentem zakupowym w fabryce. Planujemy produkcję wyrobu: {product_name}.
Ilość do wyprodukowania: {plan_qty} szt.

Oto analiza zapotrzebowania na surowce (BOM vs Magazyn) {selected_mag_info}:
{bom_summary}
{warehouse_context}

Zadanie:
1. Wskaż krytyczne braki (co musimy pilnie zamówić?).
2. Jeśli są surowce na innych magazynach - zasugeruj przesunięcie międzymagazynowe.
3. Czy są jakieś ryzyka dla ciągłości produkcji?
4. Podaj rekomendację dla działu zakupów.
Odpowiedz krótko i konkretnie w języku polskim."""

    def save(self):
        """Saves current configuration to file."""
        self._ensure_config_dir()

        try:
            data = {
                "llm": asdict(self._config.llm),
                "prompts": asdict(self._config.prompts),
                "alerts": asdict(self._config.alerts),
                "system": asdict(self._config.system),
            }
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved configuration to {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            raise

    # -------------------------------------------------------------------------
    # LLM Settings
    # -------------------------------------------------------------------------

    def get_llm_settings(self) -> LLMSettings:
        """Returns current LLM settings."""
        return self._config.llm

    def update_llm_settings(
        self,
        default_engine: str = None,
        default_model: str = None,
        gemini_api_key: str = None,
        ollama_host: str = None,
        ollama_model: str = None,
        openrouter_api_key: str = None,
        openrouter_model: str = None,
    ):
        """Updates LLM settings."""
        if default_engine is not None:
            self._config.llm.default_engine = default_engine
        if default_model is not None:
            self._config.llm.default_model = default_model
        if gemini_api_key is not None:
            self._config.llm.gemini_api_key = gemini_api_key
        if ollama_host is not None:
            self._config.llm.ollama_host = ollama_host
        if ollama_model is not None:
            self._config.llm.ollama_model = ollama_model
        if openrouter_api_key is not None:
            self._config.llm.openrouter_api_key = openrouter_api_key
        if openrouter_model is not None:
            self._config.llm.openrouter_model = openrouter_model

        self.save()
        logger.info("LLM settings updated")

    def get_user_llm_engine(self, username: str = None) -> str:
        """
        Returns LLM engine for user.
        Falls back to global default if user has no specific assignment.
        """
        if username:
            from src.security.auth import get_auth_manager

            auth = get_auth_manager()
            user = auth.get_user(username)
            if user and user.llm_engine:
                return user.llm_engine

        return self._config.llm.default_engine

    def get_user_llm_model(self, username: str = None) -> str:
        """
        Returns LLM model for user.
        Falls back to global default if user has no specific assignment.
        """
        if username:
            from src.security.auth import get_auth_manager

            auth = get_auth_manager()
            user = auth.get_user(username)
            if user and user.llm_model:
                return user.llm_model

        return self._config.llm.default_model

    # -------------------------------------------------------------------------
    # Prompt Settings
    # -------------------------------------------------------------------------

    def get_prompts(self) -> PromptSettings:
        """Returns current prompt settings."""
        return self._config.prompts

    def update_prompts(self, raw_material_analysis: str = None, bom_analysis: str = None):
        """Updates prompt templates."""
        if raw_material_analysis is not None:
            self._config.prompts.raw_material_analysis = raw_material_analysis
        if bom_analysis is not None:
            self._config.prompts.bom_analysis = bom_analysis

        self.save()
        logger.info("Prompt settings updated")

    def reset_prompts_to_default(self):
        """Resets prompts to default values."""
        self._set_default_prompts()
        self.save()
        logger.info("Prompts reset to defaults")

    # -------------------------------------------------------------------------
    # System Settings
    # -------------------------------------------------------------------------

    def get_system_settings(self) -> SystemSettings:
        """Returns current system settings."""
        return self._config.system

    def get_available_databases(self) -> list[str]:
        """Returns list of available databases."""
        return self._config.system.available_databases

    def update_system_settings(
        self, cache_ttl_seconds: int = None, max_forecast_weeks: int = None, available_databases: list[str] = None
    ):
        """Updates system settings."""
        if cache_ttl_seconds is not None:
            self._config.system.cache_ttl_seconds = cache_ttl_seconds
        if max_forecast_weeks is not None:
            self._config.system.max_forecast_weeks = max_forecast_weeks
        if available_databases is not None:
            self._config.system.available_databases = available_databases

        self.save()
        logger.info("System settings updated")

    # -------------------------------------------------------------------------
    # Alert Settings
    # -------------------------------------------------------------------------

    def get_alerts(self) -> AlertSettings:
        """Returns current alert settings."""
        return self._config.alerts

    def update_alerts(
        self,
        critical_days_threshold: int = None,
        low_days_threshold: int = None,
        anomaly_percent_threshold: int = None,
        enable_email_notifications: bool = None,
        email_recipients: list[str] = None,
        daily_report_enabled: bool = None,
        weekly_report_enabled: bool = None,
    ):
        """Updates alert settings."""
        if critical_days_threshold is not None:
            self._config.alerts.critical_days_threshold = critical_days_threshold
        if low_days_threshold is not None:
            self._config.alerts.low_days_threshold = low_days_threshold
        if anomaly_percent_threshold is not None:
            self._config.alerts.anomaly_percent_threshold = anomaly_percent_threshold
        if enable_email_notifications is not None:
            self._config.alerts.enable_email_notifications = enable_email_notifications
        if email_recipients is not None:
            self._config.alerts.email_recipients = email_recipients
        if daily_report_enabled is not None:
            self._config.alerts.daily_report_enabled = daily_report_enabled
        if weekly_report_enabled is not None:
            self._config.alerts.weekly_report_enabled = weekly_report_enabled

        self.save()
        logger.info("Alert settings updated")


# Singleton instance for app-wide use
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Returns singleton ConfigManager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def reset_config_manager():
    """Resets the singleton (useful for testing)."""
    global _config_manager
    _config_manager = None
