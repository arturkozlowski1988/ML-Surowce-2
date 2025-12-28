"""
Async Data Loader Service.
Provides non-blocking data loading for heavy SQL queries using ThreadPoolExecutor.
Prevents GUI freezing during long-running database operations.
"""

import time
import logging
import streamlit as st
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable, Any, Optional, Dict
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger('AsyncLoader')


class LoadingState(Enum):
    """Represents the state of a loading operation."""
    IDLE = "idle"
    LOADING = "loading"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class LoadResult:
    """Result container for async loading operations."""
    state: LoadingState = LoadingState.IDLE
    data: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)
    
    @property
    def is_ready(self) -> bool:
        return self.state == LoadingState.COMPLETED
    
    @property
    def is_loading(self) -> bool:
        return self.state == LoadingState.LOADING


class AsyncDataLoader:
    """
    Thread-based async data loader for Streamlit applications.
    Uses ThreadPoolExecutor to run database queries in background.
    
    Usage:
        loader = AsyncDataLoader()
        result = loader.load_async("my_data", lambda: db.get_historical_data())
        
        if result.is_loading:
            st.spinner("Loading...")
        elif result.is_ready:
            st.dataframe(result.data)
    """
    
    # Shared thread pool across all instances
    _executor: Optional[ThreadPoolExecutor] = None
    _max_workers: int = 3
    
    # Session state key prefix
    _state_prefix = "_async_loader_"
    
    def __init__(self):
        """Initialize the async loader with shared thread pool."""
        if AsyncDataLoader._executor is None:
            AsyncDataLoader._executor = ThreadPoolExecutor(
                max_workers=self._max_workers,
                thread_name_prefix="async_loader_"
            )
            logger.info(f"AsyncDataLoader initialized with {self._max_workers} workers")
    
    def _get_state_key(self, task_id: str) -> str:
        """Generate session state key for a task."""
        return f"{self._state_prefix}{task_id}"
    
    def _get_future_key(self, task_id: str) -> str:
        """Generate session state key for a future."""
        return f"{self._state_prefix}{task_id}_future"
    
    def load_async(
        self, 
        task_id: str, 
        loader_fn: Callable[[], Any],
        force_reload: bool = False,
        cache_ttl: float = 300.0
    ) -> LoadResult:
        """
        Load data asynchronously using background thread.
        
        Args:
            task_id: Unique identifier for this loading task
            loader_fn: Function that performs the actual data loading
            force_reload: If True, ignore cache and reload data
            cache_ttl: Cache time-to-live in seconds
            
        Returns:
            LoadResult with current state and data (if available)
        """
        state_key = self._get_state_key(task_id)
        future_key = self._get_future_key(task_id)
        
        # Check for cached result
        if state_key in st.session_state and not force_reload:
            cached_result: LoadResult = st.session_state[state_key]
            
            # Check if cache is still valid
            if cached_result.is_ready:
                age = time.time() - cached_result.timestamp
                if age < cache_ttl:
                    logger.debug(f"Cache HIT for {task_id} (age: {age:.1f}s)")
                    return cached_result
                else:
                    logger.debug(f"Cache EXPIRED for {task_id} (age: {age:.1f}s)")
        
        # Check if there's an ongoing loading operation
        if future_key in st.session_state:
            future: Future = st.session_state[future_key]
            
            if future.done():
                # Retrieve result from completed future
                try:
                    start_time = st.session_state.get(f"{future_key}_start", time.time())
                    duration_ms = (time.time() - start_time) * 1000
                    
                    data = future.result()
                    result = LoadResult(
                        state=LoadingState.COMPLETED,
                        data=data,
                        duration_ms=duration_ms
                    )
                    logger.info(f"Async load completed for {task_id} in {duration_ms:.0f}ms")
                except Exception as e:
                    result = LoadResult(
                        state=LoadingState.ERROR,
                        error=str(e)
                    )
                    logger.error(f"Async load failed for {task_id}: {e}")
                
                # Cache result and cleanup future
                st.session_state[state_key] = result
                del st.session_state[future_key]
                if f"{future_key}_start" in st.session_state:
                    del st.session_state[f"{future_key}_start"]
                
                return result
            else:
                # Still loading
                return LoadResult(state=LoadingState.LOADING)
        
        # Start new loading operation
        logger.info(f"Starting async load for {task_id}")
        st.session_state[f"{future_key}_start"] = time.time()
        st.session_state[future_key] = self._executor.submit(loader_fn)
        
        return LoadResult(state=LoadingState.LOADING)
    
    def load_sync_with_progress(
        self,
        task_id: str,
        loader_fn: Callable[[], Any],
        progress_text: str = "Ładowanie danych..."
    ) -> Any:
        """
        Load data synchronously but with a progress indicator.
        Useful for operations that must complete before rendering.
        
        Args:
            task_id: Identifier for logging
            loader_fn: Function that performs the data loading
            progress_text: Text to display during loading
            
        Returns:
            The loaded data
        """
        start_time = time.time()
        
        with st.spinner(progress_text):
            try:
                data = loader_fn()
                duration_ms = (time.time() - start_time) * 1000
                logger.info(f"Sync load completed for {task_id} in {duration_ms:.0f}ms")
                return data
            except Exception as e:
                logger.error(f"Sync load failed for {task_id}: {e}")
                raise
    
    def clear_cache(self, task_id: Optional[str] = None):
        """
        Clear cached data.
        
        Args:
            task_id: Specific task to clear, or None to clear all
        """
        if task_id:
            state_key = self._get_state_key(task_id)
            if state_key in st.session_state:
                del st.session_state[state_key]
                logger.info(f"Cache cleared for {task_id}")
        else:
            # Clear all async loader state
            keys_to_delete = [
                k for k in st.session_state.keys() 
                if k.startswith(self._state_prefix)
            ]
            for key in keys_to_delete:
                del st.session_state[key]
            logger.info(f"Cleared {len(keys_to_delete)} cached items")


def create_loading_placeholder(placeholder_text: str = "Ładowanie...") -> None:
    """
    Creates a styled loading placeholder for async operations.
    """
    st.markdown(
        f"""
        <div style="
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 2rem;
            background: linear-gradient(90deg, #f0f2f6 25%, #e0e2e6 50%, #f0f2f6 75%);
            background-size: 200% 100%;
            animation: shimmer 1.5s infinite;
            border-radius: 0.5rem;
        ">
            <span style="color: #666;">⏳ {placeholder_text}</span>
        </div>
        <style>
            @keyframes shimmer {{
                0% {{ background-position: -200% 0; }}
                100% {{ background-position: 200% 0; }}
            }}
        </style>
        """,
        unsafe_allow_html=True
    )


def render_with_loading(
    task_id: str,
    loader_fn: Callable[[], Any],
    render_fn: Callable[[Any], None],
    loading_text: str = "Ładowanie danych...",
    cache_ttl: float = 300.0
) -> None:
    """
    Convenience function to render content with automatic loading state handling.
    
    Args:
        task_id: Unique identifier for the loading task
        loader_fn: Function to load the data
        render_fn: Function to render the loaded data
        loading_text: Text to show during loading
        cache_ttl: Cache TTL in seconds
    """
    loader = AsyncDataLoader()
    result = loader.load_async(task_id, loader_fn, cache_ttl=cache_ttl)
    
    if result.is_loading:
        create_loading_placeholder(loading_text)
        # Trigger rerun to check if loading completed
        time.sleep(0.5)
        st.rerun()
    elif result.is_ready:
        render_fn(result.data)
    elif result.state == LoadingState.ERROR:
        st.error(f"Błąd ładowania: {result.error}")
