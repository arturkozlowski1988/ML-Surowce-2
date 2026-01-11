"""
Base ViewModel class for MVVM architecture.
Provides common patterns for state management, data loading, and error handling.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("ViewModel")


class LoadingState(Enum):
    """State of data loading."""

    IDLE = "idle"
    LOADING = "loading"
    SUCCESS = "success"
    ERROR = "error"


@dataclass
class ViewModelState:
    """Base state class for ViewModels."""

    loading_state: LoadingState = LoadingState.IDLE
    error_message: Optional[str] = None
    last_updated: Optional[float] = None

    def is_loading(self) -> bool:
        return self.loading_state == LoadingState.LOADING

    def has_error(self) -> bool:
        return self.error_message is not None

    def is_ready(self) -> bool:
        return self.loading_state == LoadingState.SUCCESS


class BaseViewModel:
    """
    Base class for ViewModels in MVVM pattern.

    Provides:
    - State management with loading/error states
    - Cached data access
    - Progress tracking
    - Error handling
    """

    def __init__(self, db=None):
        self.db = db
        self._state = ViewModelState()
        self._cache: dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutes
        self._loading_progress = 0.0
        self._loading_message = ""

    @property
    def state(self) -> ViewModelState:
        return self._state

    @property
    def loading_progress(self) -> float:
        return self._loading_progress

    @property
    def loading_message(self) -> str:
        return self._loading_message

    def _set_loading(self, progress: float = 0.0, message: str = ""):
        """Set loading state with progress."""
        self._state.loading_state = LoadingState.LOADING
        self._loading_progress = progress
        self._loading_message = message
        logger.debug(f"Loading: {progress:.0%} - {message}")

    def _set_success(self):
        """Mark loading as successful."""
        self._state.loading_state = LoadingState.SUCCESS
        self._state.error_message = None
        self._state.last_updated = time.time()
        self._loading_progress = 1.0

    def _set_error(self, message: str):
        """Set error state."""
        self._state.loading_state = LoadingState.ERROR
        self._state.error_message = message
        logger.error(f"ViewModel error: {message}")

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return data
        return None

    def _set_cached(self, key: str, value: Any):
        """Store value in cache with timestamp."""
        self._cache[key] = (value, time.time())

    def clear_cache(self):
        """Clear all cached data."""
        self._cache.clear()
        logger.debug("ViewModel cache cleared")

    def execute_with_progress(self, func: Callable, steps: list[str] = None, *args, **kwargs) -> Any:
        """
        Execute a function with progress tracking.

        Args:
            func: Function to execute
            steps: List of step descriptions for progress
            *args, **kwargs: Arguments for func

        Returns:
            Result of func
        """
        steps = steps or ["Przetwarzanie..."]

        try:
            for i, step in enumerate(steps):
                progress = (i + 0.5) / len(steps)
                self._set_loading(progress, step)

            result = func(*args, **kwargs)

            self._set_success()
            return result

        except Exception as e:
            self._set_error(str(e))
            raise
