"""
Model Manager - Persistence layer for ML models.

Provides save/load functionality for trained sklearn and TensorFlow models
using joblib for sklearn and keras native format for TensorFlow.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import joblib

logger = logging.getLogger("ModelManager")

# Default paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SAVED_MODELS_DIR = PROJECT_ROOT / "saved_models"


@dataclass
class ModelMetadata:
    """Metadata for a saved model."""

    model_type: str  # 'rf', 'gb', 'es', 'lstm'
    product_id: int
    product_name: str
    created_at: str  # ISO timestamp
    training_time_ms: float
    metrics: dict[str, float]
    hyperparameters: dict[str, Any]
    data_info: dict[str, Any]  # rows, date_range, etc.

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ModelMetadata":
        return cls(**data)


@dataclass
class SavedModelInfo:
    """Information about a saved model file."""

    path: str
    filename: str
    model_type: str
    product_id: int
    product_name: str
    created_at: str
    file_size_kb: float
    metrics: dict[str, float]


class ModelManager:
    """
    Zarządza zapisem i odczytem wytrenowanych modeli ML.

    Używa joblib dla modeli sklearn (RF, GB) i keras.save dla LSTM.
    Każdy model jest zapisywany z plikiem metadanych JSON.

    Usage:
        manager = ModelManager()
        path = manager.save_model(model, 'rf', product_id=123, metadata={...})
        model, metadata = manager.load_model(path)
    """

    def __init__(self, models_dir: Optional[Path] = None):
        """
        Initialize ModelManager.

        Args:
            models_dir: Custom directory for saved models. Defaults to saved_models/
        """
        self.models_dir = models_dir or SAVED_MODELS_DIR
        self._ensure_directory()

    def _ensure_directory(self):
        """Create models directory if it doesn't exist."""
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def _generate_filename(self, model_type: str, product_id: int) -> str:
        """Generate unique filename for a model."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{model_type}_product_{product_id}_{timestamp}"

    def save_model(
        self,
        model: Any,
        model_type: str,
        product_id: int,
        product_name: str = "",
        training_time_ms: float = 0.0,
        metrics: Optional[dict[str, float]] = None,
        hyperparameters: Optional[dict[str, Any]] = None,
        data_info: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Zapisuje wytrenowany model do pliku.

        Args:
            model: Wytrenowany model (sklearn lub keras)
            model_type: Typ modelu ('rf', 'gb', 'es', 'lstm')
            product_id: ID produktu dla którego wytrenowano model
            product_name: Nazwa produktu (opcjonalnie)
            training_time_ms: Czas treningu w milisekundach
            metrics: Słownik z metrykami (MAE, RMSE, MAPE, etc.)
            hyperparameters: Użyte hiperparametry
            data_info: Informacje o danych treningowych

        Returns:
            Ścieżka do zapisanego modelu
        """
        base_name = self._generate_filename(model_type, product_id)

        # Create metadata
        metadata = ModelMetadata(
            model_type=model_type,
            product_id=product_id,
            product_name=product_name,
            created_at=datetime.now().isoformat(),
            training_time_ms=training_time_ms,
            metrics=metrics or {},
            hyperparameters=hyperparameters or {},
            data_info=data_info or {},
        )

        try:
            if model_type == "lstm":
                # TensorFlow/Keras model - save in keras format
                model_path = self.models_dir / f"{base_name}.keras"
                model.save(str(model_path))
            else:
                # sklearn model - save with joblib
                model_path = self.models_dir / f"{base_name}.joblib"
                joblib.dump(model, model_path)

            # Save metadata JSON
            metadata_path = self.models_dir / f"{base_name}_metadata.json"
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata.to_dict(), f, indent=2, ensure_ascii=False)

            logger.info(f"Model saved: {model_path}")
            return str(model_path)

        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            raise

    def load_model(self, model_path: str) -> tuple[Any, ModelMetadata]:
        """
        Ładuje zapisany model z metadanymi.

        Args:
            model_path: Ścieżka do pliku modelu (.joblib lub .keras)

        Returns:
            Tuple (model, metadata)
        """
        path = Path(model_path)

        if not path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        try:
            # Load model
            if path.suffix == ".keras":
                # TensorFlow model
                import tensorflow as tf

                model = tf.keras.models.load_model(str(path))
            else:
                # sklearn model
                model = joblib.load(path)

            # Load metadata
            metadata_path = path.parent / f"{path.stem.replace('.joblib', '').replace('.keras', '')}_metadata.json"

            # Handle both naming conventions
            if not metadata_path.exists():
                base_name = path.stem
                metadata_path = path.parent / f"{base_name}_metadata.json"

            if metadata_path.exists():
                with open(metadata_path, encoding="utf-8") as f:
                    metadata_dict = json.load(f)
                metadata = ModelMetadata.from_dict(metadata_dict)
            else:
                # Create empty metadata if file not found
                logger.warning(f"Metadata not found for {path}")
                metadata = ModelMetadata(
                    model_type="unknown",
                    product_id=0,
                    product_name="",
                    created_at="",
                    training_time_ms=0,
                    metrics={},
                    hyperparameters={},
                    data_info={},
                )

            logger.info(f"Model loaded: {model_path}")
            return model, metadata

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def list_saved_models(self) -> list[SavedModelInfo]:
        """
        Lista wszystkich zapisanych modeli.

        Returns:
            Lista obiektów SavedModelInfo z informacjami o modelach
        """
        models = []

        for path in self.models_dir.iterdir():
            if path.suffix in [".joblib", ".keras"]:
                # Get file info
                file_size_kb = path.stat().st_size / 1024

                # Try to load metadata
                metadata_path = self.models_dir / f"{path.stem}_metadata.json"

                if metadata_path.exists():
                    try:
                        with open(metadata_path, encoding="utf-8") as f:
                            meta = json.load(f)

                        models.append(
                            SavedModelInfo(
                                path=str(path),
                                filename=path.name,
                                model_type=meta.get("model_type", "unknown"),
                                product_id=meta.get("product_id", 0),
                                product_name=meta.get("product_name", ""),
                                created_at=meta.get("created_at", ""),
                                file_size_kb=file_size_kb,
                                metrics=meta.get("metrics", {}),
                            )
                        )
                    except Exception as e:
                        logger.warning(f"Could not read metadata for {path}: {e}")
                        models.append(
                            SavedModelInfo(
                                path=str(path),
                                filename=path.name,
                                model_type="unknown",
                                product_id=0,
                                product_name="",
                                created_at="",
                                file_size_kb=file_size_kb,
                                metrics={},
                            )
                        )
                else:
                    # No metadata file
                    models.append(
                        SavedModelInfo(
                            path=str(path),
                            filename=path.name,
                            model_type="unknown",
                            product_id=0,
                            product_name="",
                            created_at="",
                            file_size_kb=file_size_kb,
                            metrics={},
                        )
                    )

        # Sort by creation date (newest first)
        models.sort(key=lambda x: x.created_at, reverse=True)

        return models

    def delete_model(self, model_path: str) -> bool:
        """
        Usuwa zapisany model i jego metadane.

        Args:
            model_path: Ścieżka do pliku modelu

        Returns:
            True jeśli usunięto pomyślnie
        """
        path = Path(model_path)

        if not path.exists():
            logger.warning(f"Model not found: {model_path}")
            return False

        try:
            # Delete model file
            path.unlink()

            # Delete metadata file
            metadata_path = self.models_dir / f"{path.stem}_metadata.json"
            if metadata_path.exists():
                metadata_path.unlink()

            logger.info(f"Model deleted: {model_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete model: {e}")
            return False

    def get_model_count(self) -> int:
        """Returns the number of saved models."""
        return len([p for p in self.models_dir.iterdir() if p.suffix in [".joblib", ".keras"]])

    def get_models_by_product(self, product_id: int) -> list[SavedModelInfo]:
        """Get all saved models for a specific product."""
        all_models = self.list_saved_models()
        return [m for m in all_models if m.product_id == product_id]

    def get_best_model_for_product(self, product_id: int, metric: str = "rmse") -> Optional[SavedModelInfo]:
        """
        Get the best saved model for a product based on a metric.

        Args:
            product_id: Product ID
            metric: Metric to compare ('rmse', 'mape', 'mae') - lower is better

        Returns:
            SavedModelInfo of the best model, or None if no models found
        """
        product_models = self.get_models_by_product(product_id)

        if not product_models:
            return None

        # Filter models that have the specified metric
        models_with_metric = [m for m in product_models if metric in m.metrics]

        if not models_with_metric:
            # Return most recent if no metrics available
            return product_models[0]

        # Return model with lowest metric value
        return min(models_with_metric, key=lambda m: m.metrics.get(metric, float("inf")))


# Singleton instance
_default_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    """Get the default ModelManager instance (singleton)."""
    global _default_manager
    if _default_manager is None:
        _default_manager = ModelManager()
    return _default_manager
