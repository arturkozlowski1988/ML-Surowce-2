"""
Model Download Service - Download LLM models from HuggingFace Hub.

Provides functionality to:
- List available GGUF models from popular repositories
- Download models with progress tracking
- Manage local model files
"""

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger("ModelDownloader")

# Project root and models directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = PROJECT_ROOT / "models"


@dataclass
class ModelInfo:
    """Information about a downloadable model."""

    name: str  # Display name
    repo_id: str  # HuggingFace repo ID
    filename: str  # Filename in the repo
    size_gb: float  # Approximate size in GB
    description: str  # Model description
    recommended: bool = False  # Is this a recommended model?

    @property
    def local_path(self) -> Path:
        return MODELS_DIR / self.filename

    @property
    def is_downloaded(self) -> bool:
        return self.local_path.exists()

    @property
    def hf_url(self) -> str:
        """Direct download URL from HuggingFace."""
        return f"https://huggingface.co/{self.repo_id}/resolve/main/{self.filename}"

    @property
    def hf_page_url(self) -> str:
        """HuggingFace model page URL."""
        return f"https://huggingface.co/{self.repo_id}"


# Pre-defined list of popular GGUF models
AVAILABLE_MODELS: list[ModelInfo] = [
    # Qwen 2.5 Family (recommended for Polish)
    ModelInfo(
        name="Qwen2.5-7B Instruct (Q4_K_M)",
        repo_id="Qwen/Qwen2.5-7B-Instruct-GGUF",
        filename="qwen2.5-7b-instruct-q4_k_m.gguf",
        size_gb=4.7,
        description="Najlepszy stosunek jakości do rozmiaru. Dobra obsługa polskiego.",
        recommended=True,
    ),
    ModelInfo(
        name="Qwen2.5-3B Instruct (Q4_K_M)",
        repo_id="Qwen/Qwen2.5-3B-Instruct-GGUF",
        filename="qwen2.5-3b-instruct-q4_k_m.gguf",
        size_gb=2.0,
        description="Mniejszy model, szybszy, mniej wymagający. Dobry na słabszych PC.",
        recommended=False,
    ),
    ModelInfo(
        name="Qwen2.5-1.5B Instruct (Q4_K_M)",
        repo_id="Qwen/Qwen2.5-1.5B-Instruct-GGUF",
        filename="qwen2.5-1.5b-instruct-q4_k_m.gguf",
        size_gb=1.1,
        description="Najmniejszy. Dla bardzo ograniczonych zasobów.",
        recommended=False,
    ),
    # Llama 3.2 Family
    ModelInfo(
        name="Llama 3.2-3B Instruct (Q4_K_M)",
        repo_id="bartowski/Llama-3.2-3B-Instruct-GGUF",
        filename="Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        size_gb=2.0,
        description="Model Meta. Bardzo dobra jakość, głównie angielski.",
        recommended=False,
    ),
    ModelInfo(
        name="Llama 3.2-1B Instruct (Q4_K_M)",
        repo_id="bartowski/Llama-3.2-1B-Instruct-GGUF",
        filename="Llama-3.2-1B-Instruct-Q4_K_M.gguf",
        size_gb=0.8,
        description="Ultra-mały model Llama. Szybki, ograniczone możliwości.",
        recommended=False,
    ),
    # Mistral Family
    ModelInfo(
        name="Mistral-7B Instruct v0.3 (Q4_K_M)",
        repo_id="MaziyarPanahi/Mistral-7B-Instruct-v0.3-GGUF",
        filename="Mistral-7B-Instruct-v0.3.Q4_K_M.gguf",
        size_gb=4.4,
        description="Popularny model Mistral. Dobra jakość i szybkość.",
        recommended=False,
    ),
    # Phi-3 Family (Microsoft)
    ModelInfo(
        name="Phi-3 Mini 4K Instruct (Q4_K_M)",
        repo_id="microsoft/Phi-3-mini-4k-instruct-gguf",
        filename="Phi-3-mini-4k-instruct-q4.gguf",
        size_gb=2.4,
        description="Model Microsoft. Efektywny, dobry do zadań biznesowych.",
        recommended=False,
    ),
]


class DownloadProgress:
    """Tracks download progress."""

    def __init__(self):
        self.total_bytes: int = 0
        self.downloaded_bytes: int = 0
        self.is_complete: bool = False
        self.is_error: bool = False
        self.error_message: str = ""
        self.is_cancelled: bool = False

    @property
    def progress_percent(self) -> float:
        if self.total_bytes == 0:
            return 0.0
        return (self.downloaded_bytes / self.total_bytes) * 100

    @property
    def downloaded_gb(self) -> float:
        return self.downloaded_bytes / (1024**3)

    @property
    def total_gb(self) -> float:
        return self.total_bytes / (1024**3)


class ModelDownloader:
    """
    Downloads LLM models from HuggingFace Hub.

    Usage:
        downloader = ModelDownloader()
        models = downloader.get_available_models()
        progress = downloader.download_model(models[0])
    """

    def __init__(self, models_dir: Optional[Path] = None):
        self.models_dir = models_dir or MODELS_DIR
        self._ensure_directory()
        self._current_download: Optional[DownloadProgress] = None
        self._download_thread: Optional[threading.Thread] = None

    def _ensure_directory(self):
        """Create models directory if it doesn't exist."""
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def get_available_models(self) -> list[ModelInfo]:
        """Get list of available models for download."""
        # Update is_downloaded status
        for model in AVAILABLE_MODELS:
            # Check if file exists in models directory
            local_path = self.models_dir / model.filename
            # Update the property by checking the path
        return AVAILABLE_MODELS

    def get_local_models(self) -> list[dict]:
        """Get list of locally downloaded models."""
        models = []
        if not self.models_dir.exists():
            return models

        for path in self.models_dir.glob("*.gguf"):
            size_gb = path.stat().st_size / (1024**3)

            # Try to match with known models
            known_model = None
            for m in AVAILABLE_MODELS:
                if m.filename == path.name:
                    known_model = m
                    break

            models.append(
                {
                    "filename": path.name,
                    "path": str(path),
                    "size_gb": size_gb,
                    "name": known_model.name if known_model else path.stem,
                    "description": known_model.description if known_model else "Ręcznie dodany model",
                }
            )

        return sorted(models, key=lambda x: x["filename"])

    def download_model(
        self, model: ModelInfo, progress_callback: Optional[Callable[[DownloadProgress], None]] = None
    ) -> DownloadProgress:
        """
        Download a model from HuggingFace Hub.

        Args:
            model: ModelInfo object for the model to download
            progress_callback: Optional callback for progress updates

        Returns:
            DownloadProgress object
        """
        progress = DownloadProgress()
        self._current_download = progress

        try:
            import requests
            from huggingface_hub import HfFileSystem, hf_hub_download
            from huggingface_hub.utils import tqdm as hf_tqdm

            # Get file info for size
            try:
                fs = HfFileSystem()
                file_info = fs.info(f"{model.repo_id}/{model.filename}")
                progress.total_bytes = file_info.get("size", 0)
            except Exception:
                # Estimate from model info
                progress.total_bytes = int(model.size_gb * 1024**3)

            logger.info(f"Starting download: {model.name} ({progress.total_gb:.1f} GB)")

            # Download to local models directory
            local_path = self.models_dir / model.filename

            # Use requests for better progress tracking
            url = f"https://huggingface.co/{model.repo_id}/resolve/main/{model.filename}"

            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            # Get actual size from headers
            content_length = response.headers.get("content-length")
            if content_length:
                progress.total_bytes = int(content_length)

            # Download with progress
            chunk_size = 8192 * 16  # 128KB chunks

            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if progress.is_cancelled:
                        logger.info("Download cancelled by user")
                        break

                    if chunk:
                        f.write(chunk)
                        progress.downloaded_bytes += len(chunk)

                        if progress_callback:
                            progress_callback(progress)

            if not progress.is_cancelled:
                progress.is_complete = True
                logger.info(f"Download complete: {model.filename}")
            else:
                # Clean up partial download
                if local_path.exists():
                    local_path.unlink()

        except ImportError as e:
            progress.is_error = True
            progress.error_message = "Brak biblioteki huggingface_hub. Zainstaluj: pip install huggingface_hub"
            logger.error(f"Import error: {e}")

        except Exception as e:
            progress.is_error = True
            progress.error_message = str(e)
            logger.error(f"Download error: {e}")

            # Clean up partial download
            local_path = self.models_dir / model.filename
            if local_path.exists():
                try:
                    local_path.unlink()
                except:
                    pass

        return progress

    def download_model_async(
        self, model: ModelInfo, progress_callback: Optional[Callable[[DownloadProgress], None]] = None
    ) -> DownloadProgress:
        """Start download in background thread."""
        progress = DownloadProgress()
        self._current_download = progress

        def download_thread():
            result = self.download_model(model, progress_callback)
            progress.is_complete = result.is_complete
            progress.is_error = result.is_error
            progress.error_message = result.error_message

        self._download_thread = threading.Thread(target=download_thread, daemon=True)
        self._download_thread.start()

        return progress

    def cancel_download(self):
        """Cancel the current download."""
        if self._current_download:
            self._current_download.is_cancelled = True

    def delete_model(self, filename: str) -> bool:
        """Delete a local model file."""
        try:
            path = self.models_dir / filename
            if path.exists():
                path.unlink()
                logger.info(f"Deleted model: {filename}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete model: {e}")
            return False

    def get_current_progress(self) -> Optional[DownloadProgress]:
        """Get current download progress."""
        return self._current_download


# Singleton instance
_downloader: Optional[ModelDownloader] = None


def get_model_downloader() -> ModelDownloader:
    """Get the default ModelDownloader instance (singleton)."""
    global _downloader
    if _downloader is None:
        _downloader = ModelDownloader()
    return _downloader
