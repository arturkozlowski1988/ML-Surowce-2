"""
ML Configuration - Hyperparameter definitions and management.

Provides dataclass-based configuration for ML models with JSON persistence.
Allows administrators to tune model parameters through the UI.
"""

import json
import logging
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any

logger = logging.getLogger('MLConfig')

# Default config path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
CONFIG_FILE = CONFIG_DIR / "ml_config.json"


@dataclass
class RandomForestConfig:
    """
    Konfiguracja modelu Random Forest.
    
    Attributes:
        n_estimators: Liczba drzew w lesie (więcej = dokładniej, wolniej)
        max_depth: Maksymalna głębokość drzewa (None = bez limitu)
        min_samples_split: Minimalna liczba próbek do podziału węzła
        min_samples_leaf: Minimalna liczba próbek w liściu
        random_state: Ziarno losowości dla powtarzalności
    """
    n_estimators: int = 100
    max_depth: Optional[int] = None
    min_samples_split: int = 2
    min_samples_leaf: int = 1
    random_state: int = 42
    
    # Business-friendly descriptions (Polish)
    DESCRIPTIONS = {
        'n_estimators': 'Liczba drzew decyzyjnych - więcej drzew zwiększa dokładność, ale wydłuża czas treningu',
        'max_depth': 'Maksymalna głębokość drzewa - ogranicza złożoność modelu, zapobiega przeuczeniu',
        'min_samples_split': 'Minimalna liczba próbek do podziału - wyższa wartość = prostszy model',
        'min_samples_leaf': 'Minimalna liczba próbek w liściu - wyższa wartość = większa generalizacja'
    }
    
    RANGES = {
        'n_estimators': (10, 500, 10),  # (min, max, step)
        'max_depth': (1, 50, 1),
        'min_samples_split': (2, 20, 1),
        'min_samples_leaf': (1, 10, 1)
    }


@dataclass
class GradientBoostingConfig:
    """
    Konfiguracja modelu Gradient Boosting.
    
    Attributes:
        n_estimators: Liczba estymatorów (etapów boostingu)
        learning_rate: Współczynnik uczenia (niższy = wolniejsze, stabilniejsze)
        max_depth: Maksymalna głębokość pojedynczego drzewa
        min_samples_split: Minimalna liczba próbek do podziału
        subsample: Frakcja próbek do trenowania każdego drzewa
        random_state: Ziarno losowości
    """
    n_estimators: int = 100
    learning_rate: float = 0.1
    max_depth: int = 3
    min_samples_split: int = 2
    subsample: float = 1.0
    random_state: int = 42
    
    DESCRIPTIONS = {
        'n_estimators': 'Liczba etapów boostingu - więcej = lepsza dokładność, dłuższy trening',
        'learning_rate': 'Współczynnik uczenia - niższy = stabilniejsze wyniki, wymaga więcej estymatorów',
        'max_depth': 'Głębokość pojedynczego drzewa - niższa = mniej przeuczenia',
        'subsample': 'Frakcja danych do treningu - mniej niż 1.0 = regularyzacja stochastyczna'
    }
    
    RANGES = {
        'n_estimators': (10, 500, 10),
        'learning_rate': (0.01, 1.0, 0.01),
        'max_depth': (1, 10, 1),
        'subsample': (0.5, 1.0, 0.1)
    }


@dataclass
class ExponentialSmoothingConfig:
    """
    Konfiguracja modelu Exponential Smoothing (Holt-Winters).
    
    Attributes:
        trend: Typ trendu ('add', 'mul', None)
        seasonal: Typ sezonowości ('add', 'mul', None)
        seasonal_periods: Liczba okresów sezonowości (4 = kwartał)
        damped_trend: Czy tłumić trend (True = bardziej konserwatywne prognozy)
    """
    trend: str = 'add'
    seasonal: str = 'add'
    seasonal_periods: int = 4
    damped_trend: bool = False
    
    DESCRIPTIONS = {
        'trend': 'Typ trendu - addytywny (stały wzrost) lub multiplikatywny (procentowy wzrost)',
        'seasonal': 'Typ sezonowości - addytywny lub multiplikatywny',
        'seasonal_periods': 'Liczba okresów w cyklu sezonowym (4 tygodnie = miesiąc)',
        'damped_trend': 'Tłumienie trendu - włącz dla bardziej ostrożnych prognoz długoterminowych'
    }
    
    RANGES = {
        'seasonal_periods': (2, 52, 1)
    }


@dataclass
class LSTMConfig:
    """
    Konfiguracja modelu LSTM (Deep Learning).
    
    Attributes:
        units: Liczba neuronów LSTM w pierwszej warstwie
        units_second: Liczba neuronów LSTM w drugiej warstwie
        epochs: Liczba epok treningu
        batch_size: Rozmiar batcha
        dropout: Współczynnik dropout (regularyzacja)
        lookback: Okno czasowe (ile tygodni wstecz patrzymy)
        learning_rate: Współczynnik uczenia optymalizatora
    """
    units: int = 64
    units_second: int = 32
    epochs: int = 50
    batch_size: int = 32
    dropout: float = 0.2
    lookback: int = 8
    learning_rate: float = 0.001
    
    DESCRIPTIONS = {
        'units': 'Neurony LSTM (warstwa 1) - więcej = większa pojemność modelu',
        'units_second': 'Neurony LSTM (warstwa 2) - zwykle mniej niż warstwa 1',
        'epochs': 'Epoki treningu - więcej = lepsze dopasowanie (ryzyko przeuczenia)',
        'batch_size': 'Rozmiar batcha - większy = szybszy trening, mniej stabilny',
        'dropout': 'Dropout - zapobiega przeuczeniu (0.1-0.5)',
        'lookback': 'Okno czasowe - ile historycznych tygodni analizujemy',
        'learning_rate': 'Współczynnik uczenia - niższy = stabilniejszy trening'
    }
    
    RANGES = {
        'units': (16, 256, 16),
        'units_second': (8, 128, 8),
        'epochs': (10, 200, 10),
        'batch_size': (8, 128, 8),
        'dropout': (0.0, 0.5, 0.05),
        'lookback': (4, 52, 1),
        'learning_rate': (0.0001, 0.01, 0.0001)
    }


@dataclass
class MLConfig:
    """
    Główna konfiguracja ML zawierająca wszystkie modele.
    """
    random_forest: RandomForestConfig = field(default_factory=RandomForestConfig)
    gradient_boosting: GradientBoostingConfig = field(default_factory=GradientBoostingConfig)
    exponential_smoothing: ExponentialSmoothingConfig = field(default_factory=ExponentialSmoothingConfig)
    lstm: LSTMConfig = field(default_factory=LSTMConfig)
    
    # Global settings
    weeks_ahead: int = 4  # Default forecast horizon
    enable_cross_validation: bool = False
    cross_validation_folds: int = 5
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'random_forest': asdict(self.random_forest),
            'gradient_boosting': asdict(self.gradient_boosting),
            'exponential_smoothing': asdict(self.exponential_smoothing),
            'lstm': asdict(self.lstm),
            'weeks_ahead': self.weeks_ahead,
            'enable_cross_validation': self.enable_cross_validation,
            'cross_validation_folds': self.cross_validation_folds
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'MLConfig':
        """Create from dictionary."""
        return cls(
            random_forest=RandomForestConfig(**data.get('random_forest', {})),
            gradient_boosting=GradientBoostingConfig(**data.get('gradient_boosting', {})),
            exponential_smoothing=ExponentialSmoothingConfig(**data.get('exponential_smoothing', {})),
            lstm=LSTMConfig(**data.get('lstm', {})),
            weeks_ahead=data.get('weeks_ahead', 4),
            enable_cross_validation=data.get('enable_cross_validation', False),
            cross_validation_folds=data.get('cross_validation_folds', 5)
        )


def load_config(config_path: Optional[Path] = None) -> MLConfig:
    """
    Ładuje konfigurację ML z pliku JSON.
    
    Args:
        config_path: Ścieżka do pliku konfiguracyjnego (domyślnie config/ml_config.json)
        
    Returns:
        MLConfig z załadowanymi ustawieniami lub domyślna konfiguracja
    """
    path = config_path or CONFIG_FILE
    
    if path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"ML config loaded from {path}")
            return MLConfig.from_dict(data)
        except Exception as e:
            logger.warning(f"Failed to load ML config: {e}. Using defaults.")
            return MLConfig()
    else:
        logger.info("No ML config file found, using defaults")
        return MLConfig()


def save_config(config: MLConfig, config_path: Optional[Path] = None) -> bool:
    """
    Zapisuje konfigurację ML do pliku JSON.
    
    Args:
        config: Obiekt MLConfig do zapisania
        config_path: Ścieżka do pliku (domyślnie config/ml_config.json)
        
    Returns:
        True jeśli zapis się powiódł
    """
    path = config_path or CONFIG_FILE
    
    try:
        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
        
        logger.info(f"ML config saved to {path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save ML config: {e}")
        return False


def reset_to_defaults(config_path: Optional[Path] = None) -> MLConfig:
    """
    Resetuje konfigurację do wartości domyślnych.
    
    Returns:
        Domyślna konfiguracja MLConfig
    """
    config = MLConfig()
    save_config(config, config_path)
    return config


def get_model_config(model_type: str, config: Optional[MLConfig] = None) -> Dict[str, Any]:
    """
    Pobiera słownik konfiguracji dla konkretnego typu modelu.
    
    Args:
        model_type: Typ modelu ('rf', 'gb', 'es', 'lstm')
        config: Obiekt MLConfig (jeśli None, ładuje z pliku)
        
    Returns:
        Słownik z parametrami gotowymi do przekazania do modelu
    """
    if config is None:
        config = load_config()
    
    if model_type == 'rf':
        rf = config.random_forest
        return {
            'n_estimators': rf.n_estimators,
            'max_depth': rf.max_depth,
            'min_samples_split': rf.min_samples_split,
            'min_samples_leaf': rf.min_samples_leaf,
            'random_state': rf.random_state
        }
    elif model_type == 'gb':
        gb = config.gradient_boosting
        return {
            'n_estimators': gb.n_estimators,
            'learning_rate': gb.learning_rate,
            'max_depth': gb.max_depth,
            'min_samples_split': gb.min_samples_split,
            'subsample': gb.subsample,
            'random_state': gb.random_state
        }
    elif model_type == 'es':
        es = config.exponential_smoothing
        return {
            'trend': es.trend,
            'seasonal': es.seasonal,
            'seasonal_periods': es.seasonal_periods,
            'damped_trend': es.damped_trend
        }
    elif model_type == 'lstm':
        lstm = config.lstm
        return {
            'units': lstm.units,
            'units_second': lstm.units_second,
            'epochs': lstm.epochs,
            'batch_size': lstm.batch_size,
            'dropout': lstm.dropout,
            'lookback': lstm.lookback,
            'learning_rate': lstm.learning_rate
        }
    else:
        logger.warning(f"Unknown model type: {model_type}")
        return {}


# Initialize default config file if it doesn't exist
def init_default_config():
    """Create default config file if it doesn't exist."""
    if not CONFIG_FILE.exists():
        save_config(MLConfig())


# Singleton config instance
_cached_config: Optional[MLConfig] = None


def get_config() -> MLConfig:
    """Get cached config instance (singleton pattern)."""
    global _cached_config
    if _cached_config is None:
        _cached_config = load_config()
    return _cached_config


def refresh_config() -> MLConfig:
    """Force reload config from file."""
    global _cached_config
    _cached_config = load_config()
    return _cached_config
